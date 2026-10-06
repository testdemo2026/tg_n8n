import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from httpx import HTTPStatusError

from ..dependencies import ClientDep, SettingsDep
from ..schemas import (
    AuthStatusResponse,
    RefreshTokenResponse,
    SmsConfirmRequest,
    SmsConfirmResponse,
    SmsStartRequest,
    SmsStartResponse,
    TokenLoginRequest,
    TokenLoginResponse,
    UserInfoResponse,
)
from ..sessions import create_session, delete_session, get_session
from ..token_store import clear_tokens
from ..utils import decode_jwt_payload

router = APIRouter(tags=["auth"])


def _probe_login(client) -> tuple[bool, Optional[str], bool]:
    """调一次需要登录的上游接口来验证凭据（会走自动刷新）。

    :return: (是否通过, 失败原因, 是否鉴权失败)
    """
    try:
        client.fs_files(page=0, page_size=1)
        return True, None, False
    except HTTPStatusError as exc:
        code = exc.response.status_code
        return False, f"上游返回 {code}", code in (401, 403)
    except Exception as exc:  # noqa: BLE001 - 网络/解析等异常统一报告
        return False, f"验证失败: {exc}", False


def _is_auth_error(info) -> bool:
    return isinstance(info, dict) and bool(info.get("error"))



@router.get(
    "/auth/status",
    summary="检查是否已登录",
    description=(
        "登录前可先调本接口判断，避免重复走短信登录流程。\n\n"
        "- 默认只做**本地**判断（有 token、是否过期、能否刷新），不产生网络请求；\n"
        "- `verify=true` 时会真正调用一次需要登录的上游接口（必要时自动刷新 token），"
        "`verified` 才代表 token 确实有效。\n\n"
        "字段含义：`logged_in` 本地判断；`expired` access_token 是否过期；"
        "`refreshed` 本次是否触发了刷新；`verified` 是否验证通过。"
    ),
    response_model=AuthStatusResponse,
)
def auth_status(client: ClientDep, verify: bool = False):
    def snapshot():
        now = time.time()
        expires_at = client.token_expires_at
        has_access = bool(client.token)
        has_refresh = bool(client.refresh_token_value)
        expired = expires_at is not None and now >= expires_at
        return {
            "logged_in": has_access and (not expired or has_refresh),
            "has_access_token": has_access,
            "has_refresh_token": has_refresh,
            "expired": expired,
            "expires_at": expires_at,
            "expires_in": int(expires_at - now) if expires_at else None,
        }

    result = {
        **snapshot(),
        "refreshed": False,
        "verified": False,
        "detail": None,
    }

    if verify and result["logged_in"]:
        token_before = client.token
        ok, detail, auth_failed = _probe_login(client)
        result["verified"] = ok
        result["detail"] = detail

        result.update(snapshot())
        result["refreshed"] = result["has_access_token"] and client.token != token_before
        if result["refreshed"]:
            result["verified"] = True
        if auth_failed and not result["verified"]:
            result["logged_in"] = False

    return result


@router.post(
    "/auth/logout",
    summary="退出登录（清除当前凭据，用于切换账号）",
    description=(
        "清除内存中的 token，并删除 `data/tokens.json` 里已持久化的凭据。\n\n"
        "退出后 `/auth/status` 返回未登录，此时再用新账号走 `/auth/sms/start`+"
        "`/auth/sms/confirm` 或 `/auth/token` 即可切换账号。\n\n"
        "也可以不退出、直接用新账号重新登录覆盖；但**不要在上传/任务进行中切换账号**，"
        "否则进行中的请求会混用新旧 token。"
    ),
)
def logout(client: ClientDep, settings: SettingsDep):
    client.clear_credentials()
    clear_tokens(settings)
    return {"status": "ok", "logged_in": False}


@router.post(
    "/auth/sms/start",
    summary="手机验证码登录-第 1 步：发送验证码",
    description=(
        "向手机号发送短信验证码，返回 `session_id`。\n\n"
        "**流程**：\n"
        "1. 调本接口（只传 phone_number）→ 返回 `status=sent` 和 `session_id`；\n"
        "2. 手机收到验证码后调 `/auth/sms/confirm` 提交。\n\n"
        "**若返回 `status=captcha_required`**（触发人机验证，未发短信）：\n"
        "1. 在浏览器打开返回的 `init.url`，完成滑块/点选验证；\n"
        "2. 验证成功后页面跳转到带 `captcha_token=xxx` 的地址，复制该值；\n"
        "3. 带上 `captcha_token` 再调一次本接口，即可正常发送。\n\n"
        "`target`：验证码发送方式，默认 `ANY` 由服务端选择。"
    ),
    response_model=SmsStartResponse,
)
def sms_start(body: SmsStartRequest, client: ClientDep):
    try:
        init = client.login_sms_init(body.phone_number, body.captcha_token)
    except Exception as exc:  # noqa: BLE001 - 上游异常统一转 502，避免裸 500
        raise HTTPException(
            status_code=502, detail=f"发送验证码失败(init): {exc}"
        ) from exc
    if not isinstance(init, dict):
        raise HTTPException(status_code=502, detail=f"上游返回异常: {init!r}")
    captcha_token = init.get("captcha_token")
    if not captcha_token:
        return {
            "status": "captcha_required",
            "captcha_token": None,
            "url": init.get("url"),
            "init": init,
        }

    try:
        send = client.login_sms_send(body.phone_number, captcha_token, body.target)
    except Exception as exc:  # noqa: BLE001 - 上游异常统一转 502，避免裸 500
        raise HTTPException(
            status_code=502, detail=f"发送验证码失败(send): {exc}"
        ) from exc
    if not isinstance(send, dict):
        raise HTTPException(status_code=502, detail=f"上游返回异常: {send!r}")
    verification_id = send.get("verification_id")
    if not verification_id:
        return {"status": "failed", "init": init, "send": send}

    session_id = create_session(
        body.phone_number, captcha_token, verification_id, body.target
    )
    payload = decode_jwt_payload(verification_id) or {}
    return {
        "status": "sent",
        "session_id": session_id,
        "phone": payload.get("p", body.phone_number),
        "expires_in": send.get("expires_in"),
        "captcha_token": None,
        "url": None,
    }


