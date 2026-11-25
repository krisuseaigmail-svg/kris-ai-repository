# 第 1 轮开发说明

实现以 `功能说明.md`、`发布构建标准.md`、`部署说明.md`、`AGENT提示词.md` 为准。`docs/` 里的旧设计没有当作实现输入。没有改 `delivery-ledger/`，没有提交 git。

## 已实现

- 空间与资产的创建、修改、删除，矩阵、层数、防环、宿主二选一、U 位重叠与机柜高度。
- 首页、空间列表/详情、只读机柜 U 表、资产列表（类型、空间、关键字同时生效，每页 200 条）。
- Excel：`/assets/export.xlsx` 与 `/spaces/{id}/export.xlsx`，列、排序、文件名和 `Content-Disposition` 按第 8 节。
- 启动前第 2.2 节跨库检查（`PRODUCT_CODE`、库 `ledger`、每个库单独连接查 `public.deliveries`）。`GET /healthz` 正文为 `ok`。
- 校验失败 HTTP 400 且页面含规格原句；成功 303；不存在 404。
- 部署：`deploy/lib.sh` 的 `assert_volume_exclusive` 按规格粘贴；`pg-guard.sh`；install/upgrade/up/backup/restore/package.sh；compose 项目名 `asset-ledger`，卷名 `delivery_ledger_pgdata`，`pull_policy: never`，`APP_PORT` 默认 8010，postgres 不映射端口。
- 结构版本 `0.1.0` 只记录初始表，`migrate.py` 没有删除数据的语句。

## 本机验证

本机默认 `python3` 是 3.9.6，没有 3.12。5432 上是客户交付台账的 Postgres，不能拿来清空。测试使用独立容器 `asset-ledger-pytest-pg`（端口 5433，卷 `asset_ledger_pytest_pgdata`，与 `delivery_ledger_pgdata` 无关）。

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

结果：55 passed。

同一连接串可以起本地进程：

```bash
PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

规格里的 5432 地址会连到交付台账那个实例。那里有库 `ledger`，本应用会按第 2.2 节退出，这是预期行为。

## 未在本机跑通的部分

- 没有执行 `./deploy/package.sh`。`vendor/wheels/` 只有占位文件，按规格在没有 wheel 时镜像构建应失败。
- 没有对真实 compose 做安装、升级、备份恢复。验收 26–30、36 的现场行为由脚本和替身 `docker` 覆盖：卷标签不对、镜像名 `delivery-ledger`、`COMPOSE_PROJECT_NAME` 不对时拒绝且不 up；`pg-guard.sh` 对无标记的已初始化目录拒绝，并在首次出现 `PG_VERSION` 时写入 `asset_ledger.owner`。
- 升级后「空间和资产仍在、`.env` 密码不变」没有用一套真实栈演练。`replace_code` 单测确认不覆盖已有 `.env` 和 `backups/`。脚本里没有 `down -v`，也不删除标记文件。

## 本版边界

没有登录、Excel 导入、机柜拖拽或第二块 MAC。资产删除不要求确认值；空间删除必须带 `confirm=yes`。仓库柜子可以放服务器。
