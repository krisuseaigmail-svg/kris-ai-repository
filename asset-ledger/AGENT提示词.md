# 机房/办公资产录入台账（asset-ledger）— Agent 工作提示词

把本文作为后续 Agent 的**项目指令**。改代码、发版、修缺陷前先读本文，再按需打开被引用的规格文档。不要凭记忆发明业务规则。

---

## 1. 你是谁、做什么

你在维护 **机房/办公资产录入台账**：可信内网里的中文 Web 应用，在线录入服务器、交换机、防火墙、硬盘的位置和编号，并导出 Excel。

工作目录：仓库内独立目录 `asset-ledger/`。  
初版 `VERSION` 为 `0.1.0`。当前版本以该文件为准。

这不是客户交付台账。不要改 `delivery-ledger/` 的代码、规格、镜像和安装脚本。不要把交付台账的客户、交付、拓扑、机柜拖拽搬进本产品。

## 2. 规格优先级（冲突时按此顺序）

1. **`功能说明.md`** — 业务、空间与挂载、卷门禁算法、验收（权威）。
2. **`发布构建标准.md`** — 离线 amd64 打包、平滑升级、历史数据保留（硬性）。
3. **`部署说明.md`** — 现场安装、升级、备份，以及同机红线。
4. 代码与测试 — 行为应与上述文档一致；改行为必须先改规格（或同步改规格）。
5. `docs/` 下各轮设计与测试报告 — 历史上下文，**不覆盖**现行规格。第 1 轮、第 2 轮正文和草案都不是实现输入。

禁止在 `功能说明.md` 中增加「不做」专节。范围外能力写在「后续迭代」里。

## 3. 产品与运行环境（摘要）

- **用户**：可信内网资产管理员。本版不设登录。
- **栈**：Python 3.12、FastAPI、Jinja2 服务端渲染、PostgreSQL 16、容器内 uvicorn。没有前端构建，机柜页是只读 U 表。
- **运行机**：SUSE Linux Enterprise Server 15.6，x86_64。镜像架构名 `linux/amd64`。
- **离线**：运行机可以没有 DNS，也不访问 `registry-1.docker.io`。compose 的 `pull_policy` 是 `never`。
- **库**：只用 compose 内的 `postgres:16`。库名和账号名是 `asset_ledger`。应用通过服务名 `postgres:5432` 连接。postgres **不**映射宿主机端口。
- **卷名**：`delivery_ledger_pgdata`。本产品独占。禁止与客户交付台账同机挂载。所有权靠《功能说明》第 2 节的脚本预检、`pg-guard.sh` 和 `asset_ledger.owner`，不是靠改卷名。
- **项目名**：compose 始终 `docker compose -p asset-ledger`。镜像名 `asset-ledger:<版本>`。`PRODUCT_CODE=asset-ledger`。
- **postgres 命令**：compose 里 `entrypoint` 是 `pg-guard.sh`，`command` 是 `["postgres"]`。两条都要写。只改 entrypoint 时 Compose 丢掉镜像 CMD，容器会马上退出。

空间、资产宿主、Excel 列和提示语以《功能说明》第 4–8 节为准，本文不复述第二套。

## 4. 绝对禁止（违反即错误）

- 把卷名改成 `asset_ledger_pgdata` 或其它名字；删除该卷；对现场执行 `docker compose down -v`。
- 删除或改写 PGDATA 里的 `asset_ledger.owner`；在已经有 `PG_VERSION` 却没有合法标记时启动 postgres。空目录首次 initdb 按《功能说明》第 2.3 节第 1 步，在 `pg_isready` 成功之前写入标记。
- 在 `install.sh`、`upgrade.sh`、`up.sh` 里各写一份卷检查。只允许调用 `deploy/lib.sh` 的 `assert_volume_exclusive`。
- 不用 `-p asset-ledger` 就执行 compose；在 `COMPOSE_PROJECT_NAME` 不是 `asset-ledger` 时继续启动。
- 在运行机直接 `docker compose up` / `build` / `pull` 当作安装或升级手段。
- 与客户交付台账装在同一 Docker 宿主机，或在本产品之后再装客户交付台账。对方不会自动拒绝同名卷；不要把「后装也会自动失败」写进验收或当成已实现的互锁。
- 升级时覆盖现场 `.env`，或清空已有空间和资产。
- 在 `migrate.py` 里删除列、删表、truncate，或任何丢掉已录入数据的语句。迁移只在列表末尾追加。
- 建表之前不按《功能说明》第 2.2 节逐个库 `CONNECT` 就查 `deliveries`。只查当前库或只查维护库的 `pg_tables` 不算做完。
- 把 arm64 或「标签像 amd64、内容是 arm64」的镜像打进发布包。
- 改业务却不改 `功能说明.md` 的验收节；或规格写了却不实现、不测。
- 改 `delivery-ledger/`，除非用户点名。
- 未经用户要求执行 `git commit` / `git push`。
- 给本版加登录、Excel 导入、第二块 MAC、自动发现，或把仓库柜子改成不能放服务器。这些要先改规格里的「后续迭代」并得到确认。

## 5. 代码地图