@router.post(
    "/auth/sms/confirm",
    summary="手机验证码登录-第 2 步：提交验证码",
    description=(
        "用 `/auth/sms/start` 返回的 session_id 和收到的验证码完成登录。"
        "成功后 access_token / refresh_token 自动持久化到 data/tokens.json。"
        "验证码与 verification_id 一一对应，verify 成功后即被消耗；若需重来请重新 start。"
    ),
    response_model=SmsConfirmResponse,
)
def sms_confirm(body: SmsConfirmRequest, client: ClientDep):
    session = get_session(body.session_id)
    if not session:
        raise HTTPException(
            status_code=400,
            detail="session_id 无效或已过期（10 分钟），请重新调用 /auth/sms/start",
        )

    try:
        verify = client.login_sms_verify(session.verification_id, body.code)
    except Exception as exc:  # noqa: BLE001 - 上游异常统一转 502，避免裸 500
        raise HTTPException(
            status_code=502, detail=f"校验验证码失败: {exc}"
        ) from exc
    if not isinstance(verify, dict):
        raise HTTPException(status_code=502, detail=f"上游返回异常: {verify!r}")
    verification_token = verify.get("verification_token")
    if not verification_token:
        return {"status": "failed", "verify": verify}

    try:
        result = client.login_sms_signin(
            body.code, verification_token, session.phone_number
        )
    except Exception as exc:  # noqa: BLE001 - 上游异常统一转 502，避免裸 500
        raise HTTPException(status_code=502, detail=f"登录失败: {exc}") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail=f"上游返回异常: {result!r}")
    if not result.get("access_token"):
        return {"status": "failed", "signin": result}

    delete_session(body.session_id)
    return {**result, "status": "ok"}


@router.post(
    "/auth/token",
    summary="使用 access_token / refresh_token 登录",
    description=(
        "直接用已有的凭据登录，会覆盖当前 token 并持久化到 data/tokens.json。"
        "refresh_token 用于 access_token 过期后自动刷新，可只传 access_token。\n\n"
        "**登录后会真正验证一次凭据**（必要时用 refresh_token 自动刷新）：\n"
        "- 验证通过 → 200，`verified=true`；\n"
        "- access_token 过期且无法刷新 → 401；\n"
        "- 上游不可达等其它错误 → 502。"
    ),
    response_model=TokenLoginResponse,
)
def token_login(body: TokenLoginRequest, client: ClientDep):
    client.set_credentials(
        body.access_token, refresh_token=body.refresh_token, device_id=body.device_id
    )
    ok, detail, auth_failed = _probe_login(client)
    if not ok:
        if auth_failed:
            raise HTTPException(status_code=401, detail=f"凭据无效或已过期: {detail}")
        raise HTTPException(status_code=502, detail=detail)
    return {
        "status": "ok",
        "access_token": client.token,
        "refresh_token": client.refresh_token_value,
        "device_id": client.device_id,
        "verified": True,
    }


@router.post(
    "/auth/refresh", summary="手动刷新 access_token", response_model=RefreshTokenResponse
)
def refresh(client: ClientDep):
    return client.refresh_token()


@router.get(
    "/auth/user",
    summary="获取当前登录用户信息",
    description=(
        "返回当前登录用户信息。access_token 失效时，会先用 refresh_token 自动刷新再重试；"
        "仍失败则返回 401（而不是把上游错误当成 200 成功返回）。"
    ),
    response_model=UserInfoResponse,
)
def user_info(client: ClientDep):
    try:
        info = client.user_info()
        if _is_auth_error(info) and client.refresh_token_value:
            try:
                client.refresh_token()
                info = client.user_info()
            except Exception:  # noqa: BLE001 - 刷新失败则按未登录处理
                pass
    except Exception as exc:  # noqa: BLE001 - 网络/解析等异常
        raise HTTPException(
            status_code=502, detail=f"获取用户信息失败: {exc}"
        ) from exc
    if _is_auth_error(info):
        raise HTTPException(
            status_code=401, detail="未登录或凭据已失效，请重新登录"
        )
    return info
