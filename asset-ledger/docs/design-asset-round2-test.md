# 机房/办公资产录入台账第 2 轮设计测试

独立复验，不采信 `design-asset-round2.md` 自述。未改设计正文，未写 `app/`。

评审对象：`docs/design-asset-round2.md`（下称设计）、`docs/design-asset-round2-spec-delta.md`（下称草案）。  
闭合对照：上轮 `docs/design-asset-round1-test.md` 第 6 节「必须改」十条。实现以草案为准，设计与草案打架时看草案是否真的写死。

## 结论

**有条件通过。可以进入第 3 轮，不可进入编码。**

上轮十条必须改里，业务与离线包九条已闭合；卷名没有按默认路径改成独立名字，走了「服从用户字面 + 同机互斥」的替代分支。替代方向在固定卷名前提下可以接受，但当前文本还不能当《AI提示词功能文档》：预检没有可复制的 Docker 命令、三条脚本没有单一实现点、跨库查 `deliveries` 的算法写错层、postgres 仍可能先打开别人的数据目录。第 3 轮把这些补成可粘贴步骤后才能开工。

---

## 1. 上轮强制修订闭合表

判定：已闭合 = 草案有可执行规则且有对应验收（若上轮要求验收）；部分 = 方向对但算法/验收/脚本范围缺一块，实现会分叉；未闭合 = 要求的行为不存在。

| # | 上轮必须改 | 闭合 | 证据 |
| --- | --- | --- | --- |
| 1 | 卷名改为 `asset_ledger_pgdata`；若用户坚持原名，则禁止同机 + 安装前发现卷已存在则失败 + postgres 不得入卷 | **部分** | 未改名，字面仍是 `delivery_ledger_pgdata`（草案第一部分 §2、第二部分 §1）。替代方案：部署说明禁止同机；`install.sh`/`upgrade.sh`/`up.sh` 在 up 前按卷标签拒绝非本产品卷（草案 §2.1、验收 26）。**postgres 不得入卷**只靠脚本，compose 本身仍会把该卷挂进 postgres；绕过脚本或后装交付台账时进程仍会打开对方 PGDATA。见第 3 节。 |
| 2 | 启动检查改到集群上可观测的事实；禁止只查当前库 `deliveries`；验收改为挂不上或失败且交付台账表不变 | **部分** | 草案 §2.2：连维护库 `postgres`，看 `pg_database` 是否有库名 `ledger`，或任一非模板库的 `public.deliveries`。并写明只查 `asset_ledger` 不算通过（验收 27）。验收 26：已装交付台账时 `deliveries` 行数与抽样列值不变。缺口：从维护库 **看不见** 其它库的表，跨库查法未写；应用检查发生在 postgres 已经入卷之后。 |
| 3 | 移动后整棵子孙新深度 ≤ 4，「空间层级过深」，父级不变；补验收 | **已闭合** | 草案 §4.2 给出公式：子孙新层数 = 该节点新层数 + 相对距离。验收 9：办公A 树移到办公E 下拒绝，A 仍为根，工位D 路径不变。设计 §3 同一反例。 |
| 4 | 防环验收补「父级设为自己」 | **已闭合** | 草案 §4.2、§4.4；验收 8。矩阵允许办公区挂办公区时，用防环句，不用「这里不能放办公区」。 |
| 5 | 消除第 1 轮设计与草案冲突（预填/超层/名称去空白/改类型+硬盘/非法父级提示） | **已闭合** | 设计 §4 逐条作废第 1 轮句子。草案：预填提交则写入、空才拒绝（§5.2、验收 17）；四层办公区合法（验收 4）；名称去首尾空白（§6）；改类型+硬盘（§5.1、验收 21）；非法父级「这里不能放」+页面用词（验收 7、8）。第 1 轮正文按任务未改，实现只认本轮草案，不再合并第 1 轮。 |
| 6 | 宿主二选一，两个外键都有值时拒绝并验收 | **已闭合** | 草案 §5.1「请只选择一种位置」；验收 14。都空「请选择位置」。 |
| 7 | 非机柜只要 U 有值，固定「这里不使用 U 位」，不先报超出机柜 | **已闭合** | 草案 §5.2、§5.4 第 7 步先于机柜区间；验收 16 写明页面正文没有「U 位超出机柜」。 |
| 8 | 离线发布可粘贴：3.12、wheels、压扁、禁 build/pull、postgres 不映射端口、install 拒绝覆盖、备份 db.sql+VERSION、pytest 不指现场卷 | **已闭合** | 草案第二部分全文。Python 3.12-slim、manylinux + 纯 Python 两次 download、create+commit、`pull_policy: never`、无 `ports`、已有 `VERSION` 则「已有安装，请使用 upgrade.sh」、备份不含 `files.tar.gz`、测试库名 `asset_ledger_test`。验收 25。包清单仍缺 `app/`，记入第 2 节新问题，不把第 8 条打回未闭合。 |
| 9 | 仓库柜子能否放整机：二选一写死 | **已闭合** | 允许。草案 §5.1、§1；验收 12：三种网络设备 + 一块硬盘都能进根为仓库的柜子，U 为空。 |
| 10 | 机房下柜子：二选一写死 | **已闭合** | 不允许。草案 §4.1「机房内的备件放在仓库节点或仓库下的柜子」；验收 2「这里不能放柜子」。不再出现「若测试认为」。 |

