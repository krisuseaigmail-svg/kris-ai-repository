# 机房/办公资产录入台账第 3 轮测试（规格收口）

独立复验四份主文档是否可编码。不采信设计自述。第 1、2 轮 `docs/` 正文不是实现输入。

实现输入：`AGENT提示词.md`、`功能说明.md`、`发布构建标准.md`、`部署说明.md`。  
对照：`docs/design-asset-round2-test.md` 第 4 节必须改；抽查该文建议改前 5 条。

本轮对主文档做了 5 处可粘贴小补丁（见第 7 节），不改业务规则，不改卷名。

## 1. 可编码性结论

**通过。允许进入双模型开发测试 3 轮。**

四份主文档在补丁之后构成唯一实现输入：空间矩阵、资产宿主、Excel、离线 amd64、固定卷名加脚本预检 / `pg-guard.sh` / 跨库 `CONNECT` 均可按字面编码。用户硬需求全覆盖。上轮必须改十条均已闭合。不要再回头合并第 1、2 轮设计正文。

---

## 2. 四份主文档一致性

优先级以 `AGENT提示词.md` 第 2 节为准：功能说明 > 发布构建标准 > 部署说明 > 代码。抽查后，**没有会让实现选边的行为冲突**。下列是已核对或已补齐的对齐点，不是未决分歧。

| 主题 | 四处是否一致 | 说明 |
| --- | --- | --- |
| 卷名 `delivery_ledger_pgdata`、不改名 | 四份一致 | AGENT 绝对禁止改成 `asset_ledger_pgdata` |
| 项目名 `-p asset-ledger`、`PRODUCT_CODE` | 四份一致 | |
| 预检只在 `lib.sh` 的 `assert_volume_exclusive` | 四份一致 | |
| `pg-guard.sh` + `asset_ledger.owner` | 四份一致 | 本轮把 AGENT「无标记不得开库」收成「已有 `PG_VERSION` 却无合法标记」；空目录首次 init 仍按功能说明 2.3 第 1 步 |
| 跨库 `to_regclass` | 功能说明算法与验收 31、AGENT 禁止项一致 | 本轮改为 `IS NOT NULL`，避免把 SQL `NULL` 当成「有表」 |
| 库名/账号 `asset_ledger`、postgres 无 `ports` | 四份一致 | |
| `write_env` 键 | 功能说明 2.4 与部署说明一致 | `APP_VERSION` 不进 `.env`，由 `start_stack` 从 `VERSION` 导出。与发布标准升级第 5 步一致 |
| 包内 `app/`、`pyproject.toml`、无现场 `.env` | 发布标准与部署说明一致 | AGENT 代码地图含 `app/` |
| 后装交付台账不作为自动失败 | 功能说明验收末句、部署红线、AGENT §4/§10 一致 | |
| 容器 uvicorn `:8000`、宿主机默认 `8010` | 功能说明 / 部署 / 发布 CMD 一致 | AGENT 本地开发示例把 uvicorn 直接绑 8010，明确「不代替 `pg-guard.sh`」，不是现场 compose 的端口 |
| Compose V2 | 功能说明脚本是 `docker compose` | 本轮删掉部署说明里 `docker-compose` 回退 |
| healthcheck / `depends_on` | 本轮写入功能说明第 2 节与发布标准 2.2 | 补丁前未写，编码时 app 会抢在 postgres 之前启动 |

残留非冲突：

- 镜像名带 `host:port` 仓库时，bash `${base%:*}` 可能截错。现行对方镜像是 `delivery-ledger:<版本>`，卷标签与 PGDATA 标记仍是主门禁。不要另写一套解析。
- 功能说明第 2 节「完整性错误按 4.3 和 6 节翻译」：4.3 管删除 RESTRICT，6 节已含「同级已有这个名称」。两节合起来够用。

---

## 3. 用户原始硬需求覆盖矩阵

