import threading
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx
import uvicorn
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from app.db import SessionLocal
from app.domain import EXCEL_HEADERS
from app.main import app
from app.models import Asset, Space

SHANGHAI = ZoneInfo("Asia/Shanghai")


def post(client, url, **data):
    payload = {key: "" if value is None else str(value) for key, value in data.items()}
    return client.post(url, data=payload, follow_redirects=False)


def new_id(response):
    assert response.status_code == 303, response.text
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def assert_bad(response, message, absent=None):
    assert response.status_code == 400, response.text
    assert response.status_code != 500
    assert message in response.text
    if absent:
        assert absent not in response.text


def space_count():
    db = SessionLocal()
    try:
        return db.scalar(select(func.count()).select_from(Space))
    finally:
        db.close()


def asset_count():
    db = SessionLocal()
    try:
        return db.scalar(select(func.count()).select_from(Asset))
    finally:
        db.close()


def load_space(space_id):
    db = SessionLocal()
    try:
        space = db.get(Space, space_id)
        if space is None:
            return None
        return {
            "name": space.name,
            "kind": space.kind,
            "parent_id": space.parent_id,
            "rack_height": space.rack_height,
            "note": space.note,
        }
    finally:
        db.close()


def load_asset(asset_id):
    db = SessionLocal()
    try:
        asset = db.get(Asset, asset_id)
        if asset is None:
            return None
        return {
            "code": asset.code,
            "serial": asset.serial,
            "name": asset.name,
            "kind": asset.kind,
            "location_space_id": asset.location_space_id,
            "mounted_asset_id": asset.mounted_asset_id,
            "start_u": asset.start_u,
            "height_u": asset.height_u,
            "bmc_ip": asset.bmc_ip,
            "biz_ip": asset.biz_ip,
            "mac": asset.mac,
        }
    finally:
        db.close()


def make_space(client, name, kind, parent="", height="", note=""):
    return new_id(
        post(client, "/spaces", name=name, kind=kind, parent_id=parent, rack_height=height, note=note)
    )


def asset_body(**overrides):
    data = {
        "code": "A1",
        "serial": "S1",
        "name": "设备",
        "kind": "server",
        "model": "",
        "bmc_ip": "",
        "biz_ip": "",
        "mac": "",
        "location_space_id": "",
        "mounted_asset_id": "",
        "start_u": "",
        "height_u": "",
        "location_note": "",
        "remark": "",
    }
    data.update(overrides)
    return data


def make_asset(client, **overrides):
    return new_id(post(client, "/assets", **asset_body(**overrides)))


def workbook_of(response):
    assert response.status_code == 200, response.text
    return load_workbook(BytesIO(response.content))


def test_acc_01_root_kinds(client):
    assert make_space(client, "机房A", "room")
    assert make_space(client, "仓库A", "warehouse")
    assert make_space(client, "办公A", "office")
    before = space_count()
    for kind, message in (("rack", "这里不能放机柜"), ("cabinet", "这里不能放柜子"), ("desk", "这里不能放工位")):
        height = "42" if kind == "rack" else ""
        response = post(client, "/spaces", name=kind, kind=kind, parent_id="", rack_height=height, note="")
        assert_bad(response, message)
    assert space_count() == before