上轮「建议改」十条，草案已收：同类型再提交（验收 6）、`FOR UPDATE` 机柜行（验收 28）、完整性错误非 500（验收 11、22）、相邻 U 与端点重合（验收 15）、先移硬盘再删服务器（验收 22）、硬盘进机房（验收 13）、机柜改到根（验收 7）、四层办公区下再加工位（验收 4）、`filename*`（验收 23）、占用高度 0/非整数（验收 17）、首页硬盘数含挂载盘（验收 24）、矩阵→防环→深度（§4.4）、MAC 旁说明（验收 20）、删除前备份（第三部分）。建议项不挡第 3 轮，个别仍要补进提示词的实现细节见第 4 节。

---

## 2. 新发现的矛盾与漏洞

严重 = 不改会入错卷、丢数、或提示词无法唯一实现；中 = 实现会分叉或验收测不绿；低 = 应写进提示词但不挡主路径。

### 严重

1. **跨库查 `public.deliveries` 按现在的写法实现不了。**  
   草案 §2.2 第 2 步：用业务账号连维护库 `postgres`，「任一非模板库中 `public.deliveries` 是表」。`pg_class` / `information_schema.tables` 是**当前库**的目录。连在 `postgres` 库上只能可靠看到 `pg_database.datname`（库名 `ledger` 这一条成立），**看不到** `ledger.public.deliveries`，除非再逐个 `CONNECT` 到每个非模板库再查。草案没写循环连接。实现若只 `SELECT FROM pg_tables`，验收 27 后半句（「只在 `asset_ledger` 里找不到 deliveries 不能继续建表」）会对着一串空结果误通过。  
   现行交付台账库名就是 `ledger`（`delivery-ledger/deploy/lib.sh`）。库名检查够挡住现行对方；表检查是附加层，必须写成可执行步骤，不能停在「查询 pg_database 中全部非模板库」这半句。

2. **卷门禁在脚本里，postgres 入卷在 compose 里，两者不是同一层。**  
   支持路径先检查再 `up`，成立。直接 `docker compose up`、或客户交付台账后装（对方 `install.sh` 无反向检查，已核对 `delivery-ledger/deploy/install.sh`），postgres 仍会打开同一 `PGDATA`。设计 §2.4、§9 承认这三句残留。固定卷名下这不是「测试太严」，是门禁放错层：Docker 标签挡不住 compose 自己，也挡不住对方脚本。应用 §2.2 失败时进程退出、不建表，但 postmaster 已经写 `postmaster.pid` 和日志，对方栈起不来或误以为要重建卷。

