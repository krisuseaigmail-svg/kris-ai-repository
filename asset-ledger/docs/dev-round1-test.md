# 第 1 轮测试报告（测试模型，不采信开发自述）

工作目录：`asset-ledger/`。权威规格：`功能说明.md`、`发布构建标准.md`、`部署说明.md`、`AGENT提示词.md`。未改业务代码，未改 `delivery-ledger/`，未 git commit。

## 结论

**有条件通过。**

业务主路径（空间矩阵、层数、宿主二选一、硬盘挂载、U 重叠、提示语原文、Excel 16 列、第 2.2 节跨库检查、`assert_volume_exclusive` 粘贴、`pg-guard.sh`）对照规格抽查成立。在独立 Postgres（容器 `asset-ledger-pytest-pg`，宿主机 **5433**，卷 `asset_ledger_pytest_pgdata`，库 `asset_ledger_test`，**未**使用 5432 上的交付台账）上复跑原有 pytest：**55 passed**。

不能判「通过」的原因：验收 26–30、36 没有真实 compose 栈；测试默认连接串指向 5432；`valid_ipv4` 对 Unicode 数字会抛异常变成 HTTP 500。这些不够推翻主功能，但第 2 轮必须修。

本机默认 `python3` 是 3.9.6（无 3.12）。pytest 在 3.9.6 下跑通，不能代替规格要求的运行时 Python 3.12 / 容器镜像。

## 本轮怎么跑

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

5433 实例当时只有 `postgres`、`asset_ledger_test`，没有库 `ledger`，也没有 `public.deliveries`（冲突用例自己创建后删除）。5432 上是 `delivery-ledger-pg`，未对它做任何写操作。

加上 `tests/test_round1_gaps.py` 后，下列用例**预期失败**，用来钉住缺陷。

## 第 9 节覆盖矩阵

| 条 | 覆盖 | 依据与缺口 |
| --- | --- | --- |
| 1 根类型 | 覆盖 | `test_acc_01`，提示原文与不落库 |
| 2 机房/叶节点 | 部分 | 机房下柜子原文有。仓库/办公区/工位/第二机房只断言 400。叶节点只测创建机房。抽查：机柜/柜子/工位下六种子类型均拒绝，提示「这里不能放」+页面用词 |
| 3 仓库/办公区 | 覆盖 | `test_acc_03` |
| 4 层数 | 部分 | 四层办公区、过深、柜子下「这里不能放工位」有。工位层数未直接断言 4 |
| 5 名称 | 覆盖 | 大小写、跨父级同名、斜杠、根机房 |
| 6 类型锁定 | 覆盖 | `test_acc_06` |
| 7 移到根 | 覆盖 | `test_acc_07` |
| 8 防环与矩阵顺序 | 覆盖 | 自己；机房父级=其下机柜 →「这里不能放机房」 |
| 9 整树过深 | 覆盖 | `test_acc_09`，路径不变 |
| 10 移动后资产 / 非机柜高度 | 覆盖 | `test_acc_10` |
| 11 删除 | 覆盖 | 子空间、直接资产、机柜+服务器+硬盘、确认值、FK 译中文 |
| 12 设备宿主 | 部分 | 机柜/仓库/仓库柜主路径有。办公区/工位/办公柜/机房 × 三类设备未全组合。抽查 `placement_allowed` 与 HTTP 一致 |
| 13 硬盘宿主 | 部分 | 服务器/仓库/柜子/办公区/工位、机柜与机房拒绝、交换机与另一硬盘挂载有。**缺防火墙挂载**。抽查：挂防火墙 →「挂载目标不是服务器」 |
| 14 宿主二选一 | 覆盖 | 创建与修改都有；抽查原文 |
| 15 U 重叠 | 覆盖 | `[1,2]` 与 `[3,4]` 可并存；改为 `[2,3]`、`[2,2]` 拒绝。抽查闭区间端点相交 |
| 16 非机柜带 U | 覆盖 | 只交占用高度 →「这里不使用 U 位」，正文无「U 位超出机柜」 |
| 17 U 格式与预填 | 部分 | 0 / 1.5 / 空格 / 起始 0 / 缺项有。预填只查 HTML `value="2"`，再手工 POST `height_u=2`。抽查：解析表单预填再提交，占用高度确为 2 |
| 18 机柜高度 | 覆盖 | 占用到 12U 改为 10；0 / 53。抽查 1 与 52 可保存 |
| 19 编号序列号 | 覆盖 | `test_acc_19` |
| 20 网络字段 | 部分 | 前导零 IP、MAC 规范化、硬盘 BMC、重复业务 IP、MAC 旁原文有。**缺「硬盘不记录业务 IP / MAC」**。抽查这两句成立 |
| 21 改类型 | 覆盖 | `test_acc_21` |
| 22 硬盘随服务器 | 覆盖 | 删除、改挂仓库、删硬盘、改机柜后导出路径 |
| 23 Excel | 覆盖 | 表名、16 列、文件名、`filename*`、机房范围、`:`→`_`。抽查宿主种类（机柜/仓库/柜子/工位/服务器）、U 为整数、空单元格、登记时间 `YYYY-MM-DD HH:MM` |
| 24 首页与健康检查 | 覆盖 | 无登录、硬盘数含挂载、`/healthz` 正文 `ok` |
| 25 compose 合同 | 覆盖 | 静态读 `docker-compose.yml`：卷名、项目名、镜像、无 postgres ports、`pg-guard`、`pull_policy: never` |
| 26 同机交付台账 | 部分 | 替身 `docker`：镜像名/项目名/外挂卷会拒绝且不 `up`。无真实对方容器，无 `deliveries` 行数不变 |
| 27 无标签卷 | 部分 | 替身 `volume inspect` 空标签。无 `docker volume create` 真实验 |
| 28 干净安装标记 | **缺失** | 无真实 `install.sh` 核对卷标签 `asset-ledger` 与 `asset_ledger.owner` |
| 29 无标记数据目录 | 部分 | `test_pg_guard_refuses_unmarked_data` 覆盖脚本；无 compose 真栈、无「官方入口未启动」容器级证明 |
| 30 `COMPOSE_PROJECT_NAME` | 覆盖 | `up.sh` + `other` → 非 0，原文「COMPOSE_PROJECT_NAME 必须是 asset-ledger」，不 `up` |
| 31 第 2.2 节 | 部分 | PRODUCT_CODE、库 `ledger`、**其它库** `deliveries`、连不上。抽查：维护库 `postgres` 上有 `deliveries` 也拒绝，且用 `to_regclass`，生产代码不用 `pg_tables` 代替第 4 步。无 `docker compose logs app` |
| 32 并行同一 U | 覆盖 | 真并行 HTTP POST，303+400，「U 位重叠」，该 U 一条 |
| 33 并行根同名 | 覆盖 | 303+400，「同级已有这个名称」 |
| 34 非法类型顺序 | 覆盖 | `printer` / `laptop`，不先出矩阵/宿主句 |
| 35 合法移动 | 覆盖 | 办公 C→A；四层改根；办公柜（仅硬盘）→仓库 |
| 36 升级保留 | 部分 | `replace_code` 不覆盖 `.env`/`backups`。无真实升级栈核对空间名、资产编号、`asset_ledger.owner` |

