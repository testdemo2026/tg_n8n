from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

ParentId = Optional[Union[int, str]]

PARENT_ID_DESC = "父目录 ID（用字符串）；0/空/不传=根目录；'*' 仅 /files/list 表示全部目录"
FILE_IDS_DESC = "文件/文件夹 ID 列表（用字符串），来自 /files/list 的 fileId"
FILE_ID_DESC = "文件/文件夹 ID（用字符串），来自 /files/list 的 fileId"
PAGE_DESC = "页码，从 0 开始"
PAGE_SIZE_DESC = "每页数量"


# ===== Auth =====


class SmsStartRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone_number": "+86 13800138000",
                "target": "ANY",
                "captcha_token": "",
            }
        }
    )

    phone_number: str = Field(
        ..., description="手机号，含国际区号，如 +86 13800138000"
    )
    target: str = Field(
        "ANY", description="验证码发送方式，默认 ANY（由服务端选择）"
    )
    captcha_token: Optional[str] = Field(
        None,
        description=(
            "人机验证 token（可选）。首次调用不传；"
            "若返回 status=captcha_required，用返回的 init.url 在浏览器完成验证，"
            "从跳转地址取 captcha_token，带上它再调一次本接口。"
        ),
    )


class SmsConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"session_id": "xxxxxxxx", "code": "123456"}}
    )

    session_id: str = Field(..., description="/auth/sms/start 返回的 session_id")
    code: str = Field(..., description="手机收到的短信验证码")


class TokenLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOi...",
                "refresh_token": "gy.xxxx",
                "device_id": "",
            }
        }
    )

    access_token: str = Field(..., description="访问令牌")
    refresh_token: Optional[str] = Field(
        None, description="刷新令牌，用于 access_token 过期后自动刷新（可选）"
    )
    device_id: Optional[str] = Field(
        None, description="设备 ID，不传则沿用当前值（可选）"
    )


# ----- Auth responses -----


class SmsStartResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "status": "sent",
                "session_id": "fa92e35b5f99d0ba",
                "phone": "+86 13800138000",
                "expires_in": 300,
                "captcha_token": None,
                "url": None,
            }
        },
    )

    status: str = Field(
        ..., description="sent=已发送；captcha_required=需先过人机验证；failed=发送失败"
    )
    session_id: Optional[str] = Field(
        None, description="第二步 /auth/sms/confirm 需要用到，有效期 10 分钟"
    )
    phone: Optional[str] = Field(None, description="手机号")
    expires_in: Optional[int] = Field(None, description="验证码有效期（秒）")
    captcha_token: Optional[str] = Field(
        None,
        description=(
            "人机验证 token（预留字段）。captcha_required 时，"
            "完成 init.url 验证后回填并在下次 /auth/sms/start 传入。"
        ),
    )
    url: Optional[str] = Field(
        None, description="人机验证地址（captcha_required 时返回，浏览器打开完成验证）"
    )
    init: Optional[Dict[str, Any]] = Field(None, description="原始 init 返回")
    send: Optional[Dict[str, Any]] = Field(None, description="原始 send 返回")


class SmsConfirmResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "status": "ok",
                "token_type": "Bearer",
                "access_token": "eyJhbGciOi...",
                "refresh_token": "gy.xxxx",
                "expires_in": 7200,
                "sub": "aj_xxxx",
            }
        },
    )

    status: str = Field(..., description="ok=成功；failed=失败")
    token_type: Optional[str] = Field(None, description="令牌类型")
    access_token: Optional[str] = Field(None, description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    expires_in: Optional[int] = Field(None, description="access_token 有效期（秒）")
    sub: Optional[str] = Field(None, description="用户标识")
    verify: Optional[Dict[str, Any]] = Field(None, description="验证码校验失败时的原始返回")
    signin: Optional[Dict[str, Any]] = Field(None, description="登录失败时的原始返回")


class TokenLoginResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "status": "ok",
                "access_token": "eyJhbGciOi...",
                "refresh_token": "gy.xxxx",
                "device_id": "3d3e9b00...",
            }
        },
    )

    status: str = Field(..., description="ok=成功")
    access_token: Optional[str] = Field(None, description="当前访问令牌")
    refresh_token: Optional[str] = Field(None, description="当前刷新令牌")
    device_id: Optional[str] = Field(None, description="当前设备 ID")


class RefreshTokenResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    token_type: Optional[str] = Field(None, description="令牌类型")
    access_token: Optional[str] = Field(None, description="新的访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    expires_in: Optional[int] = Field(None, description="access_token 有效期（秒）")
    scope: Optional[str] = Field(None, description="授权范围")
    sub: Optional[str] = Field(None, description="用户标识")


class UserInfoResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    sub: Optional[str] = Field(None, description="用户标识")
    name: Optional[str] = Field(None, description="用户名")
    phone_number: Optional[str] = Field(None, description="手机号（脱敏）")
    created_at: Optional[str] = Field(None, description="创建时间")
    password_updated_at: Optional[str] = Field(None, description="密码更新时间")


# ===== Files =====


class FilesListRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"parent_id": "", "page": 0, "page_size": 50}
        }
    )

    parent_id: ParentId = Field(None, description=PARENT_ID_DESC)
    page: int = Field(0, description=PAGE_DESC)
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    order_by: int = Field(0, description="排序字段")
    sort_type: int = Field(0, description="排序方式：0 升序，1 降序")
    file_types: Optional[List[int]] = Field(
        None,
        description="文件类型过滤：1 图片 2 视频 3 音频 4 文档 5 压缩包 9 BT种子",
    )
    res_type: Optional[int] = Field(
        None, description="资源类型：1 文件，2 文件夹（不传=全部）"
    )
    dir_type: Optional[int] = Field(
        None, description="目录类型：4 为回收站（不传=普通目录）"
    )
    need_play_record: bool = Field(
        False, description="是否返回播放记录（音视频使用）"
    )


class TypeListRequest(BaseModel):
    page: int = Field(0, description=PAGE_DESC)
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    order_by: int = Field(3, description="排序字段")
    sort_type: int = Field(1, description="排序方式：0 升序，1 降序")
    need_play_record: bool = Field(
        False, description="是否返回播放记录（音视频使用）"
    )


class RecycleListRequest(BaseModel):
    page: int = Field(0, description=PAGE_DESC)
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    order_by: int = Field(10, description="排序字段")
    sort_type: int = Field(0, description="排序方式：0 升序，1 降序")


class FileIdRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"file_id": "1928031687445237826"}}
    )

    file_id: str = Field(..., description=FILE_ID_DESC)


class CreateDirRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"dir_name": "新建文件夹", "parent_id": ""}}
    )

    dir_name: str = Field(..., description="文件夹名称")
    parent_id: ParentId = Field(None, description=PARENT_ID_DESC)
    fail_if_name_exist: bool = Field(
        False, description="同名文件夹已存在时是否报错"
    )


class CopyMoveRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_ids": ["1928031687445237826"],
                "parent_id": "1930348727118114862",
            }
        }
    )

    file_ids: List[Union[int, str]] = Field(..., description=FILE_IDS_DESC)
    parent_id: ParentId = Field(None, description="目标目录 ID（" + PARENT_ID_DESC + "）")


class RenameRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"file_id": "1928031687445237826", "new_name": "新名字"}
        }
    )

    file_id: str = Field(..., description=FILE_ID_DESC)
    new_name: str = Field(..., description="新的文件/文件夹名称")


class FileIdsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"file_ids": ["1928031687445237826"]}}
    )

    file_ids: List[Union[int, str]] = Field(
        ...,
        description=(
            FILE_IDS_DESC
            + "。普通目录中的 ID → 移入回收站；回收站中的 ID → 永久删除"
        ),
    )


class TaskIdRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"task_id": "1954108920804642829"}}
    )

    task_id: str = Field(..., description="异步任务 ID，来自 copy/move/delete 等返回的 taskId")


# ===== Cloud download =====


class CloudTaskListRequest(BaseModel):
    page: int = Field(0, description=PAGE_DESC)
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    status: Optional[List[int]] = Field(
        None, description="任务状态过滤，默认 [0, 1, 3, 4]"
    )


class CloudResolveUrlRequest(BaseModel):
    url: str = Field(..., description="下载链接，支持 HTTP / 磁力 / ed2k 等")