3. **预检算法不可复制。**  
   「存在容器，其镜像去掉标签后的最后一段仓库名是 `delivery-ledger`」没有给出 `docker ps` 范围（是否含 Exited）、镜像字段（`RepoTags` / `Config.Image` / 仅 sha256 时怎么办）。「卷的 `com.docker.compose.project`」没有 `docker volume inspect` 模板。`COMPOSE_PROJECT_NAME` 或 `docker compose -p` 覆盖文件里的 `name: asset-ledger` 时，本产品会给卷打上别人的项目名，下次自己的升级会被 §2.1 第 2 步误杀，或反过来把对方卷认成自己的。三条脚本各写一遍检查，第 3 轮提示词若不收成**一个函数**，安装/升级/日常启动会三套行为。

### 中

4. **发布包清单没有 `app/`、`pyproject.toml`。**  
   第二部分 §2.1 列出 VERSION、images、wheels、deploy 脚本、Dockerfile、compose、文档。升级要「替换程序和镜像」。客户交付台账的包是带 `app/` 的。不写进去，实现会只靠镜像、磁盘上没有可替换程序，或漏打源码导致现场对不上 `migrate.py`。

5. **验收 26 只点 `install.sh`。**  
   草案 §2.1 要求 `upgrade.sh`、`up.sh` 做同一套检查。没有对应验收，实现会只挡首次安装。

6. **`FOR UPDATE` 未规定锁行顺序。**  
   §5.2：先锁机柜空间行，再锁该柜资产行。资产行若不 `ORDER BY id`，两个事务以不同顺序锁多行会死锁，验收 28 可能变成 500 而不是「U 位重叠」。

7. **「类型无效」不在保存顺序里。**  
   空间 §4.4、资产 §5.4 都没有这一步。非法类型可能先打出「这里不能放…」或宿主句。提示词必须把「类型无效」放在矩阵/宿主之前。

8. **空间同名的唯一约束冲突未规定译码。**  
   第一部分 §2 说完整性错误按 §4.3 和 §6 译中文。§4.3 只有删除 RESTRICT，§6 只有资产编号/序列号。并发两个根机房同名，可能 500。应译成「同级已有这个名称」，HTTP 400。

9. **`.env` 完整键没有可粘贴块。**  
   散落着 `DATABASE_URL`、`POSTGRES_USER`/`PASSWORD`/`DB`、`PRODUCT_CODE`、`APP_PORT`。缺 `APP_VERSION`、是否要 `TZ`。`PRODUCT_CODE` 若 install 漏写，应用每次都退出且不建表，compose 若 `restart: unless-stopped` 会空转。提示词必须给出 `write_env` 全文。

10. **`restore.sh` 只有「用 db.sql、不删其它备份」。**  
    未写：postgres 必须已起；断连接；DROP/CREATE 业务库；属主仍是 `asset_ledger`；失败不 `down -v`。实现会抄交付台账或直接 psql 进错误的库。

11. **U 位「空」未定义表单空字符串。**  
    浏览器会提交 `u_start=`。必须写：去掉首尾空白后长度为 0 视为空。只提交空格的占用高度，不应走「占用高度无效」还是「请填写」会分叉。

### 低

12. 移到自己的祖先：正文允许，无验收。  
13. 深度 4 的办公区改回根（层数变浅）无验收。  
14. 办公柜子（只有硬盘）移到仓库应成功，无验收。  
15. 导出文件名非法字符未列出集合。应写 `<>:"/\|?*` 与控制字符。  
16. 验收 28 未规定两个并发客户端的测法（双线程 POST，而不是连续两次）。  
17. 设计 §5 把 `[1,2]` 与 `[2,2]` 写成「端点相接」，草案写成闭区间相交。以草案为准，无行为分歧。  
18. 对方 compose **没有**顶层 `name:`（现行 `delivery-ledger/docker-compose.yml` 只有卷 `name:`）。项目名等于安装目录名，不一定是 `delivery-ledger`。草案用「标签不是 `asset-ledger`」挡卷，这条比「项目等于 delivery-ledger」更对；容器侧「项目等于 delivery-ledger」只是启发式，提示词不要把它当成充分条件。

