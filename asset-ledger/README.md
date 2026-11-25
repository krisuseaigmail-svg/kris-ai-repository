# 机房/办公资产录入台账（asset-ledger）

Python / FastAPI / Jinja2 / PostgreSQL 16。容器内 uvicorn，默认宿主机端口 **8010**。

规格见同目录《功能说明》《部署说明》《发布构建标准》《AGENT提示词》。

## 快速预览（有外网）

```bash
cd asset-ledger
cp .env.example .env
# 把 .env 里的 PASSWORD 改成实际密码；DATABASE_URL 主机名保持 postgres
docker compose -f docker-compose.preview.yml --env-file .env up -d --build
curl -fsS http://127.0.0.1:8010/healthz   # 应为 ok
```

浏览器打开 `http://127.0.0.1:8010/`。停止：

```bash
docker compose -f docker-compose.preview.yml --env-file .env down
```

预览卷名是 `asset_ledger_preview_pgdata`，不会创建生产卷 `delivery_ledger_pgdata`。

## 现场离线安装（SUSE x86_64）

使用发布包 `dist/asset-ledger-<版本>.tar.gz` 与 `deploy/install.sh`。见《部署说明》。生产 compose 卷名固定为 `delivery_ledger_pgdata`，不要与客户交付台账同机部署。

## 本机 pytest

需要独立 PostgreSQL（不要指向现场卷）。示例：

```bash
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```
