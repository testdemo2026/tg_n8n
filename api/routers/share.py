from fastapi import APIRouter

from guangyaclient import GuangyaClient

from ..dependencies import ClientDep
from ..schemas import (
    ShareAccessTokenRequest,
    ShareCreateRequest,
    ShareDeleteRequest,
    ShareDownloadUrlRequest,
    ShareFilesListRequest,
    ShareFilesSizeRequest,
    ShareListRequest,
    ShareRestoreRequest,
    ShareSummaryRequest,
    ShareUpdateRequest,
)
from ..utils import coerce_file_ids

router = APIRouter(tags=["share"])


@router.post("/share/create", summary="创建分享")
def share_create(body: ShareCreateRequest, client: ClientDep):
    return client.share_create(
        coerce_file_ids(body.file_ids),
        body.title,
        validate_duration=body.validate_duration,
        share_type=body.share_type,
        code=body.code,
        auto_fill_code=body.auto_fill_code,
        traffic_limit=body.traffic_limit,
        max_restore_count=body.max_restore_count,
        download_type=body.download_type,
    )


@router.post("/share/list", summary="获取我的分享列表")
def share_list(body: ShareListRequest, client: ClientDep):
    return client.share_user_list(
        page=body.page,
        page_size=body.page_size,
        order_type=body.order_type,
        sort_type=body.sort_type,
    )


@router.post("/share/update", summary="更新分享")
def share_update(body: ShareUpdateRequest, client: ClientDep):
    return client.share_update(
        body.share_id,
        body.title,
        validate_duration=body.validate_duration,
        share_type=body.share_type,
        code=body.code,
        auto_fill_code=body.auto_fill_code,
        traffic_limit=body.traffic_limit,
        max_restore_count=body.max_restore_count,
        download_type=body.download_type,
    )


@router.post("/share/delete", summary="删除分享")
def share_delete(body: ShareDeleteRequest, client: ClientDep):
    return client.share_delete(body.ids)


@router.post("/share/restore", summary="转存分享文件")
def share_restore(body: ShareRestoreRequest, client: ClientDep):
    return client.share_restore(
        body.access_token, coerce_file_ids(body.file_ids), parent_id=body.parent_id
    )


@router.post("/share/download-url", summary="获取分享文件下载链接")
def share_download_url(body: ShareDownloadUrlRequest, client: ClientDep):
    return client.share_download_url(body.file_id, body.access_token)


@router.post("/share/files-size", summary="获取分享文件大小")
def share_files_size(body: ShareFilesSizeRequest, client: ClientDep):
    return client.share_files_size(
        body.access_token, coerce_file_ids(body.file_ids), download=body.download
    )


@router.post("/share/summary", summary="获取分享摘要（无需登录）")
def share_summary(body: ShareSummaryRequest):
    return GuangyaClient.share_summary(body.share_id)


@router.post("/share/access-token", summary="获取分享访问令牌（无需登录）")
def share_access_token(body: ShareAccessTokenRequest):
    return GuangyaClient.share_access_token(body.share_id, body.code)


@router.post("/share/files", summary="获取分享页文件列表（无需登录）")
def share_files(body: ShareFilesListRequest):
    return GuangyaClient.share_files_list(
        body.access_token,
        parent_id=body.parent_id,
        page=body.page,
        page_size=body.page_size,
        order_by=body.order_by,
        sort_type=body.sort_type,
    )