判定：有 = 现行主文档有可执行规则且可验收。全表为「有」才通过。

| 硬需求 | 覆盖 | 证据 |
| --- | --- | --- |
| Python | 有 | 功能说明 §2：3.12；发布标准 `FROM python:3.12-slim` |
| FastAPI | 有 | 功能说明 §2 钉 `fastapi==0.115.6`；发布 CMD 为 uvicorn 加载 `app.main:app` |
| Jinja2 | 有 | 功能说明 §2、§7；`jinja2==3.1.4`；简体中文服务端渲染 |
| PostgreSQL 16 | 有 | 功能说明 §2；发布标准 `postgres:16` |
| 容器内 uvicorn | 有 | 监听 8000；本轮发布标准写出 `CMD` |
| 在线创建机房、机柜、仓库、柜子、工位等 | 有 | 功能说明 §4 六类；空态先建机房/仓库/办公区；验收 1–3 |
| 逐层递进 | 有 | §4.1 矩阵；机房→机柜、仓库→柜子、办公区→办公区/柜子/工位；验收 2–4 |
| 记录服务器/交换机/防火墙/硬盘 | 有 | §5 四类 |
| 位置、资产编号、SN | 有 | §5、§6、§7 列表位置列 |
| BMC IP、业务 IP、Mac | 有 | 网络设备可填；硬盘必须空（§5.3、§6）；导出十六列含这三项；验收 20。不是每种资产都要有值 |
| 服务器在机柜或仓库 | 有 | §5.1 机柜 U / 仓库节点 / 仓库下柜子；验收 12 |
| 硬盘在服务器、仓库或办公空间 | 有 | 挂服务器 / 仓库 / 任意柜子 / 办公区 / 工位；验收 13 |
| 在线录入 | 有 | §7 表单与路由 |
| 导出 Excel | 有 | §8；无上传入口；验收 23 |
| SLES 15.6 x86_64 | 有 | 四份均写 |
| Docker + Compose | 有 | 仅 `app` + `postgres` |
| 宿主机不装 Python | 有 | 运行机不 pip；wheels 进镜像 |
| 无 DNS / 不访问 registry-1.docker.io | 有 | `pull_policy: never`；只 `docker load` |
| 仅 compose 内 postgres:16 | 有 | 无 `ports`；不用宿主机 PostgreSQL |
| 卷名固定 `delivery_ledger_pgdata` | 有 | 字面固定；独占 + 预检 + `pg-guard`；禁止改名 |
| Apple Silicon 必须 linux/amd64 | 有 | create+commit 压扁；Architecture=amd64 且 `uname -m=x86_64` |

---

## 4. 上轮必须改闭合表

对照 `design-asset-round2-test.md` 第 4 节「必须改」1–10。

| # | 要求 | 闭合 | 证据 |
| --- | --- | --- | --- |
| 1 | 卷互斥写成可粘贴脚本、postgres 包装、跨库 SQL、验收、红线；不改卷名 | **已闭合** | 功能说明 2.1 函数全文、2.2、2.3；验收 26–31、36 及「后装不测」；部署红线；AGENT 禁止改卷名 |
| 2 | 发布包含 `app/`、`pyproject.toml`；无 `.env` / `backups/` / 现场卷 | **已闭合** | 发布标准 2.1、2.4 |
| 3 | `.env.example` 与 `write_env` 全文 | **已闭合** | 功能说明 2.4；部署说明键列表 |
| 4 | backup/restore：健康、只动 `asset_ledger`、保留标记、禁止 `-v` | **已闭合** | 功能说明 2.5；部署「备份与恢复」 |
| 5 | 「类型无效」进顺序；空间同名冲突译中文 HTTP 400 | **已闭合** | §4.4 / §5.4；§6；验收 33、34 |
| 6 | U 锁：机柜行 `FOR UPDATE` 后资产行 `ORDER BY id` | **已闭合** | §5.2；验收 32 |
| 7 | 去空白后长度 0 视为空 | **已闭合** | §6；验收 17 |
| 8 | `upgrade.sh`/`up.sh` 与 install 同一预检；无标记 PGDATA 拒开库 | **已闭合** | 验收 26、29、30 |
| 9 | 四块主文档一次贴出；第 1 轮不作实现输入 | **已闭合** | 四份已在 `asset-ledger/` 根；功能说明开篇、AGENT §2.5 |
| 10 | pytest 独立库 `asset_ledger_test`；并发 U 为两个并行 POST | **已闭合** | 功能说明 §2、验收 32；AGENT §7 |

