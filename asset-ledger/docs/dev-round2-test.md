# 第 2 轮测试报告（测试模型，不采信开发自述）

工作目录：`asset-ledger/`。对照：`docs/dev-round1-test.md` 强制项、规格四件套。`docs/dev-round2.md` 只作对照。未改业务代码，未改 `delivery-ledger/`，未 git commit。未对 `delivery-ledger-pg` 执行 `down -v`，结束后本机仍无卷 `delivery_ledger_pgdata`。

## 结论

**有条件通过。**

第 1 轮强制项 1、2、4 已闭合；5（wheels）本仓库已放齐，但发布包仍未打。强制项 3 用**临时卷**验证了门禁与 `pg-guard`，**没有**跑仓库里的 `install.sh` / `upgrade.sh`（那会创建规格卷名 `delivery_ledger_pgdata`）。主功能与独立库 pytest 全绿。第 3 轮必须打离线包并走官方安装/升级脚本，才能交付试用。

## 本轮怎么跑

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

结果：**62 passed**（含 `tests/test_round1_gaps.py` 3 条、`tests/test_round2_closures.py` 4 条）。解释器仍是本机 3.9.6。容器内运行时另用临时栈验证过（镜像 `asset-ledger:0.1.0`，`POST /spaces` 303，重启后记录仍在）。

测试库：容器 `asset-ledger-pytest-pg`，端口 **5433**，库 `asset_ledger_test`。5432 上的 `delivery-ledger-pg` 未写入。

## 第 1 轮强制项闭合表

| # | 强制项 | 状态 | 独立证据 |
| --- | --- | --- | --- |
| 1 | `valid_ipv4` Unicode 不得 500 | **闭合** | `valid_ipv4("1.1.1.²")` / `"١.١.١.١"` 为 False；HTTP 400「IP 格式不正确」。`test_round1_gaps` 变绿。解析只认 ASCII `0-9` |
| 2 | 测试不得默认 5432 | **闭合** | 默认 `127.0.0.1:5433/asset_ledger_test`。端口 5432 或库名 `ledger` / `asset_ledger` 在导入阶段 `RuntimeError`。连不上独立库是 `pytest.fail`，不是 skip。`test_cluster` 对非本用例创建的 `ledger`、或其中已有 `deliveries` 行，拒绝 DROP |
| 3 | 真栈 26–30、36 | **部分** | 见下节。脚本路径 `install.sh` / `upgrade.sh` 未跑 |
| 4 | 钉住已抽查行为 | **闭合** | 叶节点六种子类型原文；挂防火墙；硬盘业务 IP / MAC；表单预填占用高度 2 再提交；四层路径 |
| 5 | wheels / 发布包 | **部分** | `vendor/wheels/` 27 个，全是 `py3-none-any` 或 `manylinux2014_x86_64` / `manylinux_2_17_x86_64`，**无 macosx**。`psycopg` 与 `psycopg-binary` 均为 `3.2.13`。`pyproject.toml` 已声明 package-data。**未**执行 `./deploy/package.sh`，无 `dist/asset-ledger-0.1.0.tar.gz` |

## 真实验证（临时卷，未动交付台账数据）

本机 `delivery-ledger-pg` 镜像是 `postgres:16`，匿名卷，**没有**名为 `delivery_ledger_pgdata` 的卷，compose 项目标签为空。按规格算法，这个容器本身不会触发「禁止与客户交付台账同机部署」。

| 场景 | 做法 | 结果 |
| --- | --- | --- |
| 验收 27 | `docker volume create delivery_ledger_pgdata`（无标签），`assert_volume_exclusive`，随后 `docker volume rm` 掉这个空卷 | 非 0，stderr「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」 |
| 验收 26 | `docker create --name asset-r2-probe-dl delivery-ledger:1.2.1`（未 start），再删探针容器 | 非 0，stderr「禁止与客户交付台账同机部署」。删掉探针后函数退出码 0 |
| 验收 29 / `pg-guard` | 临时卷 `asset_ledger_r2test_guard`（已删） | **无 `command` 参数**：容器立刻 `exit 0`，未拉起库（证实 compose 必须写 `command: ["postgres"]`）。**带 `postgres`**：`pg_isready` 成功，标记 13 字节（`asset-ledger` + 换行）。删标记保留 `PG_VERSION` 再启动：`exit 1`，原文「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」，`PG_VERSION` 与 `postgresql.conf` 校验和不变，标记未写回 |
| 健康检查 + 标记 + 重启 | 临时 compose 项目 `asset-ledger-r2test`，卷 `asset_ledger_r2test_stack`，端口 8019。`stop` / `rm` **无 `-v`**，再只删该测试卷 | `/healthz` 正文 `ok`。标记 hex `61 73 73 65 74 2d 6c 65 64 67 65 72 0a`。`POST /spaces` 303，页面有「机房验收」。重启后空间与标记仍在 |
| 镜像架构 | `docker image inspect` + `docker run --platform linux/amd64 … uname -m` | `asset-ledger:0.1.0` 与 `postgres:16` 均为 `Architecture=amd64`，`uname -m=x86_64`。这是本地标签，**不是**发布包压扁产物 |
| 验收 28 官方路径 | 未跑 `install.sh` | 未在规格卷名 `delivery_ledger_pgdata`、项目名 `asset-ledger` 上核对。临时栈项目名是 `asset-ledger-r2test` |
| 验收 36 官方路径 | 未跑 `upgrade.sh` | 仅临时栈重启保留数据；`replace_code` 单测仍证明不覆盖 `.env` |
| 验收 30 | 沿用替身 docker 单测 | `COMPOSE_PROJECT_NAME=other` 时 `up.sh` 非 0，原文正确 |

