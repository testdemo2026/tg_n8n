from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    access_token: str = ""
    refresh_token: str = ""
    device_id: str = ""
    api_key: Optional[str] = None
    token_file: str = "data/tokens.json"

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = False
    log_level: str = "info"

    # ===== 上传（默认按 1 vCPU / 1 GB 内存 / 24 GB 磁盘调优） =====
    upload_chunk_size: int = Field(
        8 * 1024 * 1024,
        description="上传分片大小（字节）。默认 8MB：1GB 文件约 128 片，内存占用可控。",
    )
    upload_timeout: float = Field(
        300.0,
        description=(
            "上传等长耗时请求的读写超时（秒）。httpx 默认仅 5 秒，"
            "1GB+ 文件上传必被中断，故放宽到 5 分钟。"
        ),
    )
    upload_tmp_dir: str = Field(
        "data/tmp",
        description="分片上传临时目录；放数据盘，避免写满 /tmp。留空则用系统临时目录。",
    )
    upload_root: Optional[str] = Field(
        None,
        description="按路径上传时允许访问的根目录；留空不限制（仅内网 + API_KEY 保护）。",
    )
    max_concurrent_uploads: int = Field(
        2,
        description="同时进行的上传任务上限，避免 1GB 内存的小机器被并发占满。",
    )
    max_upload_jobs: int = Field(
        20,
        description=(
            "异步上传（/upload/path/async）同时在册的任务上限（排队 + 运行中）。"
            "超过则拒绝新任务，避免小机器被大量后台线程拖垮。"
        ),
    )
    upload_job_ttl: float = Field(
        3600.0,
        description="异步上传任务结束后结果保留时长（秒），过期自动清理。",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