---

## 3. 卷名互斥：固定字面前提下能否进入第 3 轮

### 3.1 裁决

**可以进入第 3 轮，不可以按当前文本编码。不要求第 3 轮改卷名。**

用户硬约束是卷名 `delivery_ledger_pgdata`。上轮默认解（改名）与用户字面冲突；本轮走禁止同机 + 标签门禁，符合上轮「若书面坚持原名」那一分支的方向。库名 `asset_ledger`、镜像 `asset-ledger`、项目名 `asset-ledger` **不能**代替卷隔离，设计 §2.3 这句成立。

不可接受的是把「脚本先看一下 Docker 标签」写成已经做到「postgres 不得入卷」。在固定卷名下，要做到可编码，必须把所有权检查下沉到 **本产品 postgres 启动之前**，并给出脚本层的精确命令。做不到双向技术互锁（改不了 `delivery-ledger/`），第 3 轮不得假装能做到。

### 3.2 当前方案挡得住 / 挡不住

| 顺序 | 脚本标签门禁 | 应用 §2.2 | 对方数据 |
| --- | --- | --- | --- |
| 对方已装、卷标签不是 `asset-ledger`，走 `install.sh` | 挡：§2.1 第 2 步 | 不会走到 | 验收 26 要求行不变。成立 |
| 对方已 `compose down`（未 `-v`），卷还在 | 挡：同上 | 不会走到 | 成立。比上轮「卷存在就失败」更精确，不会误伤本产品自己的升级 |
| 对方容器已停，镜像仍叫 `delivery-ledger` | 取决于 `docker ps` 是否含退出容器；卷步骤仍挡 | — | 必须写 `ps -a` |
| 只 load 了对方镜像、无容器无卷 | 不挡（草案已写） | 本产品会建自己的卷 | 随后对方再装会挂上。只能文档红线 |
| 本产品先装，对方后装 | 不挡（改不了对方脚本） | 对方 postgres 打开本产品 PGDATA；对方应用多半因账号 `ledger` 连不上 | 本产品数据被对方 postmaster 占用。**文档红线，不能当验收通过条件** |
| 绕过脚本 `docker compose up` | 不挡 | 建表可拒；postgres 已入卷 | 见严重-2 |
| 把卷标签改成 `asset-ledger` | 脚本放行 | 若库名仍是 `ledger` 或仍有 `deliveries` 则拒建表；postgres 已入卷 | 标签不可当作数据目录签名 |

### 3.3 不改卷名的补强要求（第 3 轮必须写进提示词）

**A. Postgres 启动包装（门禁下沉，必须项）**

compose 的 postgres 不得直接用镜像默认 entrypoint 开库。安装目录提供 `deploy/pg-guard.sh`，bind mount 进容器，先于 `docker-entrypoint.sh`：

1. 数据目录为空（或仅 `lost+found`）：执行官方入口做 initdb，成功后在 PGDATA 写入普通文件 `asset_ledger.owner`，内容一行 `asset-ledger`。
2. 数据目录已初始化且该文件内容恰好是 `asset-ledger`：执行官方入口启动。
3. 数据目录已初始化且没有该文件、或内容不是 `asset-ledger`：向 stderr 写「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」，退出码非 0，**不得启动 postgres**。不 `volume rm`，不改目录里已有文件。

这样：直接 `compose up`、标签被改掉但数据仍是对方的、卸载对方后留下的卷，本产品的 postgres 都不会打开那份 PGDATA。不增加第三张镜像，包内仍是 `asset-ledger:<版本>` + `postgres:16`。

