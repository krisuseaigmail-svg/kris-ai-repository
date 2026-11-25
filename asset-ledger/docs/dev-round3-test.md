# 第 3 轮测试报告（测试模型，不采信开发自述）

工作目录：`asset-ledger/`。对照：`docs/dev-round2-test.md` 强制项、规格四件套（`功能说明.md` / `发布构建标准.md` / `部署说明.md` / `AGENT提示词.md`）。`docs/dev-round3.md` 只作对照与临时卷冒烟证据。未改业务代码，未改 `delivery-ledger/`，未 git commit。未创建、未删除卷 `delivery_ledger_pgdata`，未对 `delivery-ledger-pg` 执行 `down -v`。

## 结论

**通过。**

可按《部署说明》在**干净的 SUSE 15.6（x86_64）Docker 宿主机**上试用安装。本机已有客户交付台账容器，本轮没有用规格卷名跑完整 `install.sh`；官方安装/升级路径采信开发方 `scripts/smoke-isolated.sh` 临时卷证据。

## 本轮怎么跑

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

结果：**64 passed**（8.62s）。解释器仍是本机 3.9.6。测试库：容器 `asset-ledger-pytest-pg`，端口 **5433**，库 `asset_ledger_test`。5432 上的 `delivery-ledger-pg` 未写入。

发布包抽查：

```bash
ls -lh dist/asset-ledger-0.1.0.tar.gz
tar tzf dist/asset-ledger-0.1.0.tar.gz | head
docker image inspect asset-ledger:0.1.0 --format '{{.Architecture}}'
docker image inspect postgres:16 --format '{{.Architecture}}'
docker run --rm --platform linux/amd64 asset-ledger:0.1.0 uname -m
docker run --rm --platform linux/amd64 --entrypoint uname postgres:16 -m
```

## 第 2 轮强制项闭合表

| # | 强制项 | 状态 | 独立证据 |
| --- | --- | --- | --- |
| 1 | 打发布包，两镜像 amd64 / x86_64 | **闭合** | `dist/asset-ledger-0.1.0.tar.gz` 约 213MB（mtime Nov 12）。包内 `images/asset-ledger-images-amd64.tar.gz`。本机标签 `asset-ledger:0.1.0`、`postgres:16` 均为 `Architecture=amd64`，`uname -m=x86_64`。从包内镜像 config blob 读到 `architecture=amd64` / `os=linux`（`asset-ledger:0.1.0` 与 `postgres:16` 各一份），不是只看本地未压扁标签 |
| 2 | 官方 `install.sh` / `upgrade.sh` 各一次 | **采信临时卷** | 本机 `delivery-ledger-pg` 仍在跑（镜像标签 `postgres:16`、匿名卷，**没有**卷 `delivery_ledger_pgdata`）。按规格第 2.1 节算法看不见它，直接跑仓库 `install.sh` 仍会创建生产卷名，之后再装客户交付台账会挂上该卷。本轮因此不在这台开发机上用生产卷名安装。`scripts/smoke-isolated.sh` 存在；本轮抽跑被环境拦截，未启动官方栈。按任务说明采信 `docs/dev-round3.md`：覆盖卷 `asset_ledger_smoke_pgdata`、项目名仍是 `asset-ledger`，`/healthz` 为 `ok`，写入「冒烟机房」，同版本 `upgrade.sh` 后记录与 `.env` 密码仍在，`asset_ledger.owner` 去掉换行是 `asset-ledger`，卷标签 `com.docker.compose.project=asset-ledger`，生产卷始终未出现 |
| 3 | 《功能说明》第 2 节写 `command: ["postgres"]` | **闭合** | 第 2 节原文：`command` 是 `["postgres"]`，并说明只改 entrypoint、不写 command 时包装进程立刻退出。`docker-compose.yml`（仓库与包内）均为 `command: ["postgres"]`。`test_spec_requires_postgres_command`、`test_compose_contract` 在 64 条里绿。`发布构建标准.md` / `部署说明.md` / `AGENT提示词.md` 同样有该句 |
| 4 | pytest 钉住 wheels | **闭合** | `test_vendor_wheels_are_linux_amd64` 绿。包内 `vendor/wheels/` 含 `openpyxl-3.1.5-py2.py3-none-any.whl`、`psycopg_binary-3.2.13-…-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`，未见 macosx / win_ |
| 5 | 试用前核对包内容 | **闭合** | 见下节 |

## 发布包抽查

`tar tzf` 前若干项含顶层 `asset-ledger/`，以及 `images/`、`deploy/`、`docker-compose.yml`。合计 105 项。

