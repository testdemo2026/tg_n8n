from fastapi import APIRouter, HTTPException

from ..dependencies import ClientDep
from ..schemas import (
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
from ..utils import decode_jwt_payload

router = APIRouter(tags=["auth"])


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
    init = client.login_sms_init(body.phone_number, body.captcha_token)
    captcha_token = init.get("captcha_token")
    if not captcha_token:
        return {
            "status": "captcha_required",
            "captcha_token": None,
            "url": init.get("url"),
            "init": init,
        }

    send = client.login_sms_send(body.phone_number, captcha_token, body.target)
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

    verify = client.login_sms_verify(session.verification_id, body.code)
    verification_token = verify.get("verification_token")
    if not verification_token:
        return {"status": "failed", "verify": verify}

    result = client.login_sms_signin(body.code, verification_token, session.phone_number)
    if not result.get("access_token"):
        return {"status": "failed", "signin": result}

    delete_session(body.session_id)
    return {"status": "ok", **result}


@router.post(
    "/auth/token",
    summary="使用 access_token / refresh_token 登录",
    description=(
        "直接用已有的凭据登录，会覆盖当前 token 并持久化到 data/tokens.json。"
        "refresh_token 用于 access_token 过期后自动刷新，可只传 access_token。"
    ),
    response_model=TokenLoginResponse,
)
def token_login(body: TokenLoginRequest, client: ClientDep):
    client.set_credentials(
        body.access_token, refresh_token=body.refresh_token, device_id=body.device_id
    )
    return {
        "status": "ok",
        "access_token": client.token,
        "refresh_token": client.refresh_token_value,
        "device_id": client.device_id,
    }


@router.post(
    "/auth/refresh", summary="手动刷新 access_token", response_model=RefreshTokenResponse
)
def refresh(client: ClientDep):
    return client.refresh_token()


@router.get(
    "/auth/user", summary="获取当前登录用户信息", response_model=UserInfoResponse
)
def user_info(client: ClientDep):
    return client.user_info()
