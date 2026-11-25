"""补上第 1 轮测试报告里已经抽查、但原用例没钉住的行为。"""

import re

from app.domain import SPACE_LABELS

from tests.test_acceptance import assert_bad, asset_body, load_asset, make_asset, make_space, post


def test_leaf_spaces_reject_every_child_kind(client):
    room = make_space(client, "机房A", "room")
    warehouse = make_space(client, "仓库A", "warehouse")
    office = make_space(client, "办公A", "office")
    parents = {
        make_space(client, "机柜1", "rack", parent=room, height=42): "rack",
        make_space(client, "柜子", "cabinet", parent=warehouse): "cabinet",
        make_space(client, "工位1", "desk", parent=office): "desk",
    }
    for parent_id in parents:
        for kind, label in SPACE_LABELS.items():
            response = post(
                client,
                "/spaces",
                name=f"{parent_id}-{kind}",
                kind=kind,
                parent_id=parent_id,
                rack_height="42" if kind == "rack" else "",
                note="",
            )
            assert_bad(response, f"这里不能放{label}")


def test_disk_network_messages_and_firewall_mount(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    firewall = make_asset(
        client,
        code="FW",
        serial="FWS",
        name="防火墙",
        kind="firewall",
        location_space_id=rack,
        start_u=1,
        height_u=1,
    )
    response = post(
        client,
        "/assets",
        **asset_body(code="D1", serial="DS1", name="硬盘", kind="disk", mounted_asset_id=firewall),
    )
    assert_bad(response, "挂载目标不是服务器")
    response = post(
        client,
        "/assets",
        **asset_body(code="D2", serial="DS2", name="硬盘", kind="disk", location_space_id=warehouse, biz_ip="10.1.1.1"),
    )
    assert_bad(response, "硬盘不记录业务 IP")
    response = post(
        client,
        "/assets",
        **asset_body(
            code="D3",
            serial="DS3",
            name="硬盘",
            kind="disk",
            location_space_id=warehouse,
            mac="AABBCCDDEEFF",
        ),
    )
    assert_bad(response, "硬盘不记录 MAC")


def test_new_server_keeps_prefilled_height(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    page = client.get("/assets/new")
    match = re.search(r'name="height_u" value="([^"]*)"', page.text)
    assert match is not None
    height = match.group(1)
    assert height == "2"
    saved = make_asset(
        client,
        code="SVR",
        serial="SN",
        name="服务器",
        kind="server",
        location_space_id=rack,
        start_u=1,
        height_u=height,
    )
    assert load_asset(saved)["height_u"] == 2


def test_desk_depth_is_four(client):
    first = make_space(client, "办公1", "office")
    second = make_space(client, "办公2", "office", parent=first)
    third = make_space(client, "办公3", "office", parent=second)
    desk = make_space(client, "工位D", "desk", parent=third)
    page = client.get(f"/spaces/{desk}")
    assert page.status_code == 200
    assert "办公1 / 办公2 / 办公3 / 工位D" in page.text