class CloudCreateTaskRequest(BaseModel):
    url: str = Field(..., description="下载链接，支持 HTTP / 磁力 / ed2k 等")
    parent_id: ParentId = Field(None, description="保存到的目标目录 ID")


# ===== Share =====


class ShareCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_ids": ["1950797091944763422"],
                "title": "我的分享",
                "validate_duration": 0,
                "code": "",
            }
        }
    )

    file_ids: List[Union[int, str]] = Field(..., description=FILE_IDS_DESC)
    title: str = Field(..., description="分享标题")
    validate_duration: int = Field(
        0, description="有效期（秒）：86400=1天，604800=7天，2592000=30天，0=永久"
    )
    share_type: int = Field(1, description="分享类型（官网快速分享用 0）")
    code: str = Field("", description="提取码；空串则按 auto_fill_code 处理")
    auto_fill_code: bool = Field(
        True, description="是否自动生成提取码（code 为空时生效；设 false 且 code 为空则无密码）"
    )
    traffic_limit: str = Field("0", description="流量限制，\"0\"=不限")
    max_restore_count: int = Field(0, description="最大转存次数，0=不限")
    download_type: int = Field(1, description="下载类型")


class ShareListRequest(BaseModel):
    page: int = Field(0, description=PAGE_DESC)
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    order_type: int = Field(1, description="排序字段")
    sort_type: int = Field(1, description="排序方式：0 升序，1 降序")


class ShareUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "share_id": "1950797091944763422",
                "title": "我的分享",
                "validate_duration": 604800,
                "code": "",
                "auto_fill_code": True,
            }
        }
    )

    share_id: str = Field(
        ...,
        description="分享 ID，取 /share/list 返回项的 `id`（注意不是 shareId）",
    )
    title: str = Field(..., description="标题（注意：服务端不支持修改，传了也不生效）")
    validate_duration: int = Field(
        0, description="有效期（秒）：86400=1天，604800=7天，2592000=30天，0=永久"
    )
    share_type: int = Field(1, description="分享类型")
    code: str = Field("", description="提取码；空串则按 auto_fill_code 处理")
    auto_fill_code: bool = Field(True, description="是否自动生成提取码")
    traffic_limit: str = Field("0", description="流量限制，\"0\"=不限")
    max_restore_count: int = Field(0, description="最大转存次数，0=不限")
    download_type: int = Field(1, description="下载类型")


class ShareDeleteRequest(BaseModel):
    ids: List[str] = Field(..., description="分享 ID 列表（/share/list 的 `id`）")


class ShareRestoreRequest(BaseModel):
    access_token: str = Field(..., description="分享访问令牌（/share/access-token 获取）")
    file_ids: List[Union[int, str]] = Field(
        ..., description="分享中的文件 ID 列表"
    )
    parent_id: str = Field("", description="转存到的目标目录 ID，空=根目录")


class ShareDownloadUrlRequest(BaseModel):
    file_id: str = Field(..., description="分享中的文件 ID")
    access_token: str = Field(..., description="分享访问令牌")


class ShareFilesSizeRequest(BaseModel):
    access_token: str = Field(..., description="分享访问令牌")
    file_ids: List[Union[int, str]] = Field(..., description="分享中的文件 ID 列表")
    download: bool = Field(True, description="是否为下载场景")


class ShareSummaryRequest(BaseModel):
    share_id: str = Field(..., description="分享 ID（shareUrl 里的那串，如 xxx_aj_xxx）")


class ShareAccessTokenRequest(BaseModel):
    share_id: str = Field(..., description="分享 ID（shareUrl 里的那串）")
    code: str = Field(..., description="分享提取码，无密码传空串")


class ShareFilesListRequest(BaseModel):
    access_token: str = Field(..., description="分享访问令牌")
    parent_id: str = Field("", description="分享内父目录 ID，空=分享根目录")
    page: int = Field(1, description="页码，从 1 开始")
    page_size: int = Field(50, description=PAGE_SIZE_DESC)
    order_by: int = Field(0, description="排序字段")
    sort_type: int = Field(0, description="排序方式：0 升序，1 降序")