| 路径 | 职责 |
| --- | --- |
| `app/main.py` | 入口。先做第 2.2 节集群检查，再建表和迁移。`/healthz` |
| `app/routes.py` | HTTP 路由与表单。`/assets/new`、`/assets/export.xlsx` 先于 `/assets/{id}` |
| `app/services.py` | 写入、校验、中文错误。完整性错误译成规格里的句子，HTTP 400 |
| `app/domain.py` | 空间矩阵、资产宿主、层数、U 区间 |
| `app/models.py` | SQLAlchemy 模型。主键为整数 |
| `app/present.py` | 首页计数、空间路径、机柜 U 表、Excel 行 |
| `app/migrate.py` | 结构迁移，只追加 |
| `app/formtext.py` | 表单 UTF-8 误解码修复 |
| `app/templates/` | Jinja2。语言为简体中文 |
| `app/static/app.css` | 样式。本版机柜不拖拽，不要加 `rack.js` |
| `deploy/lib.sh` | `assert_volume_exclusive`、`compose`、`write_env`、`backup_to`。三份启动脚本都 source 它 |
| `deploy/pg-guard.sh` | postgres 入口包装。无 `asset_ledger.owner` 则拒开库 |
| `deploy/package.sh` | 离线 amd64 包，含 create + commit 压扁 |
| `deploy/install.sh` / `upgrade.sh` / `up.sh` | 只调用 `assert_volume_exclusive`，再 `compose up` |
| `deploy/backup.sh` / `restore.sh` | `db.sql` + `VERSION`。恢复不删标记文件，不 `down -v` |
| `tests/` | pytest。库名 `asset_ledger_test`，禁止指向现场卷 |
| `vendor/wheels/` | 打包用 wheel。运行机不 pip |

## 6. 改功能时怎么做

1. 先读 `功能说明.md` 对应章节。要新行为就先改规格和验收，再改代码与测试。
2. 矩阵、层数、宿主、U 重叠放在 `domain.py` / `services.py`。路由保持薄。
3. 改表：改 `models.py`，在 `migrate.py` **末尾**追加版本，并在《功能说明》第 2 节的结构版本列表写同一句。
4. 卷、入口包装、`.env`、备份恢复：以《功能说明》第 2 节的命令和键为准，不要换一套提示句。
5. 校验失败返回 400 和规格里的那一句，数据库不变。成功创建或修改返回 303。不存在返回 404。
6. 表单先去掉首尾空白，长度为 0 视为未填。不要把只含空格的占用高度报成「占用高度无效」。

## 7. 测试

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5432/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

- 验收对齐 `功能说明.md` 第 9 节。
- 这个 URL 必须指向独立的 Postgres。禁止对卷 `delivery_ledger_pgdata` 上的业务库跑会清空数据的测试。
- 测试实例里不要预置库 `ledger` 或表 `deliveries`，除非该用例就是在验证冲突退出。
- 同一 U 的并发用例是两个并行 HTTP POST，不是先后两次请求。
- pytest 可以清空 `asset_ledger_test`。不得清空现场库。

## 8. 发版与升级（必须遵守《发布构建标准》）

### 发版

1. 递增 `VERSION`、`pyproject.toml`、compose 默认 `APP_VERSION`。
2. 有迁移则追加 `migrate.py` 并更新规格。
3. 在能访问镜像站的机器上执行 `./deploy/package.sh`。脚本把镜像压成真正的 `linux/amd64`。
4. 核对两镜像 `Architecture=amd64`，且 `uname -m` 为 `x86_64`。产物是 `dist/asset-ledger-<VERSION>.tar.gz`。

### 现场升级（保留已录入的空间和资产）

```bash
tar -xzf asset-ledger-<新版本>.tar.gz -C /tmp
sudo /tmp/asset-ledger/deploy/upgrade.sh /opt/asset-ledger
```

升级脚本会：先做与安装相同的卷预检 → 备份 `db.sql` 和 `VERSION` → 换程序与镜像 → **保留** `.env`、`backups/` 和卷 → 保留 `asset_ledger.owner` → 健康检查。  
已有资产编号、序列号和空间必须仍在。

首次安装才用 `install.sh`。目录里已有 `VERSION` 时安装脚本退出，提示使用 `upgrade.sh`。

## 9. 本地开发常用

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5432/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

本地 uvicorn 不代替现场的 `pg-guard.sh`。测无标记数据目录时，用 compose 里的包装入口，而不是跳过它直接跑官方 `docker-entrypoint.sh`。

健康检查：`GET /healthz`，正文是 `ok`。

## 10. 已知产品边界（不要当成缺陷改规格）

- 无登录。只在可信内网开放端口。删除前要备份，页面删了不能恢复。
- 一块 MAC。IP 可以重复。没有 Excel 导入。
- 机柜只读、整宽、只记正面。半 U 和背面会算作重叠。
- 层数最多 4。仓库下的柜子可以放服务器。机房下不能建柜子。
- 本产品先安装之后，客户交付台账若再装到这台机器，对方会挂上同名卷。规格要求人不要这样装，不是要求本产品把对方的安装脚本变成失败。

## 11. 回复与协作习惯

- 对用户默认简体中文，直接、简洁。
- 改前说明影响面。涉及卷、`.env`、`asset_ledger.owner` 时写明是否触碰这三处。
- 不要主动 commit。用户要求提交时再按仓库提交规范执行。
- 设计与测试分轮时：实现以现行三份规格为准；测试不采信自述。

## 12. 一句话总则

**规格驱动、迁移只追加、升级不丢数、镜像必须真 amd64、卷名不改但无标记拒开库、内网台账不做登录。**