def test_acc_02_room_and_leaf_children(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    before = space_count()
    assert_bad(post(client, "/spaces", name="柜子", kind="cabinet", parent_id=room, rack_height="", note=""), "这里不能放柜子")
    for kind in ("warehouse", "office", "desk", "room"):
        response = post(client, "/spaces", name=kind, kind=kind, parent_id=room, rack_height="", note="")
        assert response.status_code == 400
    cabinet = make_space(client, "仓库柜", "cabinet", parent=make_space(client, "仓库B", "warehouse"))
    desk_parent = make_space(client, "办公B", "office")
    desk = make_space(client, "工位1", "desk", parent=desk_parent)
    for parent in (rack, cabinet, desk):
        response = post(client, "/spaces", name="下级", kind="room", parent_id=parent, rack_height="", note="")
        assert response.status_code == 400
        assert "这里不能放机房" in response.text
    assert load_space(room)["name"] == "机房A"
    children = client.get(f"/spaces/{room}").text
    assert "柜子" not in children or "这里不能放柜子" in client.post(
        "/spaces", data={"name": "柜子", "kind": "cabinet", "parent_id": str(room), "rack_height": "", "note": ""}, follow_redirects=False
    ).text
    assert space_count() >= before


def test_acc_03_warehouse_and_office(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    assert make_space(client, "柜子", "cabinet", parent=warehouse)
    for kind in ("rack", "room", "warehouse", "office", "desk"):
        height = "42" if kind == "rack" else ""
        response = post(client, "/spaces", name=f"拒{kind}", kind=kind, parent_id=warehouse, rack_height=height, note="")
        assert response.status_code == 400
    office = make_space(client, "办公A", "office")
    assert make_space(client, "办公B", "office", parent=office)
    assert make_space(client, "柜子", "cabinet", parent=office)
    assert make_space(client, "工位", "desk", parent=office)


def test_acc_04_depth(client):
    first = make_space(client, "办公1", "office")
    second = make_space(client, "办公2", "office", parent=first)
    third = make_space(client, "办公3", "office", parent=second)
    desk = make_space(client, "工位D", "desk", parent=third)
    assert load_space(desk)["parent_id"] == third
    fourth = make_space(client, "办公4", "office", parent=third)
    before = space_count()
    response = post(client, "/spaces", name="太深", kind="desk", parent_id=fourth, rack_height="", note="")
    assert_bad(response, "空间层级过深")
    assert space_count() == before
    cabinet = make_space(client, "办公柜", "cabinet", parent=third)
    before = space_count()
    response = post(client, "/spaces", name="再下", kind="desk", parent_id=cabinet, rack_height="", note="")
    assert_bad(response, "这里不能放工位")
    assert "空间层级过深" not in response.text
    assert space_count() == before


def test_acc_05_names(client):
    room_a = make_space(client, "机房A", "room")
    room_b = make_space(client, "机房B", "room")
    make_space(client, "RackA", "rack", parent=room_a, height=42)
    other = make_space(client, "RackB", "rack", parent=room_a, height=42)
    response = post(client, f"/spaces/{other}", name="racka", kind="rack", parent_id=room_a, rack_height="42", note="")
    assert_bad(response, "同级已有这个名称")
    assert load_space(other)["name"] == "RackB"
    assert make_space(client, "同名柜", "rack", parent=room_a, height=42)
    assert make_space(client, "同名柜", "rack", parent=room_b, height=42)
    for bad in ("机/房", "机\\房"):
        response = post(client, "/spaces", name=bad, kind="room", parent_id="", rack_height="", note="")
        assert_bad(response, "名称不能含斜杠")
    response = post(client, "/spaces", name="机房a", kind="room", parent_id="", rack_height="", note="")
    assert_bad(response, "同级已有这个名称")


def test_acc_06_type_locked_after_create(client):
    office = make_space(client, "办公旧", "office")
    response = post(client, f"/spaces/{office}", name="办公新", kind="office", parent_id="", rack_height="", note="")
    assert response.status_code == 303
    assert load_space(office)["name"] == "办公新"
    assert load_space(office)["kind"] == "office"
    response = post(client, f"/spaces/{office}", name="改成仓库", kind="warehouse", parent_id="", rack_height="", note="")
    assert_bad(response, "类型创建后不能改")
    assert load_space(office)["kind"] == "office"
    assert load_space(office)["name"] == "办公新"


def test_acc_07_move_to_root(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    response = post(client, f"/spaces/{rack}", name="机柜1", kind="rack", parent_id="", rack_height="42", note="")
    assert_bad(response, "这里不能放机柜")
    assert load_space(rack)["parent_id"] == room
    parent = make_space(client, "办公根", "office")
    child = make_space(client, "办公子", "office", parent=parent)
    response = post(client, f"/spaces/{child}", name="办公子", kind="office", parent_id="", rack_height="", note="")
    assert response.status_code == 303
    assert load_space(child)["parent_id"] is None


def test_acc_08_cycle_and_matrix_order(client):
    office = make_space(client, "办公A", "office")
    response = post(client, f"/spaces/{office}", name="办公A", kind="office", parent_id=office, rack_height="", note="")
    assert_bad(response, "不能放到自己的下级")
    assert load_space(office)["parent_id"] is None
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    response = post(client, f"/spaces/{room}", name="机房A", kind="room", parent_id=rack, rack_height="", note="")
    assert_bad(response, "这里不能放机房")
    assert load_space(room)["parent_id"] is None


def test_acc_09_move_tree_too_deep(client):
    office_a = make_space(client, "办公A", "office")
    office_b = make_space(client, "办公B", "office", parent=office_a)
    office_c = make_space(client, "办公C", "office", parent=office_b)
    desk = make_space(client, "工位D", "desk", parent=office_c)
    office_e = make_space(client, "办公E", "office")
    response = post(client, f"/spaces/{office_a}", name="办公A", kind="office", parent_id=office_e, rack_height="", note="")
    assert_bad(response, "空间层级过深")
    assert load_space(office_a)["parent_id"] is None
    page = client.get(f"/spaces/{desk}")
    assert "办公A / 办公B / 办公C / 工位D" in page.text


def test_acc_10_move_assets_and_height_on_warehouse(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    cabinet = make_space(client, "备件柜", "cabinet", parent=warehouse)
    make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=cabinet)
    office = make_space(client, "办公A", "office")
    response = post(client, f"/spaces/{cabinet}", name="备件柜", kind="cabinet", parent_id=office, rack_height="", note="")
    assert_bad(response, "移动后已有资产不能留在这里")
    assert load_space(cabinet)["parent_id"] == warehouse
    response = post(client, f"/spaces/{warehouse}", name="仓库A", kind="warehouse", parent_id="", rack_height="42", note="")
    assert_bad(response, "这里不使用机柜高度")
    assert load_space(warehouse)["rack_height"] is None


def test_acc_11_delete_space(client):
    parent = make_space(client, "办公A", "office")
    child = make_space(client, "办公B", "office", parent=parent)
    response = post(client, f"/spaces/{parent}/delete", confirm="yes")
    assert_bad(response, "下面还有空间")
    assert load_space(parent) is not None
    response = post(client, f"/spaces/{child}/delete", confirm="no")
    assert_bad(response, "请确认删除")
    assert load_space(child) is not None
    warehouse = make_space(client, "仓库A", "warehouse")
    make_asset(client, code="DISK1", serial="DS1", name="硬盘", kind="disk", location_space_id=warehouse)
    response = post(client, f"/spaces/{warehouse}/delete", confirm="yes")
    assert_bad(response, "这里还有资产")
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2
    )
    make_asset(client, code="DISK2", serial="DS2", name="硬盘", kind="disk", mounted_asset_id=server)
    response = post(client, f"/spaces/{rack}/delete", confirm="yes")
    assert_bad(response, "这里还有资产")
    assert load_space(rack) is not None


def test_space_fk_is_chinese(client, monkeypatch):
    import app.services as services

    parent = make_space(client, "办公A", "office")
    make_space(client, "办公B", "office", parent=parent)
    monkeypatch.setattr(services, "has_child_spaces", lambda *_args, **_kwargs: False)
    response = post(client, f"/spaces/{parent}/delete", confirm="yes")
    assert_bad(response, "下面还有空间")
    assert load_space(parent) is not None


def test_acc_12_device_hosts(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    cabinet = make_space(client, "仓库柜", "cabinet", parent=warehouse)
    office = make_space(client, "办公A", "office")
    desk = make_space(client, "工位1", "desk", parent=office)
    office_cabinet = make_space(client, "办公柜", "cabinet", parent=office)
    before = asset_count()
    for index, kind in enumerate(("server", "switch", "firewall")):
        height = 2 if kind == "server" else 1
        start = 1 + index * 3
        assert make_asset(
            client,
            code=f"R{kind}",
            serial=f"RS{kind}",
            name=kind,
            kind=kind,
            location_space_id=rack,
            start_u=start,
            height_u=height,
        )
        assert make_asset(
            client,
            code=f"W{kind}",
            serial=f"WS{kind}",
            name=kind,
            kind=kind,
            location_space_id=warehouse,
        )
        saved = make_asset(
            client,
            code=f"C{kind}",
            serial=f"CS{kind}",
            name=kind,
            kind=kind,
            location_space_id=cabinet,
        )
        assert load_asset(saved)["start_u"] is None
        assert load_asset(saved)["height_u"] is None
    assert make_asset(client, code="CDISK", serial="CDS", name="硬盘", kind="disk", location_space_id=cabinet)
    messages = {"server": "服务器不能放在这里", "switch": "交换机不能放在这里", "firewall": "防火墙不能放在这里"}
    for kind, host in (
        ("server", office),
        ("switch", desk),
        ("firewall", office_cabinet),
        ("server", room),
    ):
        response = post(
            client,
            "/assets",
            **asset_body(code=f"BAD{kind}{host}", serial=f"BADS{kind}{host}", kind=kind, location_space_id=host),
        )
        assert_bad(response, messages[kind])
    assert asset_count() == before + 10


def test_acc_13_disk_hosts(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    cabinet = make_space(client, "柜子", "cabinet", parent=warehouse)
    office = make_space(client, "办公A", "office")
    office_cabinet = make_space(client, "办公柜", "cabinet", parent=office)
    desk = make_space(client, "工位", "desk", parent=office)
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2
    )
    switch = make_asset(
        client, code="SW", serial="SWS", name="交换机", kind="switch", location_space_id=rack, start_u=3, height_u=1
    )
    disk = make_asset(client, code="D1", serial="DS1", name="硬盘", kind="disk", mounted_asset_id=server, location_note="槽位1")
    assert make_asset(client, code="D2", serial="DS2", name="硬盘", kind="disk", location_space_id=warehouse, location_note="槽位1")
    assert make_asset(client, code="D3", serial="DS3", name="硬盘", kind="disk", location_space_id=cabinet)
    assert make_asset(client, code="D4", serial="DS4", name="硬盘", kind="disk", location_space_id=office)
    assert make_asset(client, code="D5", serial="DS5", name="硬盘", kind="disk", location_space_id=desk)
    assert make_asset(client, code="D6", serial="DS6", name="硬盘", kind="disk", location_space_id=office_cabinet)
    assert load_asset(disk)["mounted_asset_id"] == server
    for host in (rack, room):
        response = post(client, "/assets", **asset_body(code=f"X{host}", serial=f"XS{host}", kind="disk", location_space_id=host))
        assert_bad(response, "硬盘不能放在这里")
    other = make_asset(client, code="D7", serial="DS7", name="硬盘", kind="disk", location_space_id=warehouse)
    for target, label in ((switch, "交换机"), (other, "硬盘")):
        response = post(client, "/assets", **asset_body(code=f"M{target}", serial=f"MS{target}", kind="disk", mounted_asset_id=target))
        assert_bad(response, "挂载目标不是服务器")
        assert label


def test_acc_14_one_host(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    server = make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=warehouse)
    before = asset_count()
    response = post(
        client,
        "/assets",
        **asset_body(code="BOTH", serial="BOTHS", kind="disk", location_space_id=warehouse, mounted_asset_id=server),
    )
    assert_bad(response, "请只选择一种位置")
    response = post(client, "/assets", **asset_body(code="NONE", serial="NONES", kind="disk"))
    assert_bad(response, "请选择位置")
    assert asset_count() == before
    kept = make_asset(client, code="KEEP", serial="KEEPS", name="硬盘", kind="disk", location_space_id=warehouse)
    response = post(
        client,
        f"/assets/{kept}",
        **asset_body(code="KEEP", serial="KEEPS", name="硬盘", kind="disk", location_space_id=warehouse, mounted_asset_id=server),
    )
    assert_bad(response, "请只选择一种位置")
    assert load_asset(kept)["location_space_id"] == warehouse
    assert load_asset(kept)["mounted_asset_id"] is None


def test_acc_15_u_overlap(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    first = make_asset(client, code="A", serial="SA", name="甲", kind="server", location_space_id=rack, start_u=1, height_u=2)
    second = make_asset(client, code="B", serial="SB", name="乙", kind="server", location_space_id=rack, start_u=3, height_u=2)
    response = post(
        client,
        f"/assets/{second}",
        **asset_body(code="B", serial="SB", name="乙", kind="server", location_space_id=rack, start_u=2, height_u=2),
    )
    assert_bad(response, "U 位重叠")
    assert load_asset(second)["start_u"] == 3
    assert load_asset(second)["height_u"] == 2
    response = post(
        client,
        "/assets",
        **asset_body(code="C", serial="SC", name="丙", kind="server", location_space_id=rack, start_u=2, height_u=1),
    )
    assert_bad(response, "U 位重叠")
    assert load_asset(first)["start_u"] == 1


def test_acc_16_u_not_used_off_rack(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    response = post(
        client,
        "/assets",
        **asset_body(code="SVR", serial="SN", name="服务器", kind="server", location_space_id=warehouse, height_u=2),
    )
    assert_bad(response, "这里不使用 U 位", absent="U 位超出机柜")
    assert asset_count() == 0


def test_acc_17_u_format(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    for height in ("0", "1.5", "-1"):
        response = post(
            client,
            "/assets",
            **asset_body(code="H", serial="HS", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=height),
        )
        assert_bad(response, "占用高度无效")
    response = post(
        client,
        "/assets",
        **asset_body(code="H", serial="HS", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u="   "),
    )
    assert_bad(response, "请填写占用高度", absent="占用高度无效")
    response = post(
        client,
        "/assets",
        **asset_body(code="H", serial="HS", name="服务器", kind="server", location_space_id=rack, start_u=0, height_u=1),
    )
    assert_bad(response, "U 位超出机柜")
    response = post(
        client,
        "/assets",
        **asset_body(code="H", serial="HS", name="服务器", kind="server", location_space_id=rack, height_u=2),
    )
    assert_bad(response, "请填写起始 U")
    response = post(
        client,
        "/assets",
        **asset_body(code="H", serial="HS", name="服务器", kind="server", location_space_id=rack, start_u=1),
    )
    assert_bad(response, "请填写占用高度")
    form = client.get("/assets/new")
    assert 'name="height_u" value="2"' in form.text
    saved = make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=10, height_u=2)
    assert load_asset(saved)["height_u"] == 2


def test_acc_18_rack_height(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=11, height_u=2)
    response = post(client, f"/spaces/{rack}", name="机柜1", kind="rack", parent_id=room, rack_height=10, note="")
    assert_bad(response, "机柜高度小于已占用 U 位")
    assert load_space(rack)["rack_height"] == 42
    for height in ("0", "53", "1.5"):
        response = post(client, "/spaces", name="坏柜", kind="rack", parent_id=room, rack_height=height, note="")
        assert_bad(response, "机柜高度无效")


def test_acc_19_identity_fields(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    assert_bad(post(client, "/assets", **asset_body(code="   ", serial="SN", location_space_id=warehouse)), "请填写资产编号")
    assert_bad(post(client, "/assets", **asset_body(code="A1", serial="  ", location_space_id=warehouse)), "请填写序列号")
    assert_bad(post(client, "/assets", **asset_body(code="A 1", serial="SN", location_space_id=warehouse)), "资产编号不能有空格")
    assert_bad(post(client, "/assets", **asset_body(code="A1", serial="S N", location_space_id=warehouse)), "序列号不能有空格")
    assert_bad(post(client, "/assets", **asset_body(code="A1", serial="SN", name="   ", location_space_id=warehouse)), "请填写名称")
    first = make_asset(client, code="Ab", serial="Xy", name="服务器", kind="server", location_space_id=warehouse)
    assert_bad(
        post(client, "/assets", **asset_body(code="ab", serial="OTHER", name="另一台", location_space_id=warehouse)),
        "资产编号已存在",
    )
    assert_bad(
        post(client, "/assets", **asset_body(code="OTHER", serial="xY", name="另一台", location_space_id=warehouse)),
        "序列号已存在",
    )
    assert load_asset(first)["code"] == "Ab"
    assert make_asset(client, code="Xy", serial="NOT-XY", name="编号用了别人的序列号", kind="disk", location_space_id=warehouse)


def test_acc_20_network(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    for ip in ("192.168.001.1", "bmc"):
        response = post(
            client,
            "/assets",
            **asset_body(code="IP", serial="IPS", name="服务器", kind="server", location_space_id=warehouse, biz_ip=ip),
        )
        assert_bad(response, "IP 格式不正确")
    saved = make_asset(
        client,
        code="SVR",
        serial="SN",
        name="服务器",
        kind="server",
        location_space_id=rack,
        start_u=1,
        height_u=2,
        mac="AABBCCDDEEFF",
        biz_ip="10.0.0.8",
    )
    page = client.get(f"/assets/{saved}")
    assert "aa:bb:cc:dd:ee:ff" in page.text
    assert "本版只记录一块 MAC" in page.text
    assert "本版只记录一块 MAC" in client.get("/assets/new").text
    exported = workbook_of(client.get("/assets/export.xlsx"))
    assert exported.active["M2"].value == "aa:bb:cc:dd:ee:ff"
    before = asset_count()
    response = post(
        client,
        "/assets",
        **asset_body(code="DISK", serial="DS", name="硬盘", kind="disk", location_space_id=warehouse, bmc_ip="10.0.0.9"),
    )
    assert_bad(response, "硬盘不记录 BMC")
    assert asset_count() == before
    make_asset(
        client,
        code="SVR2",
        serial="SN2",
        name="另一台",
        kind="server",
        location_space_id=warehouse,
        biz_ip="10.0.0.8",
    )
    assert asset_count() == before + 1


def test_acc_21_type_change_host(client):
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2
    )
    response = post(
        client,
        f"/assets/{server}",
        **asset_body(code="SVR", serial="SN", name="服务器", kind="disk", location_space_id=rack, start_u=1, height_u=2),
    )
    assert_bad(response, "硬盘不能放在这里")
    assert load_asset(server)["kind"] == "server"
    disk = make_asset(client, code="DISK", serial="DS", name="硬盘", kind="disk", mounted_asset_id=server)
    response = post(
        client,
        f"/assets/{server}",
        **asset_body(code="SVR", serial="SN", name="服务器", kind="switch", location_space_id=rack, start_u=1, height_u=2),
    )
    assert_bad(response, "请先移出硬盘")
    assert load_asset(server)["kind"] == "server"
    response = post(
        client,
        f"/assets/{disk}",
        **asset_body(code="DISK", serial="DS", name="硬盘", kind="server", mounted_asset_id=server),
    )
    assert_bad(response, "服务器不能放在这里")
    assert load_asset(disk)["kind"] == "disk"


def test_acc_22_disk_follows_server(client):
    room = make_space(client, "机房A", "room")
    rack_a = make_space(client, "机柜A", "rack", parent=room, height=42)
    rack_b = make_space(client, "机柜B", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack_a, start_u=1, height_u=2
    )
    disk = make_asset(client, code="DISK", serial="DS", name="硬盘", kind="disk", mounted_asset_id=server)
    response = post(client, f"/assets/{server}/delete")
    assert_bad(response, "请先移出硬盘")
    assert load_asset(server) is not None
    assert load_asset(disk) is not None
    response = post(
        client,
        f"/assets/{disk}",
        **asset_body(code="DISK", serial="DS", name="硬盘", kind="disk", location_space_id=warehouse),
    )
    assert response.status_code == 303
    response = post(client, f"/assets/{server}/delete")
    assert response.status_code == 303
    assert load_asset(server) is None
    assert load_asset(disk)["location_space_id"] == warehouse
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack_a, start_u=1, height_u=2
    )
    disk = make_asset(client, code="DISK2", serial="DS2", name="硬盘", kind="disk", mounted_asset_id=server)
    response = post(client, f"/assets/{disk}/delete")
    assert response.status_code == 303
    assert load_asset(server) is not None
    disk = make_asset(client, code="DISK2", serial="DS2", name="硬盘", kind="disk", mounted_asset_id=server)
    response = post(
        client,
        f"/assets/{server}",
        **asset_body(code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack_b, start_u=5, height_u=2),
    )
    assert response.status_code == 303
    assert load_asset(disk)["mounted_asset_id"] == server
    book = workbook_of(client.get("/assets/export.xlsx"))
    rows = list(book.active.iter_rows(min_row=2, values_only=True))
    disk_row = next(row for row in rows if row[0] == "DISK2")
    assert disk_row[5] == "服务器"
    assert disk_row[6] == "机房A / 机柜B"
    assert disk_row[9] == "SVR"
    assert disk_row[7] is None
    assert disk_row[8] is None


def test_asset_fk_delete_is_chinese(client, monkeypatch):
    import app.services as services

    warehouse = make_space(client, "仓库A", "warehouse")
    server = make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=warehouse)
    make_asset(client, code="DISK", serial="DS", name="硬盘", kind="disk", mounted_asset_id=server)
    monkeypatch.setattr(services, "has_mounted_disks", lambda *_args, **_kwargs: False)
    response = post(client, f"/assets/{server}/delete")
    assert_bad(response, "请先移出硬盘")
    assert load_asset(server) is not None


def test_acc_23_excel(client):
    room = make_space(client, "机房:甲", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    server = make_asset(
        client, code="b-2", serial="SN2", name="乙", kind="server", location_space_id=rack, start_u=1, height_u=2
    )
    make_asset(client, code="A-1", serial="SN1", name="甲", kind="switch", location_space_id=rack, start_u=3, height_u=1)
    make_asset(client, code="DISK", serial="DS", name="硬盘", kind="disk", mounted_asset_id=server)
    make_asset(client, code="OTHER", serial="OS", name="仓库硬盘", kind="disk", location_space_id=warehouse)
    response = client.get("/assets/export.xlsx")
    header = response.headers["content-disposition"]
    assert 'filename="asset-ledger.xlsx"' in header
    assert "filename*=UTF-8''%E8%B5%84%E4%BA%A7%E5%8F%B0%E8%B4%A6.xlsx" in header
    book = workbook_of(response)
    assert book.sheetnames == ["资产"]
    headers = [cell.value for cell in book.active[1]]
    assert tuple(headers) == EXCEL_HEADERS
    codes = [row[0] for row in book.active.iter_rows(min_row=2, values_only=True)]
    assert codes == ["A-1", "b-2", "DISK", "OTHER"]
    filtered = client.get("/assets/export.xlsx?kind=disk")
    filtered_header = filtered.headers["content-disposition"]
    assert 'filename="asset-ledger-filter.xlsx"' in filtered_header
    assert unquote(filtered_header.split("UTF-8''", 1)[1]) == "资产台账-筛选.xlsx"
    disk_book = workbook_of(filtered)
    kinds = [row[3] for row in disk_book.active.iter_rows(min_row=2, values_only=True)]
    assert kinds == ["硬盘", "硬盘"]
    room_export = client.get(f"/spaces/{room}/export.xlsx")
    room_header = room_export.headers["content-disposition"]
    assert 'filename="asset-ledger-space.xlsx"' in room_header
    filename = unquote(room_header.split("UTF-8''", 1)[1])
    assert filename == "资产台账-机房_甲.xlsx"
    assert ":" not in filename
    room_codes = [row[0] for row in workbook_of(room_export).active.iter_rows(min_row=2, values_only=True)]
    assert room_codes == ["A-1", "b-2", "DISK"]
    assert "OTHER" not in room_codes


def test_acc_24_home_and_health(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    server = make_asset(
        client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2
    )
    make_asset(client, code="D1", serial="DS1", name="硬盘", kind="disk", mounted_asset_id=server)
    make_asset(client, code="D2", serial="DS2", name="硬盘", kind="disk", location_space_id=warehouse)
    for path in ("/", "/spaces", "/assets", "/assets/new"):
        page = client.get(path)
        assert page.status_code == 200
        assert "登录" not in page.text
        assert 'type="password"' not in page.text
    home = client.get("/")
    assert home.status_code == 200
    assert 'id="disk-count">2<' in home.text
    assert 'id="asset-count">3<' in home.text
    assert 'href="/assets/' in home.text
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.text.strip() == "ok"


def parallel_posts(path, payloads):
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=0.3)
            if response.status_code == 200 and response.text.strip() == "ok":
                break
        except Exception:
            time.sleep(0.05)
    else:
        server.should_exit = True
        raise RuntimeError("并发测试用的服务没有启动")
    barrier = threading.Barrier(len(payloads))
    results = [None] * len(payloads)
    errors = [None] * len(payloads)

    def shoot(index, payload):
        try:
            barrier.wait(10)
            form = {key: "" if value is None else str(value) for key, value in payload.items()}
            results[index] = httpx.post(
                f"http://127.0.0.1:{port}{path}",
                data=form,
                timeout=10,
                follow_redirects=False,
            )
        except Exception as exc:
            errors[index] = exc

    workers = [threading.Thread(target=shoot, args=(index, payload)) for index, payload in enumerate(payloads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(20)
    server.should_exit = True
    thread.join(5)
    assert errors == [None, None], errors
    return results


def test_acc_32_parallel_same_u(database_ready):
    from app.services import reset_data

    reset_data()
    with TestClient(app) as setup:
        room = make_space(setup, "机房A", "room")
        rack = make_space(setup, "机柜1", "rack", parent=room, height=42)
    results = parallel_posts(
        "/assets",
        [
            asset_body(code="P1", serial="SP1", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2),
            asset_body(code="P2", serial="SP2", name="服务器", kind="server", location_space_id=rack, start_u=1, height_u=2),
        ],
    )
    statuses = sorted(result.status_code for result in results)
    assert statuses == [303, 400]
    failed = next(result for result in results if result.status_code == 400)
    assert "U 位重叠" in failed.text
    db = SessionLocal()
    try:
        rows = list(db.scalars(select(Asset).where(Asset.location_space_id == rack)))
    finally:
        db.close()
    assert len(rows) == 1
    assert rows[0].start_u == 1


def test_acc_33_parallel_root_name(database_ready):
    from app.services import reset_data

    reset_data()
    results = parallel_posts(
        "/spaces",
        [
            {"name": "并发机房", "kind": "room", "parent_id": "", "rack_height": "", "note": ""},
            {"name": "并发机房", "kind": "room", "parent_id": "", "rack_height": "", "note": ""},
        ],
    )
    statuses = sorted(result.status_code for result in results)
    assert statuses == [303, 400]
    failed = next(result for result in results if result.status_code == 400)
    assert failed.status_code != 500
    assert "同级已有这个名称" in failed.text
    assert space_count() == 1


def test_acc_34_invalid_type(client):
    response = post(client, "/spaces", name="打印机", kind="printer", parent_id="", rack_height="", note="")
    assert_bad(response, "类型无效", absent="这里不能放")
    response = post(client, "/assets", **asset_body(kind="laptop", location_space_id=""))
    assert_bad(response, "类型无效")
    assert "请选择位置" not in response.text
    assert "请只选择一种位置" not in response.text
    assert asset_count() == 0


def test_acc_35_legal_moves(client):
    office_a = make_space(client, "办公A", "office")
    office_b = make_space(client, "办公B", "office", parent=office_a)
    office_c = make_space(client, "办公C", "office", parent=office_b)
    response = post(client, f"/spaces/{office_c}", name="办公C", kind="office", parent_id=office_a, rack_height="", note="")
    assert response.status_code == 303
    assert load_space(office_c)["parent_id"] == office_a
    deep = make_space(client, "一层", "office")
    second = make_space(client, "二层", "office", parent=deep)
    third = make_space(client, "三层", "office", parent=second)
    fourth = make_space(client, "四层", "office", parent=third)
    response = post(client, f"/spaces/{fourth}", name="四层", kind="office", parent_id="", rack_height="", note="")
    assert response.status_code == 303
    assert load_space(fourth)["parent_id"] is None
    office = make_space(client, "办公区", "office")
    cabinet = make_space(client, "硬盘柜", "cabinet", parent=office)
    disk = make_asset(client, code="DISK", serial="DS", name="硬盘", kind="disk", location_space_id=cabinet)
    warehouse = make_space(client, "仓库A", "warehouse")
    response = post(client, f"/spaces/{cabinet}", name="硬盘柜", kind="cabinet", parent_id=warehouse, rack_height="", note="")
    assert response.status_code == 303
    assert load_space(cabinet)["parent_id"] == warehouse
    assert load_asset(disk)["location_space_id"] == cabinet


def test_missing_objects_and_filters(client):
    missing_space = client.get("/spaces/999999")
    assert missing_space.status_code == 404
    assert "没有这个空间" in missing_space.text
    missing_asset = client.get("/assets/999999")
    assert missing_asset.status_code == 404
    assert "没有这个资产" in missing_asset.text
    room = make_space(client, "机房A", "room")
    rack = make_space(client, "机柜1", "rack", parent=room, height=42)
    warehouse = make_space(client, "仓库A", "warehouse")
    server = make_asset(
        client,
        code="SVR-1",
        serial="SN-1",
        name="计算节点",
        kind="server",
        model="Model-X",
        location_space_id=rack,
        start_u=1,
        height_u=2,
    )
    make_asset(client, code="DISK-1", serial="DS-1", name="系统盘", kind="disk", mounted_asset_id=server)
    make_asset(client, code="DISK-2", serial="DS-2", name="备件", kind="disk", location_space_id=warehouse)
    page = client.get("/assets", params={"kind": "disk", "space_id": str(room), "q": "系统"})
    assert "DISK-1" in page.text
    assert "DISK-2" not in page.text
    assert "计算节点" not in page.text
    found = client.get("/assets", params={"q": "model-x"})
    assert "SVR-1" in found.text
    empty = client.get("/spaces")
    assert empty.status_code == 200


def test_empty_library_hint_and_created_at_stable(client):
    page = client.get("/spaces")
    assert "请先建立机房、仓库或办公区，工位要建在办公区下。" in page.text
    warehouse = make_space(client, "仓库A", "warehouse")
    asset_id = make_asset(client, code="SVR", serial="SN", name="服务器", kind="server", location_space_id=warehouse)
    db = SessionLocal()
    try:
        created = db.get(Asset, asset_id).created_at
    finally:
        db.close()
    response = post(
        client,
        f"/assets/{asset_id}",
        **asset_body(code="SVR", serial="SN", name="改名", kind="server", location_space_id=warehouse),
    )
    assert response.status_code == 303
    db = SessionLocal()
    try:
        again = db.get(Asset, asset_id).created_at
    finally:
        db.close()
    assert again == created
    shown = client.get(f"/assets/{asset_id}").text
    assert created.astimezone(SHANGHAI).strftime("%Y-%m-%d %H:%M") in shown


def test_pagination_200(client):
    warehouse = make_space(client, "仓库A", "warehouse")
    now = datetime.now(SHANGHAI)
    db = SessionLocal()
    try:
        for index in range(201):
            db.add(
                Asset(
                    code=f"D{index:03d}",
                    serial=f"S{index:03d}",
                    name="硬盘",
                    kind="disk",
                    location_space_id=warehouse,
                    created_at=now,
                )
            )
        db.commit()
    finally:
        db.close()
    first = client.get("/assets")
    assert "本页 200 条" in first.text
    second = client.get("/assets", params={"page": 2})
    assert "本页 1 条" in second.text


def test_position_missing_and_note_limits(client):
    response = post(client, "/spaces", name="机房", kind="room", parent_id="999999", rack_height="", note="")
    assert_bad(response, "位置不存在")
    response = post(client, "/spaces", name="", kind="room", parent_id="", rack_height="", note="")
    assert_bad(response, "请填写名称")
    response = post(client, "/spaces", name="名" * 101, kind="room", parent_id="", rack_height="", note="")
    assert_bad(response, "名称过长")
    response = post(client, "/spaces", name="机房", kind="room", parent_id="", rack_height="", note="说" * 2001)
    assert_bad(response, "说明过长")
    response = post(client, "/spaces", name="坏柜", kind="rack", parent_id="", rack_height="", note="")
    assert_bad(response, "请填写机柜高度")
