from app.domain import (
    content_disposition,
    exceeds_depth,
    filename_part,
    intervals_overlap,
    matrix_message,
    normalize_mac,
    parse_int,
    placement_allowed,
    u_span,
    valid_ipv4,
)
from app.formtext import repair_utf8


def test_matrix_messages():
    assert matrix_message("rack") == "这里不能放机柜"
    assert matrix_message("cabinet") == "这里不能放柜子"
    assert matrix_message("desk") == "这里不能放工位"
    assert matrix_message("room") == "这里不能放机房"


def test_placement_matrix():
    assert placement_allowed("server", "rack", "room")
    assert placement_allowed("server", "warehouse", "warehouse")
    assert placement_allowed("server", "cabinet", "warehouse")
    assert not placement_allowed("server", "cabinet", "office")
    assert not placement_allowed("server", "office", "office")
    assert not placement_allowed("server", "desk", "office")
    assert not placement_allowed("server", "room", "room")
    assert placement_allowed("disk", "warehouse", "warehouse")
    assert placement_allowed("disk", "cabinet", "warehouse")
    assert placement_allowed("disk", "cabinet", "office")
    assert placement_allowed("disk", "office", "office")
    assert placement_allowed("disk", "desk", "office")
    assert not placement_allowed("disk", "rack", "room")
    assert not placement_allowed("disk", "room", "room")


def test_u_overlap_rules():
    assert not intervals_overlap(u_span(1, 2), u_span(3, 2))
    assert intervals_overlap(u_span(1, 2), u_span(2, 2))
    assert intervals_overlap(u_span(1, 2), u_span(2, 1))
    assert parse_int("0") == 0
    assert parse_int("1.5") is None
    assert parse_int("02") is None
    assert parse_int("-3") == -3


def test_ip_and_mac():
    assert not valid_ipv4("192.168.001.1")
    assert not valid_ipv4("bmc")
    assert valid_ipv4("192.168.0.1")
    assert valid_ipv4("0.0.0.0")
    assert normalize_mac("AABBCCDDEEFF") == "aa:bb:cc:dd:ee:ff"
    assert normalize_mac("aa-bb-cc-dd-ee-ff") == "aa:bb:cc:dd:ee:ff"
    assert normalize_mac("aa:bb:cc:dd:ee:ff") == "aa:bb:cc:dd:ee:ff"
    assert normalize_mac("abc") is None


def test_depth_move_would_exceed():
    parents = {1: None, 2: 1, 3: 2, 4: 3, 5: None}
    children = {None: [1, 5], 1: [2], 2: [3], 3: [4]}
    assert exceeds_depth(1, 5, parents, children)
    assert not exceeds_depth(3, 1, parents, children)
    assert not exceeds_depth(4, None, parents, children)


def test_filename_and_disposition():
    assert filename_part("机房:甲") == "机房_甲"
    assert filename_part("a<b>") == "a_b_"
    header = content_disposition("asset-ledger.xlsx", "资产台账.xlsx")
    assert header == 'attachment; filename="asset-ledger.xlsx"; filename*=UTF-8\'\'%E8%B5%84%E4%BA%A7%E5%8F%B0%E8%B4%A6.xlsx'


def test_utf8_form_repair():
    garbled = "机房".encode("utf-8").decode("latin-1")
    assert repair_utf8(garbled) == "机房"
    assert repair_utf8("机房") == "机房"
    assert repair_utf8("rack-1") == "rack-1"
