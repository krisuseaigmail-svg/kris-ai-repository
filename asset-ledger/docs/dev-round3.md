# 第 3 轮交付说明

没有改 `delivery-ledger/`，没有 git commit，没有创建或删除卷 `delivery_ledger_pgdata`。本机 `delivery-ledger-pg` 仍在运行。

## 交付清单

发布包：`dist/asset-ledger-0.1.0.tar.gz`（约 213MB）。

包内有 `VERSION`（0.1.0）、`app/`、`pyproject.toml`、`deploy/`（含 `lib.sh`、`pg-guard.sh`、`install.sh`、`upgrade.sh`）、`images/asset-ledger-images-amd64.tar.gz`、`功能说明.md`、`发布构建标准.md`、`部署说明.md`、`AGENT提示词.md`。没有现场 `.env`，没有业务库数据。默认 `docker-compose.yml` 的卷名仍是 `delivery_ledger_pgdata`，并带有 `command: ["postgres"]`。

`scripts/smoke-isolated.sh` 和 `scripts/compose.smoke-volume.yml` 只用于开发机冒烟。覆盖文件把卷名改成临时名，不改生产 compose。

## 镜像架构

`./deploy/package.sh` 在压进包之前做过 create+commit，并检查：

- `asset-ledger:0.1.0`：`Architecture=amd64`，`uname -m=x86_64`
- `postgres:16`：`Architecture=amd64`，`uname -m=x86_64`

从包内 `images/asset-ledger-images-amd64.tar.gz` 再 `docker load` 后，两项仍然是 amd64 / x86_64。

## 在 SUSE 15.6 上安装

运行机是已装 Docker Compose V2 的 SUSE Linux Enterprise Server 15.6（x86_64），不要装 Python，也不要使用宿主机上已有的 PostgreSQL。不要和客户交付台账装在同一台 Docker 宿主机上。

```bash
tar -xzf asset-ledger-0.1.0.tar.gz -C /tmp
sudo /tmp/asset-ledger/deploy/install.sh /opt/asset-ledger
```

安装目录不要用解压出来的 `/tmp/asset-ledger` 本身。浏览器打开 `http://<服务器>:8010/`，端口以 `.env` 的 `APP_PORT` 为准。就绪判据是 `http://127.0.0.1:8010/healthz` 正文 `ok`。

以后启动用 `/opt/asset-ledger/deploy/up.sh`。升级用新包里的 `deploy/upgrade.sh /opt/asset-ledger`。停止不要加 `-v`。不要直接 `docker compose up`，不要 `down -v`，不要改卷名，不要删 `asset_ledger.owner`。

## 本机验证

pytest（独立库 5433，Python 3.9.6）：**64 passed**。

本机已有 `delivery-ledger-pg`（镜像 `postgres:16`、匿名卷）。规格算法看不见它，所以 `assert_volume_exclusive` 不会拒绝。若直接跑 `install.sh`，会创建生产卷名 `delivery_ledger_pgdata`。之后再装客户交付台账时，对方会挂上这个卷。因此没有在这台开发机上用生产卷名做完整安装。

改用解压后的发布包和 `scripts/smoke-isolated.sh`（覆盖卷名 `asset_ledger_smoke_pgdata`，项目名仍是 `asset-ledger`）：

- `install.sh` 完成，`/healthz` 正文 `ok`。
- 写入空间「冒烟机房」（303，`/spaces/1`）。
- 同版本 `upgrade.sh`（0.1.0 → 0.1.0）完成后，页面仍有「冒烟机房」，`.env` 密码不变。
- `asset_ledger.owner` 去掉一个换行后是 `asset-ledger`。
- 卷标签 `com.docker.compose.project=asset-ledger`。
- 生产卷 `delivery_ledger_pgdata` 始终不存在。冒烟卷在核对后已删除。

## 已知限制

- 没有在 SUSE 实机上装过；架构校验是在本机用 `--platform linux/amd64` 做的。
- 升级演练是同一版本的官方 `upgrade.sh`，不是更高版本号。
- 本机 pytest 仍是 Python 3.9.6。容器里的应用是 Python 3.12。
- 开发机冒烟不代替「项目名 `asset-ledger` + 卷名 `delivery_ledger_pgdata`」的现场首次安装。干净的 SUSE 机器应按《部署说明》直接跑 `install.sh`。