合计：覆盖 20，部分 15，缺失 1（第 28 条）。

## 抽查记录（独立于开发自述）

### 空间矩阵边界

`ALLOWED_PARENTS` 与第 4.1 节表一致。HTTP 扫 6 种子类型 × 根/六种父级：允许的 303，拒绝的 400 且原文「这里不能放」+子类型页面用词。机房详情「添加子空间」下拉只有机柜，没有柜子。机柜详情没有添加子空间表单。

### 硬盘挂载

可挂服务器。挂交换机、防火墙、另一块硬盘均为 400「挂载目标不是服务器」。挂载后 Excel：宿主种类「服务器」，空间路径等于服务器路径，起始 U / 占用 U 空，挂载于资产编号为服务器编号。

### U 重叠

`[1,2]` 与 `[3,4]` 可同时保存。改为起始 2 占用 2，或另存起始 2 占用 1，均为「U 位重叠」。锁顺序为机柜 `FOR UPDATE`，再按 `id` 排序锁该柜资产，与第 5.2 节一致。

### 宿主二选一

空间+挂载同时有值 →「请只选择一种位置」。都空 →「请选择位置」。编号不存在 →「位置不存在」。

### Excel 列

第 1 行 16 列与第 8 节完全一致。抽查行：仓库柜上的服务器宿主「柜子」、U 空；办公柜/工位上的硬盘宿主「柜子」「工位」；机柜设备 U 为 Python `int`。

### 提示语原文

抽查未改写、未加句号。含：「这里不能放机柜/柜子/工位/机房」「请只选择一种位置」「挂载目标不是服务器」「这里不使用 U 位」「硬盘不记录 BMC/业务 IP/MAC」「本版只记录一块 MAC」「请先建立机房、仓库或办公区，工位要建在办公区下。」错误走 `base.html` 的 `banner`。

### 第 2.2 节跨库检查

`boot()` 先 `assert_cluster_exclusive` 再 `create_all` / `migrate`。连维护库 `postgres` 列 `datname`，再对每个库单独连接执行 `SELECT to_regclass('public.deliveries') IS NOT NULL`。`app/cluster.py` 不用维护库 `pg_tables` 代替第 4 步。在 5433 上：维护库建 `deliveries` 后 `boot()` 退出码非 0，stderr 含「数据库卷与客户交付台账冲突」，且不建 `assets`。

### `assert_volume_exclusive`