首次由本产品 init 的卷，升级后标记仍在。`restore.sh` 恢复进本产品正在用的卷时不得删这个文件。

**B. 脚本预检单一实现（必须项）**

`deploy/lib.sh` 提供函数 `assert_volume_exclusive`，仅 `install.sh`、`upgrade.sh`、`up.sh` 在任何 `compose up` 之前调用。禁止三份拷贝。命令必须写成下面这些语义（提示词里用完整 CLI，不得用散文）：

1. `docker ps -aq`（**含退出容器**）。镜像名取 `docker inspect` 的 `Config.Image` 与 `RepoDigests`/`RepoTags`：去掉 digest 和 tag 后，路径最后一段等于 `delivery-ledger` 则失败，句为「禁止与客户交付台账同机部署」。
2. 任一容器（同上范围）的标签 `com.docker.compose.project=delivery-ledger`，或挂载了卷 `delivery_ledger_pgdata` 且项目标签不是 `asset-ledger`：同一句失败。
3. `docker volume inspect delivery_ledger_pgdata`：卷存在且 Labels 中 `com.docker.compose.project` 不是 `asset-ledger`（无 Labels 或无该键视为不是）：失败，句为「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」。
4. 脚本自身始终 `docker compose -p asset-ledger`。若环境里已有 `COMPOSE_PROJECT_NAME` 且值不是 `asset-ledger`，失败，句为「COMPOSE_PROJECT_NAME 必须是 asset-ledger」。compose 文件保留顶层 `name: asset-ledger`。

失败：退出码非 0；不 up；不 `volume rm`；不 `down -v`；不停止、不删除对方容器。

**C. 应用层集群检查写死算法（必须项）**

在 A 之后，§2.2 仍保留（防 `DATABASE_URL` 指错、防标记被手工补上）。算法：

1. `PRODUCT_CODE` 恰好 `asset-ledger`，否则「PRODUCT_CODE 必须是 asset-ledger」。
2. 用与业务库相同的用户、密码连库名 `postgres`（不是 `asset_ledger`）。连不上：「无法检查数据库卷归属」。
3. `SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate`。若集合中有 `ledger`：冲突句，不建表。
4. 对每个 `datname`（含 `postgres`、`asset_ledger`），再连过去查 `to_regclass('public.deliveries')`。任一库为表：同一冲突句。禁止只查当前库。
5. 本产品不创建名为 `ledger` 的库，表不命名 `deliveries`。其它陌生表不触发。

**D. 文档红线（必须项，且不得写成已有技术互锁）**

第三部分用单独短句，不得改成「系统会自动挡住后装的交付台账」：

- 禁止与客户交付台账安装在同一 Docker 宿主机。
- 本产品先装之后，禁止再在这台机器上安装客户交付台账；对方脚本不会拒绝同名卷。
- 禁止在运行机直接 `docker compose up`；只允许 `install.sh` / `upgrade.sh` / `up.sh`。
- 禁止 `docker compose down -v`、禁止改卷名、禁止改卷的 compose 项目标签。
- 本版无登录；只在可信内网放行 `APP_PORT`。删除前跑 `backup.sh`。

**E. 验收边界（必须项）**

第 3 轮验收必须包含、且**不要**包含：

必须测：

- 对方已装时，`install.sh`、`upgrade.sh`、`up.sh` 均非 0 退出，对方 `deliveries` 行数与抽样列值不变，本产品 postgres 容器不在运行。
- 手工 `docker volume create delivery_ledger_pgdata`（无项目标签）时安装失败，postgres 未启动。
- 干净安装后卷标签为 `asset-ledger`，且 PGDATA 中有 `asset_ledger.owner`。
- 把一份无标记的已初始化数据目录挂进本产品 compose 时，postgres 退出，日志含「不属于本产品」，不出现 `spaces`/`assets`。
- compose 无 `ports`；`COMPOSE_PROJECT_NAME=other ./up.sh` 失败。

