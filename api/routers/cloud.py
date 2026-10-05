import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from ..dependencies import ClientDep
from ..schemas import CloudCreateTaskRequest, CloudResolveUrlRequest, CloudTaskListRequest
from ..utils import coerce_parent_id

router = APIRouter(tags=["cloud"])


@router.post("/cloud/tasks", summary="获取云下载任务列表")
def cloud_tasks(body: CloudTaskListRequest, client: ClientDep):
    return client.cloud_task_list(
        page=body.page, page_size=body.page_size, status=body.status
    )


@router.post("/cloud/resolve-url", summary="解析云下载链接")
def cloud_resolve_url(body: CloudResolveUrlRequest, client: ClientDep):
    return client.cloud_resolve_url(body.url)


@router.post("/cloud/resolve-torrent", summary="解析 BT 种子文件")
def cloud_resolve_torrent(client: ClientDep, torrent: UploadFile = File(...)):
    suffix = Path(torrent.filename or "file.torrent").suffix or ".torrent"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        while chunk := torrent.file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.close()
        return client.cloud_resolve_torrent(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


@router.post("/cloud/create-task", summary="创建云下载任务")
def cloud_create_task(body: CloudCreateTaskRequest, client: ClientDep):
    return client.cloud_create_task(body.url, parent_id=coerce_parent_id(body.parent_id))
