# 第 2 轮开发说明

没有改 `delivery-ledger/`，没有 git commit，没有改规格里的卷名 `delivery_ledger_pgdata`。

## 修复

- `tests/conftest.py` 默认连接 `127.0.0.1:5433/asset_ledger_test`。端口是 5432，或库名是 `ledger` / `asset_ledger` 时，导入阶段直接失败，不 skip、不建库。
- `tests/test_cluster.py` 只在上述独立实例上建临时库。库 `ledger` 如果事先就存在，直接失败，不 `DROP`。即便是本用例刚建的 `ledger`，只要里面已有 `public.deliveries` 的行，也拒绝删除。
- `valid_ipv4`、整数和编号解析只接受 ASCII `0-9`。Unicode 数字返回非法，HTTP 400「IP 格式不正确」，不再 500。
- 补上报告里已抽查但没钉住的用例：叶节点下六种子类型的拒绝原文、硬盘业务 IP / MAC、挂防火墙、按新建表单预填的占用高度 2 提交。
- `pyproject.toml` 把模板和静态文件标进 package-data。
- `docker-compose.yml` 为 postgres 写上 `command: ["postgres"]`。只改 entrypoint 时，Compose 不会带上镜像自带的 CMD，包装脚本收到空参数，官方入口马上以 0 退出，健康检查失败。
- `vendor/wheels/` 已放入 linux/amd64 与 `py3-none-any` wheel。`psycopg` 与 `psycopg-binary` 都钉在 `3.2.13`，否则离线安装对不上版本。`deploy/package.sh` 的下载步骤按这个方式改过，避免在 Mac 上把 macosx wheel 下进目录。

## pytest

```bash
cd asset-ledger
DATABASE_URL='postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test' \
PRODUCT_CODE=asset-ledger \
PYTHONPATH=. python3 -m pytest -q
```

**62 passed**（含 `tests/test_round1_gaps.py`）。本机解释器仍是 Python 3.9.6。

## 真栈验证

本机 `delivery-ledger-pg` 仍在，镜像是 `postgres:16`，数据在匿名卷里，没有名为 `delivery_ledger_pgdata` 的卷。因此：

- 直接对真实 Docker 调用 `assert_volume_exclusive`，退出码是 0。规格算法看不到这个容器（镜像名不是 `delivery-ledger`，卷名也不是 `delivery_ledger_pgdata`）。
- 用本地镜像 `delivery-ledger:1.2.1` `docker create` 出一个未启动容器后，同一函数退出码 1，stderr 为「禁止与客户交付台账同机部署」。随后只删除了这个探针容器。
- 没有执行仓库里的 `docker-compose.yml` / `install.sh`。那会创建规格卷名 `delivery_ledger_pgdata`。这台机器已经在跑交付台账的 Postgres，不能把这个卷名占上。

用临时目录里的 compose（项目名 `asset-ledger`，卷名 `asset_ledger_round2_pgdata`，端口 8012）起过一套，验证完已 `down`（没有 `-v`），并只删除了这个测试卷：

- postgres 健康，`GET /healthz` 正文 `ok`。
- 卷标签 `com.docker.compose.project=asset-ledger`。
- 数据目录 `asset_ledger.owner` 去掉末尾换行后是 `asset-ledger`。
- `POST /spaces` 创建「机房验收」返回 303；重启两个容器后页面仍在，标记文件仍在。
- 本地镜像 `asset-ledger:0.1.0` 与 `postgres:16` 的 `Architecture` 都是 `amd64`。构建用的是 `pip install --no-index --find-links=/wheels`，没有访问 PyPI。

另外用 arm64 的 `postgres:16` 单独跑了 `pg-guard.sh`（卷 `asset_ledger_round2_guard`，已删除）：

- 空目录初始化后、`pg_isready` 成功时标记已是 `asset-ledger` 加一个换行。
- 删掉标记、保留 `PG_VERSION` 后再启动：退出码 1，stderr 含「卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载」，`PG_VERSION` 与 `postgresql.conf` 的校验和不变，标记没有被写回去。

## 没做

- 没有跑 `./deploy/package.sh`，没有 `dist/asset-ledger-0.1.0.tar.gz`，也没有在容器里核对 `uname -m`。本地 `docker build --platform linux/amd64` 只证明离线安装和 amd64 架构名，不是发布包要求的 create+commit 压扁。
- 没有跑真实 `install.sh` / `upgrade.sh`。升级后「空间名、资产编号、`.env` 密码、`asset_ledger.owner`」仍在，这次只在测试卷上做了重启，不是 `upgrade.sh`。
- 宿主机没有 Python 3.12。
