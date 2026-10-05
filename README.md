# 光鸭云盘 Python 客户端

[![PyPI version](https://img.shields.io/pypi/v/guangyaclient)](https://pypi.org/project/guangyaclient/)
[![Python version](https://img.shields.io/pypi/pyversions/guangyaclient)](https://pypi.org/project/guangyaclient/)
[![License](https://img.shields.io/github/license/DDSRem-Dev/guangyaclient)](./LICENSE)

[光鸭云盘](https://www.guangyapan.com) Python 客户端库。

## 安装

```bash
pip install guangyaclient
```

## 快速开始

```python
from guangyaclient import GuangyaClient

# 已有 token 直接初始化
client = GuangyaClient(access_token="your_token")

# 或使用短信登录（会自动更新 client 的 token）
client = GuangyaClient()
client.login_sms("+86 13800138000")
```

## 认证

### 短信登录全流程

```python
client = GuangyaClient()

# 一键完成登录，默认通过 input() 读取验证码
client.login_sms("+86 13800138000")

# 自动化场景（传入回调）
client.login_sms(
    "+86 13800138000",
    get_code=lambda: sms_service.get_code(),
)
```

登录成功后 `client.token`、`client.token_expires_at`、`client.refresh_token_value` 自动更新。

### 手动刷新 Token

```python
client.refresh_token()  # 使用已存储的 refresh_token
```

`request()` 会在 token 过期时自动刷新，也会在收到 401 时自动重试。

## API 参考

### 用户

| 方法 | 说明 |
|------|------|
| `user_info()` | 获取当前登录用户信息 |

### 文件管理

| 方法 | 说明 |
|------|------|
| `fs_files(parent_id, ...)` | 获取文件列表 |
| `fs_image_list(parent_id, ...)` | 获取图片列表 |
| `fs_video_list(parent_id, ...)` | 获取视频列表 |
| `fs_document_list(parent_id, ...)` | 获取文档列表 |
| `fs_recycle_files(...)` | 获取回收站文件列表 |
| `fs_detail(file_id)` | 获取文件详情 |
| `fs_create_dir(dir_name, parent_id)` | 创建文件夹 |
| `fs_copy(file_ids, parent_id)` | 复制文件 |
| `fs_move(file_ids, parent_id)` | 移动文件 |
| `fs_rename(file_id, new_name)` | 重命名文件 |
| `fs_delete(file_ids)` | 删除文件（移入回收站或永久删除） |
| `fs_recycle(file_ids)` | 从回收站还原文件 |
| `fs_clear_recycle_bin()` | 清空回收站 |
| `get_task_status(task_id)` | 获取任务状态 |

### 下载

| 方法 | 说明 |
|------|------|
| `download_url(file_id)` | 获取文件下载链接 |

### 上传

```python
# 自动处理小文件直传、大文件分片上传和秒传
result = client.file_upload("/path/to/file.mp4", parent_id=123)
```

| 方法 | 说明 |
|------|------|
| `file_upload(file_path, parent_id)` | 上传文件（全流程） |
| `upload_token(name, file_size, ...)` | 获取上传 token |
| `check_can_flash_upload(task_id, file_path)` | 检查是否可秒传 |
| `cdn_upload(file_path, token_data, ...)` | CDN 分片上传 |
| `upload_info(task_id)` | 获取上传任务信息 |

### 云下载

| 方法 | 说明 |
|------|------|
| `cloud_task_list(page, page_size, status)` | 获取云下载任务列表 |
| `cloud_resolve_url(url)` | 解析 HTTP/磁力/ed2k 链接 |
| `cloud_resolve_torrent(torrent)` | 解析 BT 种子文件 |
| `cloud_create_task(url, parent_id)` | 创建云下载任务 |

### 分享

| 方法 | 说明 |
|------|------|
| `share_create(file_ids, ...)` | 创建分享 |
| `share_user_list(page, page_size)` | 获取我的分享列表 |
| `share_update(share_id, ...)` | 更新分享设置 |
| `share_delete(ids)` | 删除分享 |
| `share_restore(access_token, file_ids, parent_id)` | 转存分享文件 |
| `share_download_url(file_id, access_token)` | 获取分享文件下载链接 |
| `share_files_size(access_token, file_ids)` | 获取分享文件大小 |
| `share_summary(share_id)` | 获取分享摘要（无需登录） |
| `share_access_token(share_id, code)` | 获取分享访问令牌（无需登录） |
| `share_files_list(access_token, ...)` | 获取分享页文件列表（无需登录） |

### 工具函数

```python
from guangyaclient import calculate_gcid, generate_did, generate_traceparent, FILE_TYPE, FILE_TYPE_NAME

# 文件类型常量
FILE_TYPE["图片"]   # 1
FILE_TYPE["视频"]   # 2
FILE_TYPE_NAME[1]   # "图片"
```

## HTTP API 服务（FastAPI）

把客户端封装成 HTTP 接口，方便用任意语言/脚本操作云盘文件。

### 安装与启动

```bash
# 创建虚拟环境并安装（含 API 依赖）
uv venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
uv pip install -e ".[api]"

# 配置：复制并按需修改
copy .env.example .env            # Windows
# cp .env.example .env            # macOS / Linux

# 启动
python -m api.main
# 或：uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

- 接口文档：http://127.0.0.1:8000/docs
- 配置读取自仓库根目录 `.env`（`ACCESS_TOKEN` / `REFRESH_TOKEN` / `DEVICE_ID` / `API_KEY` 等）
- 登录或刷新后的 token 会持久化到 `data/tokens.json`（含过期时间），重启无需重新登录
- 设置了 `API_KEY` 时，所有请求需带请求头 `X-API-Key`

### Docker 部署

仓库已包含 `Dockerfile` 与 `docker-compose.yml`。

```bash
# 1) 准备配置
cp .env.example .env
#   编辑 .env：至少设置 API_KEY（保护接口，强烈建议）
#   ACCESS_TOKEN/REFRESH_TOKEN 可留空，登录后自动写入 data/tokens.json

# 2) 构建并启动
docker compose up -d --build

# 3) 查看日志 / 状态
docker compose logs -f
docker compose ps

# 接口只在 tgapi_n8n_network 内可访问：
#   同网络容器 -> http://guangya-api:8000/docs
```

说明：
- 不映射宿主机端口，**仅内部网络可访问，公网无法访问**。
- 容器内监听 `0.0.0.0:8000`，同网络其它容器用 `http://guangya-api:8000` 访问。
- 数据目录挂载到宿主机 `/opt/guangya_data`（`/opt/guangya_data:/app/data`），token 持久化，重启不丢；
  部署前先 `sudo mkdir -p /opt/guangya_data && sudo chown 1000:1000 /opt/guangya_data`。
- 默认以 `user: "1000:1000"` 运行，生成的 token 文件属主即 1000（与目录一致）；不需要可删掉该行（则用 root）。
- 已加入外部网络 `tgapi_n8n_network`；该网络需已存在，否则先创建：`docker network create tgapi_n8n_network`。
- 配置全部走 `.env`（compose 的 `env_file`），无需改镜像。
- 停止：`docker compose down`（数据仍在 `/opt/guangya_data`）。
- 部署到无外网的服务器时，可在本地 `docker build -t guangyaclient-api:latest .` 后
  `docker save` 导出、服务器 `docker load` 导入，再 `docker compose up -d`。
- 单独用 `docker run`：
  ```bash
  docker build -t guangyaclient-api:latest .
  docker run -d --name guangya-api --restart always \
    --network tgapi_n8n_network \
    --user 1000:1000 \
    -e APP_HOST=0.0.0.0 \
    -v /opt/guangya_data:/app/data \
    -e API_KEY=your_key \
    guangyaclient-api:latest
  ```

### 短信登录（两步，符合验证码交互）

验证码是发到手机后才拿到的，所以分两步：

```bash
# 第 1 步：发短信，拿到 session_id
curl -X POST http://127.0.0.1:8000/auth/sms/start \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+86 13800138000"}'
# -> {"status":"sent","session_id":"xxxx","send":{...}}

# 第 2 步：手机收到验证码后提交
curl -X POST http://127.0.0.1:8000/auth/sms/confirm \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxxx", "code": "123456"}'
# -> {"status":"ok","access_token":"...","refresh_token":"..."}
```

`session_id` 有效期 10 分钟。若第 1 步返回 `captcha_required`，需先完成人机验证。

### 用已有 Token 登录

如果已从别处拿到凭据，可直接用接口写入（会持久化到 `data/tokens.json`）：

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"access_token":"eyJ...","refresh_token":"gy.xxxx"}'
```

也可以直接在 `.env` 里填 `ACCESS_TOKEN` / `REFRESH_TOKEN` / `DEVICE_ID` 后重启。

### Token 过期处理

- access_token 过期时，客户端会**自动**用 refresh_token 刷新并用新 token 重试，新 token 会自动落盘。
- 若 refresh_token 也失效（返回 401 且无法刷新），重新走上面的短信登录即可。
- 也可手动 `POST /auth/refresh`。

### 文件管理

| 库方法 | HTTP 接口 | 说明 |
|--------|-----------|------|
| `fs_files(parent_id, ...)` | `POST /files/list` | 获取文件列表 |
| `fs_image_list(...)` | `POST /files/images` | 获取图片列表（全部目录） |
| `fs_video_list(...)` | `POST /files/videos` | 获取视频列表（全部目录） |
| `fs_document_list(...)` | `POST /files/documents` | 获取文档列表（全部目录） |
| `fs_recycle_files(...)` | `POST /files/recycle` | 获取回收站文件列表 |
| `fs_detail(file_id)` | `POST /files/detail` | 获取文件详情 |
| `fs_create_dir(dir_name, parent_id)` | `POST /files/mkdir` | 创建文件夹 |
| `fs_copy(file_ids, parent_id)` | `POST /files/copy` | 复制文件 |
| `fs_move(file_ids, parent_id)` | `POST /files/move` | 移动文件 |
| `fs_rename(file_id, new_name)` | `POST /files/rename` | 重命名文件 |
| `fs_delete(file_ids)` | `POST /files/delete` | 删除文件（移入回收站或永久删除） |
| `fs_recycle(file_ids)` | `POST /files/recycle/restore` | 从回收站还原文件 |
| `fs_clear_recycle_bin()` | `POST /files/recycle/clear` | 清空回收站 |
| `get_task_status(task_id)` | `POST /files/task/status` | 获取任务状态 |
| `file_upload(...)` | `POST /upload` | 上传文件（multipart，自动秒传/分片） |
| `download_url(file_id)` | `POST /download/url` | 获取文件下载直链 |
| （服务端中转） | `GET /download/{file_id}` | 下载文件（流式转发） |

请求体字段与库方法参数同名（蛇形命名），例如：

```bash
# 文件列表
curl -X POST http://127.0.0.1:8000/files/list \
  -H "Content-Type: application/json" \
  -d '{"parent_id": null, "page": 0, "page_size": 50}'

# 新建文件夹
curl -X POST http://127.0.0.1:8000/files/mkdir \
  -H "Content-Type: application/json" \
  -d '{"dir_name": "新建文件夹", "parent_id": null}'

# 上传文件
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@D:/test.mp4" -F "parent_id=" 
```

### 其他接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/auth/sms/start` `/auth/sms/confirm` | 手机验证码登录（发码 + 提交验证码） |
| POST | `/auth/token` | 使用 access_token / refresh_token 登录 |
| POST | `/auth/refresh` | 手动刷新 access_token |
| GET | `/auth/user` | 获取当前登录用户信息 |
| POST | `/share/*` | 分享相关 |
| POST | `/cloud/*` | 云下载相关 |

## License

[MIT](./LICENSE)