`deploy/lib.sh` 中该函数与《功能说明》第 2.1 节粘贴块**逐字相同**。`write_env` 同样相同。`install.sh` / `upgrade.sh` / `up.sh` 只调用、不各自再写一份。失败路径不 `up`、脚本中无 `down -v`、无 `docker volume rm`。

### `pg-guard.sh`

无 `PG_VERSION` 走官方入口，出现 `PG_VERSION` 后写入 `asset_ledger.owner`（去掉至多一个换行后为 `asset-ledger`）并 `sync`。已有合法标记则 `exec` 官方入口。已有 `PG_VERSION` 但标记缺失/非法：stderr 含「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」，不调官方入口，不改已有文件。初始化失败且尚无 `PG_VERSION` 时沿用官方退出码，不打印「不属于本产品」。单测覆盖上述分支。

## 缺陷列表

### 严重

无。未发现会写错交付台账卷、静默丢数、或矩阵/U 位主路径放行非法数据的实现错误。

### 中

1. **测试默认 `DATABASE_URL` 指向 `127.0.0.1:5432`。** `tests/conftest.py` `setdefault` 如此。本机 5432 是 `delivery-ledger-pg`。未导出 5433 时，轻则连错后 skip/报错，重则在交付台账实例上 `CREATE DATABASE asset_ledger_test`。`test_cluster.py` 还会在该连接串指向的实例上 `CREATE`/`DROP DATABASE ledger`。违反第 2 节「不得把测试指到卷 `delivery_ledger_pgdata` 上的业务库」。`database_ready` 连不上时 `pytest.skip`，可能空绿。
2. **验收 26–30、28、36 未在真实 compose 上闭合。** 脚本静态与替身 docker 看起来对，但卷标签、`asset_ledger.owner`、无标记数据目录拒开库、升级后编号/密码/标记仍在，本轮都没有装过一次真栈。`vendor/wheels/` 只有 `.gitkeep`，`package.sh` 未执行。
3. **第 9 节测试有洞，回退测不红。** 防火墙作挂载目标、硬盘业务 IP/MAC 原文、叶节点六种子类型原文、按预填占用高度提交，实现抽查已过，但原测试未钉住。

### 低

1. **`valid_ipv4` 使用 `str.isdigit()` 再 `int()`。** 输入 `1.1.1.²` 或阿拉伯数字时抛 `ValueError`，HTTP **500**，不是 400「IP 格式不正确」。ASCII 前导零 / `bmc` 的验收 20 不受影响。见 `tests/test_round1_gaps.py`。
2. 本机无 Python 3.12，pytest 跑在 3.9.6。运行时规格仍是容器内 3.12。
3. `pyproject.toml` 未声明 `package-data`（模板与静态文件）。镜像靠 `WORKDIR /srv` + `COPY app` 碰巧能找到模板；若只靠 `pip install` 的 site-packages 启动会缺模板。

## 第 2 轮开发强制修订清单

1. **修 `valid_ipv4`：** 只接受 ASCII `0-9` 十进制段；Unicode 数字与其它非 ASCII 一律非法，返回「IP 格式不正确」、HTTP 400，禁止 500。`tests/test_round1_gaps.py` 应变绿。
2. **测试连接串：** `conftest.py` 禁止默认 5432。没有显式 `DATABASE_URL` 应失败而不是 skip，也不是连本机交付台账。文档示例可保留 5432，但本仓库默认必须指向独立实例（例如开发用的 5433 容器），库名仍是 `asset_ledger_test`。`test_cluster` 只允许在该独立实例上创建名为 `ledger` 的库。
3. **真栈补验收 26–30、36：** 至少一次干净 `install.sh`（卷标签 `com.docker.compose.project=asset-ledger`，数据目录 `asset_ledger.owner` 内容为 `asset-ledger`）；无标记已初始化目录交给 compose 时 postgres 退出且日志含「不属于本产品」；升级后空间名、资产编号、`.env` 密码、`asset_ledger.owner` 仍在。不要用 `down -v`。
4. **补测试钉住已经抽查通过的行为：** 挂防火墙 →「挂载目标不是服务器」；硬盘填业务 IP / MAC 的两句原文；机柜/柜子/工位下创建全部六种类型的拒绝原文；`GET /assets/new` 不改占用高度直接提交，服务器保存为 2。
5. **发布：** `vendor/wheels` 按《发布构建标准》放齐，或保持「无 wheel 则镜像构建失败」。本轮未打 `dist/asset-ledger-0.1.0.tar.gz`，发版前必须 `./deploy/package.sh` 并核对两镜像 `Architecture=amd64` 且 `uname -m=x86_64`。

## 明确不是缺陷

- 仓库下的柜子可以放服务器（规格如此）。
- 本产品先装、再装客户交付台账，对方不会自动失败（规格红线，现场遵守）。
- 资产删除不要求 `confirm=yes`（仅空间删除要）。
- 无登录、无 Excel 导入、机柜只读。
- `POST /spaces/{id}/children` 为页面添加子空间用，仍走同一套 `save_space`。
