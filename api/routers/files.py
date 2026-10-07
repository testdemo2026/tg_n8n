import mimetypes
import tempfile
import threading
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from ..config import Settings
from ..dependencies import ClientDep, SettingsDep
from ..schemas import (
    CopyMoveRequest,
    CreateDirRequest,
    FileIdRequest,
    FindByNameRequest,
    FindByNameResponse,
    FileIdsRequest,
    FilesListRequest,
    RecycleListRequest,
    RenameRequest,
    TaskIdRequest,
    TypeListRequest,
    UploadPathRequest,
)
from ..utils import coerce_file_ids, coerce_parent_id, find_url

router = APIRouter(tags=["files"])


@router.post("/files/list", summary="获取文件列表")
def files_list(body: FilesListRequest, client: ClientDep):
    return client.fs_files(
        parent_id=coerce_parent_id(body.parent_id),
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
        file_types=body.file_types,
        res_type=body.res_type,
        dir_type=body.dir_type,
        need_play_record=body.need_play_record,
    )


@router.post("/files/images", summary="获取图片列表（全部目录）")
def files_images(body: TypeListRequest, client: ClientDep):
    return client.fs_image_list(
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
    )


@router.post("/files/videos", summary="获取视频列表（全部目录）")
def files_videos(body: TypeListRequest, client: ClientDep):
    return client.fs_video_list(
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
        need_play_record=body.need_play_record,
    )


@router.post("/files/documents", summary="获取文档列表（全部目录）")
def files_documents(body: TypeListRequest, client: ClientDep):
    return client.fs_document_list(
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
    )


@router.post("/files/recycle", summary="获取回收站列表")
def files_recycle(body: RecycleListRequest, client: ClientDep):
    return client.fs_recycle_files(
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
    )


@router.post("/files/detail", summary="获取文件详情")
def files_detail(body: FileIdRequest, client: ClientDep):
    return client.fs_detail(body.file_id)


_FIND_PAGE_SIZE = 500
_FIND_MAX_PAGES = 200


@router.post(
    "/files/find",
    summary="按名称查找文件/文件夹（返回 id）",
    description=(
        "在指定目录下按名称**精确**查找文件或文件夹，返回其 "
        "`file_id`、名称、父目录 id 及类型（文件类型）。\n\n"
        "- `dir_id`：不传 / `0` / 空串 都表示**从根目录**查找；传入具体 id 则在该目录下查找\n"
        "- 同一目录下名称唯一，因此最多命中一个；未找到时返回 `exists=false`\n"
        "- 自动分页拉取该目录直到命中或遍历完\n"
        "- `res_type`：`1` 只找文件，`2` 只找文件夹，不传则两者都找\n"
        "- 返回的 `parent_id` 为实际查找的父目录，**根目录返回 `0`**"
    ),
    response_model=FindByNameResponse,
)
def files_find(body: FindByNameRequest, client: ClientDep):
    parent = coerce_parent_id(body.dir_id)
    page = 0
    while page < _FIND_MAX_PAGES:
        resp = client.fs_files(
            parent_id=parent,
            page=page,
            page_size=_FIND_PAGE_SIZE,
            res_type=body.res_type,
        )
        data = (resp or {}).get("data") or {}
        items = data.get("list") or []
        for item in items:
            if item.get("fileName") == body.name:
                res_type = item.get("resType")
                return {
                    "exists": True,
                    "file_id": item.get("fileId"),
                    "name": item.get("fileName"),
                    "parent_id": item.get("parentId") or parent or 0,
                    "res_type": res_type,
                    "is_dir": res_type == 2 if res_type is not None else None,
                }
        total = data.get("total") or 0
        page += 1
        if not items or page * _FIND_PAGE_SIZE >= total:
            break
    return {
        "exists": False,
        "file_id": None,
        "name": body.name,
        "parent_id": parent or 0,
        "res_type": None,
        "is_dir": None,
    }


@router.post("/files/mkdir", summary="创建文件夹")
def files_mkdir(body: CreateDirRequest, client: ClientDep):
    return client.fs_create_dir(
        body.dir_name,
        parent_id=coerce_parent_id(body.parent_id),
        fail_if_name_exist=body.fail_if_name_exist,
    )


@router.post("/files/copy", summary="复制文件")
def files_copy(body: CopyMoveRequest, client: ClientDep):
    return client.fs_copy(
        coerce_file_ids(body.file_ids), parent_id=coerce_parent_id(body.parent_id)
    )


@router.post("/files/move", summary="移动文件")
def files_move(body: CopyMoveRequest, client: ClientDep):
    return client.fs_move(
        coerce_file_ids(body.file_ids), parent_id=coerce_parent_id(body.parent_id)
    )


@router.post("/files/rename", summary="重命名文件")
def files_rename(body: RenameRequest, client: ClientDep):
    return client.fs_rename(body.file_id, body.new_name)


@router.post("/files/delete", summary="删除文件（移入回收站/永久删除）")
def files_delete(body: FileIdsRequest, client: ClientDep):
    return client.fs_delete(coerce_file_ids(body.file_ids))


@router.post("/files/recycle/restore", summary="从回收站还原")
def files_recycle_restore(body: FileIdsRequest, client: ClientDep):
    return client.fs_recycle(coerce_file_ids(body.file_ids))


@router.post("/files/recycle/clear", summary="清空回收站")
def files_recycle_clear(client: ClientDep):
    return client.fs_clear_recycle_bin()


@router.post("/files/task/status", summary="获取任务状态")
def files_task_status(body: TaskIdRequest, client: ClientDep):
    return client.get_task_status(body.task_id)