包内有：`VERSION`（0.1.0）、`app/`、`pyproject.toml`、`deploy/`（`lib.sh`、`pg-guard.sh`、`install.sh`、`upgrade.sh`、`up.sh`、`backup.sh`、`restore.sh`、`package.sh`）、`images/asset-ledger-images-amd64.tar.gz`、`功能说明.md`、`发布构建标准.md`、`部署说明.md`、`AGENT提示词.md`、`.env.example`。没有现场 `.env`，没有 `*.sql`，没有业务库数据。

包内 compose：顶层 `name: asset-ledger`，`pull_policy: never` 两处，`command: ["postgres"]`，卷名仍是 `delivery_ledger_pgdata`。

本机 Docker：`delivery-ledger-pg` 运行中，5432 映射到宿主机；`asset-ledger-pytest-pg` 运行中，`127.0.0.1:5433`。命名卷有 `asset_ledger_pytest_pgdata`，**没有** `delivery_ledger_pgdata`。本机另有未运行的 `delivery-ledger:1.2.1` 等镜像，当前 `docker ps -a` 没有用该镜像名跑着的容器。

## 本机交付台账冲突（为何不跑生产卷名安装）

- 容器 `delivery-ledger-pg` 在跑，镜像配置为 `postgres:16`（实际 image id 对应 `docker.m.daocloud.io/library/postgres:16`，Architecture=arm64），挂载匿名卷，compose 项目标签为空。
- 规格 `assert_volume_exclusive` 按镜像名 `delivery-ledger`、项目名 `delivery-ledger`、或已有非本产品卷 `delivery_ledger_pgdata` 拒绝。上述容器对算法不可见，因此 `install.sh` **不会**因它失败，而会新建 `delivery_ledger_pgdata`。
- 《部署说明》现场红线：本产品先装之后，禁止再在这台机器上装客户交付台账；对方不会拒绝该卷名。故本轮禁止在这台开发机上用生产卷名安装。
- 本轮也未删除该匿名卷、未 stop 交付台账。

## 试用安装步骤摘要

运行机：已装 Docker Compose V2 的 SUSE Linux Enterprise Server 15.6（x86_64）。不要装 Python，不要用宿主机已有 PostgreSQL。不要和客户交付台账装在同一台 Docker 宿主机上。

```bash
tar -xzf asset-ledger-0.1.0.tar.gz -C /tmp
sudo /tmp/asset-ledger/deploy/install.sh /opt/asset-ledger
```

安装目录不要用解压出来的 `/tmp/asset-ledger` 本身。浏览器打开 `http://<服务器>:8010/`，端口以 `.env` 的 `APP_PORT` 为准。就绪判据是 `http://127.0.0.1:8010/healthz` 正文 `ok`。

以后启动：`/opt/asset-ledger/deploy/up.sh`。升级：新包里的 `deploy/upgrade.sh /opt/asset-ledger`。停止不要加 `-v`。

## 同机红线

- 禁止与客户交付台账安装在同一 Docker 宿主机。
- 禁止直接 `docker compose up`。只允许 `deploy/install.sh`、`deploy/upgrade.sh`、`deploy/up.sh`。
- 禁止 `docker compose down -v`，禁止改卷名 `delivery_ledger_pgdata`，禁止改卷的 compose 项目标签，禁止删除 `asset_ledger.owner`。
- 本产品先装之后，不要再在这台机器上装客户交付台账；对方会挂上同一卷名。
- 本版没有登录。只在可信内网放行 `APP_PORT`。
- 本机开发验证：pytest 只用 5433 独立库，禁止把测试指到 5432 / 卷 `delivery_ledger_pgdata` 上的业务库。

## 已知限制（不构成不通过）

- 没有在 SUSE 实机上装过；架构校验是本机 `linux/amd64` 标签 + 包内 config blob。
- 开发方升级演练是同一版本 `0.1.0 → 0.1.0`，不是更高版本号。
- 本机 pytest 仍是 Python 3.9.6。容器内应用是 Python 3.12。
- 开发机临时卷冒烟不代替现场「项目名 `asset-ledger` + 卷名 `delivery_ledger_pgdata`」的首次安装。干净机按《部署说明》直接跑 `install.sh`。

## 明确不是缺陷

- 仓库柜子可以放服务器。
- 本产品先装、再装客户交付台账，对方不会自动失败（这是现场红线，不是脚本互斥）。
- 本机现有 `delivery-ledger-pg`（`postgres:16`、匿名卷）不被第 2.1 节拒绝，与规格字面一致。
- 资产删除不要求 `confirm=yes`。
- 无登录、无 Excel 导入、机柜只读。