结束后：`delivery-ledger-pg`、`asset-ledger-pytest-pg` 仍在运行；`delivery_ledger_pgdata` 不存在。

## 第 9 节覆盖（相对第 1 轮）

第 1 轮「部分」里，实现侧抽查已过、本轮补测钉住的：2（叶节点六种）、4（四层路径）、13（防火墙挂载）、17（预填高度 2）、20（硬盘业务 IP/MAC）。

仍偏测试洞、不是实现错误：

- 第 2 条机房下仓库/办公区/工位/第二机房：原用例仍只断言 400。本轮 HTTP 抽查原文「这里不能放仓库/办公区/工位/机房」成立。
- 第 12 条办公区/工位/办公柜/机房 × 三类设备未全组合。本轮抽查：交换机→办公区、防火墙→工位、服务器→办公柜、服务器→机房，均为对应「不能放在这里」。
- 第 26/28/36 官方脚本与规格卷名：见上。

## 新缺陷

### 严重

无。

### 中

1. **发布与官方安装升级仍未闭合。** 无 `dist/asset-ledger-0.1.0.tar.gz`。`install.sh` / `upgrade.sh` 未在「项目名 `asset-ledger` + 卷名 `delivery_ledger_pgdata`」上跑过。试用机按《部署说明》解包安装这一条还不能签字。wheels 已齐，缺的是 `package.sh` 压扁与官方脚本一次成功路径。
2. **`command: ["postgres"]` 未写入规格第 2 节 compose 合同。** 独立复现：只改 entrypoint、不带 command 时 postgres 包装进程立刻 `exit 0`，健康检查失败。代码里已经补上，测试也断言了；若不写进《功能说明》，以后按规格删多余键会把栈打挂。

### 低

1. `tests/test_deploy.py` 未断言 `vendor/wheels/*.whl` 非空、且不含 macosx。wheels 目录一旦被清空，镜像构建会失败，但 pytest 仍绿。
2. 本机 pytest 仍跑在 Python 3.9.6。容器内 3.12 本轮用临时栈跑通首页级写入；不能代替发布包在 SUSE/amd64 上的一次安装。
3. 运行中的交付台账容器若只叫 `postgres:16`、不挂 `delivery_ledger_pgdata`，规格第 2.1 节算法看不见它。这是规格算法边界，不是本轮回归。同机红线仍靠现场，以及镜像名为 `delivery-ledger` 时的拒绝（本轮探针已证实）。

## 第 3 轮强制清单（目标：可交付试用）

1. **打发布包。** 在能访问镜像站的机器执行 `./deploy/package.sh`。产物 `dist/asset-ledger-0.1.0.tar.gz`。包内两镜像 `Architecture=amd64`，且 `docker run --rm --platform linux/amd64 <镜像> uname -m` 为 `x86_64`。禁止把未压扁的本地标签冒充发布包。
2. **官方安装与升级各一次**（干净机，或确认不会挂上交付台账业务数据的 Docker 环境；禁止 `down -v` 交付台账，禁止删别人的 `delivery_ledger_pgdata` 内容）：
   - `install.sh`：卷标签 `com.docker.compose.project=asset-ledger`；数据目录 `asset_ledger.owner` 去掉一个换行后是 `asset-ledger`；`/healthz` 为 `ok`。
   - `upgrade.sh`：升级前已有空间名、资产编号仍在；`.env` 密码不变；标记文件仍在且内容不变。
3. **把 `command: ["postgres"]` 写进《功能说明》第 2 节**（与 healthcheck、`pull_policy: never` 并列），并保持 `test_compose_contract` 断言。
4. **pytest 钉住 wheels：** 至少一枚 `.whl`、无 `macosx`、含 `openpyxl==3.1.5` 与 `psycopg_binary` 的 manylinux x86_64。
5. **试用前核对：** 包内有 `app/`、`pyproject.toml`、规格三件套与 `AGENT提示词.md`，无现场 `.env` 和业务数据。运行机只走 `install.sh` / `upgrade.sh` / `up.sh`。

## 明确不是缺陷

- 仓库柜子可以放服务器。
- 本产品先装、再装客户交付台账，对方不会自动失败。
- 本机现有 `delivery-ledger-pg`（镜像 `postgres:16`、匿名卷）不被第 2.1 节拒绝，与规格字面一致。
- 资产删除不要求 `confirm=yes`。
- 无登录、无 Excel 导入、机柜只读。