@router.post(
    "/download/url",
    summary="获取文件下载直链",
    description=(
        "根据文件 file_id 获取带签名的 CDN 下载直链。\n\n"
        "- 返回 `data.signedURL` 即为可直接下载的直链（浏览器 / IDM / curl 均可用）\n"
        "- `file_id` 必须是文件（列表里 resType=1），文件夹（resType=2）需先打包\n"
        "- 直链有时效，请尽快使用；如需服务端转发请用 `GET /download/{file_id}`"
    ),
)
def download_url(body: FileIdRequest, client: ClientDep):
    return client.download_url(body.file_id)


def _close(resp: httpx.Response, http: httpx.Client) -> None:
    resp.close()
    http.close()


@router.get(
    "/download/{file_id}",
    summary="下载文件（服务端中转）",
    description=(
        "服务端自动解析下载直链并以流式转发文件内容，访问该 URL 即开始下载，"
        "无需自己处理 `signedURL`。适合直接给前端/脚本使用。"
    ),
)
def download(file_id: str, client: ClientDep):
    info = client.download_url(file_id)
    url = find_url(info)
    if not url:
        raise HTTPException(status_code=404, detail="无法解析下载链接")

    http = httpx.Client(follow_redirects=True, timeout=None)
    resp = http.send(http.build_request("GET", url), stream=True)
    if resp.status_code >= 400:
        _close(resp, http)
        raise HTTPException(status_code=resp.status_code, detail="下载失败")

    headers = {}
    disposition = resp.headers.get("content-disposition")
    if disposition:
        headers["content-disposition"] = disposition
    return StreamingResponse(
        resp.iter_bytes(chunk_size=1024 * 1024),
        media_type=resp.headers.get("content-type", "application/octet-stream"),
        headers=headers,
        background=BackgroundTask(_close, resp, http),
    )


_PLACEHOLDERS = {"string", "null", "none", "undefined", "n/a"}

_FALLBACK_CHUNK_SIZE = 8 * 1024 * 1024

_upload_sem_lock = threading.Lock()
_upload_sem: Optional[threading.BoundedSemaphore] = None


def _upload_semaphore(limit: int) -> threading.BoundedSemaphore:
    """进程内限制并发上传数（1 vCPU / 1 GB 内存的小机器）。"""
    global _upload_sem
    with _upload_sem_lock:
        if _upload_sem is None:
            _upload_sem = threading.BoundedSemaphore(max(1, limit))
        return _upload_sem


def _clean_form(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if text == "" or text.lower() in _PLACEHOLDERS:
        return None
    return text


def _resolve_chunk_size(value: Optional[int], settings: Settings) -> int:
    size = value or settings.upload_chunk_size or _FALLBACK_CHUNK_SIZE
    return size if size > 0 else _FALLBACK_CHUNK_SIZE


def _resolve_tmp_dir(settings: Settings) -> Optional[str]:
    raw = (settings.upload_tmp_dir or "").strip()
    if not raw:
        return None
    tmp_dir = Path(raw).expanduser()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_dir)


def _resolve_upload_path(raw: str, settings: Settings) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path = path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=404, detail=f"文件不存在: {raw}") from exc
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"不是文件: {raw}")

    root = (settings.upload_root or "").strip()
    if root:
        root_path = Path(root).expanduser()
        if not root_path.is_absolute():
            root_path = Path.cwd() / root_path
        root_path = root_path.resolve()
        if path != root_path and root_path not in path.parents:
            raise HTTPException(
                status_code=403, detail=f"路径不在允许的上传目录内: {root}"
            )
    return path


def _run_upload(client, path, name, parent_id, content_type, chunk_size, settings):
    with _upload_semaphore(settings.max_concurrent_uploads):
        try:
            return client.file_upload(
                path,
                name=name,
                parent_id=parent_id,
                content_type=content_type,
                chunk_size=chunk_size,
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502, detail=f"上游接口错误: {exc}"
            ) from exc
        except KeyError as exc:
            raise HTTPException(
                status_code=502, detail=f"上游返回缺少字段: {exc}"
            ) from exc


@router.post("/upload", summary="上传文件（multipart，自动秒传/分片）")
def upload(
    client: ClientDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
):
    file_name = _clean_form(name) or file.filename or "upload.bin"
    parent = coerce_parent_id(_clean_form(parent_id))
    mime = _clean_form(content_type) or file.content_type or "application/octet-stream"
    size = _resolve_chunk_size(chunk_size, settings)

    suffix = Path(file_name).suffix
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, dir=_resolve_tmp_dir(settings)
    )
    try:
        while chunk := file.file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.close()
        return _run_upload(
            client, tmp.name, file_name, parent, mime, size, settings
        )
    finally:
        Path(tmp.name).unlink(missing_ok=True)


@router.post(
    "/upload/path",
    summary="按服务器文件路径上传（推荐大文件）",
    description=(
        "直接读取服务器本地文件上传，无需 multipart，省去一份临时拷贝，"
        "适合 1GB+ 大文件。默认分片 8MB（可用 `chunk_size` 覆盖）。\n\n"
        "`file_path` 需对本服务进程可读；设置 `UPLOAD_ROOT` 可限制允许的根目录。"
    ),
)
def upload_by_path(body: UploadPathRequest, client: ClientDep, settings: SettingsDep):
    path = _resolve_upload_path(body.file_path, settings)
    file_name = _clean_form(body.name) or path.name
    mime = (
        _clean_form(body.content_type)
        or mimetypes.guess_type(str(path))[0]
        or "application/octet-stream"
    )
    size = _resolve_chunk_size(body.chunk_size, settings)
    return _run_upload(
        client,
        path,
        file_name,
        coerce_parent_id(body.parent_id),
        mime,
        size,
        settings,
    )