不要测、也不要当通过条件：

- 「后装客户交付台账时对方自动失败且卷字节级不变」。做不到除非改 `delivery-ledger/` 或改卷名。设计 §9 第 1 点成立；第 3 轮保持这句，不要再把双向互锁写成待办。

**F. 标签策略（必须项）**

只认两件事的合取：Docker 卷标签 `com.docker.compose.project=asset-ledger` **以及** PGDATA 文件 `asset_ledger.owner`。只改标签不写文件，postgres 仍拒启动。只写文件但标签是别人的，脚本第 2 步拒 up。不要发明第三套标签名。不要靠 `PRODUCT_CODE` 挡卷。

---

## 4. 第 3 轮设计强制清单

目标：产出可编码的《AI提示词功能文档》（一份，实现只认这一份）。不要再写「对齐客户交付台账」这种转引。

### 必须改

1. 按第 3 节 A–F 把卷互斥写成可粘贴的脚本函数、postgres 包装、跨库 SQL、验收句和红线。不改卷名。
2. 发布包清单补 `app/`、`pyproject.toml`、`VERSION`（已有）、compose、Dockerfile；写明包内无 `.env`、无 `backups/`、无现场卷。
3. 给出 `.env.example` 与 `write_env` 全文（含随机密码、`PRODUCT_CODE=asset-ledger`、库名账号、`APP_PORT=8010`、权限 600）。
4. `restore.sh` / `backup.sh` 步骤：备份至少 `db.sql`+`VERSION`；恢复时 postgres 已健康、不断对方产品、DROP/CREATE 仅业务库 `asset_ledger`、保留 owner 标记、禁止 `-v`。
5. 空间/资产保存顺序补「类型无效」；空间同名唯一冲突译「同级已有这个名称」，HTTP 400。
6. U 重叠锁：`SELECT … FOR UPDATE` 机柜行后，资产行 `ORDER BY id` 再锁。
7. 表单空值：去空白后长度 0 视为空（U、高度、可选 IP/MAC）。
8. 验收补：`upgrade.sh`/`up.sh` 与 `install.sh` 同一套卷门禁；postgres 包装拒无标记数据目录。
9. 文档标题和结构按「功能说明 / 发布构建标准 / 部署说明 / 启动门禁附录」四块一次性贴出，并声明第 1 轮设计正文不作实现输入。
10. 写明 pytest：`DATABASE_URL` 库名 `asset_ledger_test`，独立 Postgres（不得使用现场卷名上的业务库）；并发 U 用两个并行 HTTP POST。

### 建议改

1. 补验收：子树移到祖先且层数合法则保存；深度 4 改回根；只有硬盘的办公柜子移到仓库。
2. `filename*` 非法字符集合写死；百分号编码按 RFC 5987，示例保持草案 §8 那一行。
3. compose `restart` 在应用因 §2.2 退出时不要掩盖日志；提示词要求 `docker compose logs app` 能读到那三句检查原文。
4. 镜像名解析遇到无 tag、仅 sha256 时：不单独当通过，仍看卷标签与 PGDATA 标记。
5. 明确主键为整数；路由 `/assets/new` 先于 `/{id}`。
6. 页面空态已有「先建机房、仓库或办公区」——保持，不要再拆办公空间类型。

第 3 轮不要再讨论：改卷名、改交付台账脚本、登录、Excel 导入、第二块 MAC、柜子再收紧、层数放宽到 5。那些要么已终裁，要么是后续迭代。

---

## 5. 本轮未做

未改设计正文；未写业务代码；未在 Docker 里实跑标签门禁（结论来自 Compose 命名卷语义、PostgreSQL 每库一套系统表、以及现行 `delivery-ledger` 的 compose / `install.sh` / `lib.sh`）。第 3 轮提示词出来后应再验：预检 CLI 是否可原样执行、无标记 PGDATA 是否能拦住 postgres、三条脚本是否调用同一函数。
