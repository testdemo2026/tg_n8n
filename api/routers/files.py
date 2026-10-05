import tempfile
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from ..dependencies import ClientDep
from ..schemas import (
    CopyMoveRequest,
    CreateDirRequest,
    FileIdRequest,
    FileIdsRequest,
    FilesListRequest,
    RecycleListRequest,
    RenameRequest,
    TaskIdRequest,
    TypeListRequest,
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


def _clean_form(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if text == "" or text.lower() in _PLACEHOLDERS:
        return None
    return text


@router.post("/upload", summary="上传文件（自动秒传/分片）")
def upload(
    client: ClientDep,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    chunk_size: int = Form(5 * 1024 * 1024),
):
    file_name = _clean_form(name) or file.filename or "upload.bin"
    parent = coerce_parent_id(_clean_form(parent_id))
    mime = _clean_form(content_type) or file.content_type or "application/octet-stream"
    if not chunk_size or chunk_size <= 0:
        chunk_size = 5 * 1024 * 1024

    suffix = Path(file_name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        while chunk := file.file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.close()
        try:
            return client.file_upload(
                tmp.name,
                name=file_name,
                parent_id=parent,
                content_type=mime,
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
    finally:
        Path(tmp.name).unlink(missing_ok=True)