上轮第 3 节 A–F 补强：A `pg-guard`、B 单一函数与 CLI、C 逐库 `CONNECT`、D 红线、E 验收含/不含、F 标签与 owner 合取，均已落入功能说明与验收，不再列为缺口。

---

## 5. 抽查上轮建议改（5 条）

| 建议 | 规格是否可测、可实现 |
| --- | --- |
| 1. 子树移到祖先、深度 4 改回根、只有硬盘的办公柜子移到仓库 | **可。** 功能说明 §4.2 正文 + 验收 35。矩阵与层数公式已有，不新增类型 |
| 2. `filename*` 非法字符集合 + RFC 5987 | **可。** §8 列出 `<>:"/\|?*` 与 U+0000–U+001F；验收 23 用空间名含 `:` |
| 3. `restart` 不得吞掉 §2.2 日志；`compose logs app` 能读原句 | **可。** 功能说明 §2 段末；验收 31；部署「就绪」列出全部原句 |
| 4. 仅 sha256、无仓库名时不单独判为交付台账 | **可。** 功能说明 2.1 函数后的句子；仍走卷标签与 owner |
| 5. 主键整数；`/assets/new` 先于 `/{id}` | **可。** 功能说明 §2、§7；AGENT 代码地图。FastAPI 把 `{id}` 标成 int 即可 |

建议改第 6 条（空态文案、不拆办公空间）同样在 §7，未再抽成表。

---

## 6. 编码前补丁

补丁已写入主文档，**编码前无未完成清单**。不要再改卷名、不要改 `delivery-ledger/`、不要加登录或 Excel 导入。

---

## 7. 本轮对主文档的小改

不影响矩阵、宿主、Excel 列和卷名。

1. **`功能说明.md` §2**：补上 postgres `healthcheck` 与 app `depends_on: service_healthy`，避免编码时 app 抢跑。
2. **`功能说明.md` §2.1**：`volume inspect` 在 Labels 为 nil 时用 `{{if .Labels}}…{{end}}`，手工 `docker volume create` 仍走到「不属于本产品」那一句，而不是 Go 模板报错。
3. **`功能说明.md` §2.2 与验收 31**：跨库检查改为 `to_regclass(...) IS NOT NULL`。`NULL` 表示无表。
4. **`发布构建标准.md` §2.2**：写出 Dockerfile `EXPOSE 8000` 与 uvicorn `CMD`；compose healthcheck 与功能说明同一句。
5. **`AGENT提示词.md` §4**：禁止项与 2.3 节对齐——禁止的是「已有 `PG_VERSION` 却无合法标记还开库」，不是禁止空目录首次 initdb。
6. **`部署说明.md`**：安装前必须 `docker compose` V2，去掉 `docker-compose` 回退，以免现场用 V1 吃掉顶层 `name:`。

（5 条逻辑补丁；功能说明有两处同属第 3 条算法。）

---

## 8. 允许声明

**允许进入双模型开发测试 3 轮。**

实现只认：

- `asset-ledger/功能说明.md`
- `asset-ledger/发布构建标准.md`
- `asset-ledger/部署说明.md`
- `asset-ledger/AGENT提示词.md`

`docs/design-asset-round1*.md`、`docs/design-asset-round2*.md` 以及本报告都不是实现输入。冲突时以功能说明为准。
