"""第 1 轮复验发现的缺口。这些用例在修掉之前应当失败。"""

from pathlib import Path

from app.domain import valid_ipv4

from tests.test_acceptance import assert_bad, make_space, post

ROOT = Path(__file__).resolve().parents[1]


def test_ipv4_unicode_digits_are_invalid_not_crash():
    # 规格第 6 节：四段都是 0–255 的十进制整数。Unicode 数字不是十进制 ASCII，应判非法，不得抛异常。
    assert valid_ipv4("192.168.0.1") is True
    assert valid_ipv4("1.1.1.²") is False
    assert valid_ipv4("١.١.١.١") is False


def test_unicode_ip_is_http_400(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    try:
        response = post(
            client,
            "/assets",
            code="IPU",
            serial="IPUS",
            name="服务器",
            kind="server",
            location_space_id=warehouse,
            biz_ip="1.1.1.²",
        )
    except ValueError as exc:
        raise AssertionError(f"valid_ipv4 抛 ValueError，HTTP 会变成 500: {exc}") from exc
    assert_bad(response, "IP 格式不正确")


def test_conftest_default_url_must_not_use_host_5432():
    # 本机 5432 常是客户交付台账。默认连过去会在错误实例上建 asset_ledger_test。
    text = (ROOT / "tests" / "conftest.py").read_text()
    assert "127.0.0.1:5432" not in text, "conftest 默认 DATABASE_URL 指向 5432，本机该端口是交付台账"
