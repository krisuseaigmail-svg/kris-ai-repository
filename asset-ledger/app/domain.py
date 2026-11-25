from __future__ import annotations

import re
from urllib.parse import quote

SPACE_KINDS = ("room", "rack", "warehouse", "office", "cabinet", "desk")
SPACE_LABELS = {
    "room": "机房",
    "rack": "机柜",
    "warehouse": "仓库",
    "office": "办公区",
    "cabinet": "柜子",
    "desk": "工位",
}
ASSET_KINDS = ("server", "switch", "firewall", "disk")
ASSET_LABELS = {
    "server": "服务器",
    "switch": "交换机",
    "firewall": "防火墙",
    "disk": "硬盘",
}
ALLOWED_PARENTS = {
    "room": frozenset({None}),
    "rack": frozenset({"room"}),
    "warehouse": frozenset({None}),
    "office": frozenset({None, "office"}),
    "cabinet": frozenset({"warehouse", "office"}),
    "desk": frozenset({"office"}),
}
ROOT_KINDS = ("room", "warehouse", "office")
MAX_DEPTH = 4
PAGE_SIZE = 200
EXCEL_HEADERS = (
    "资产编号",
    "序列号",
    "名称",
    "类型",
    "型号",
    "宿主种类",
    "空间路径",
    "起始U",
    "占用U",
    "挂载于资产编号",
    "BMC IP",
    "业务 IP",
    "MAC",
    "位置备注",
    "备注",
    "登记时间",
)
_FILENAME_BAD = set('<>:"/\\|?*')
_MAC_COLON = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_MAC_DASH = re.compile(r"^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$")
_MAC_PLAIN = re.compile(r"^[0-9A-Fa-f]{12}$")
_INT_TEXT = re.compile(r"^-?(0|[1-9][0-9]*)$")
_ID_TEXT = re.compile(r"^[1-9][0-9]*$")


def space_label(kind: str) -> str:
    return SPACE_LABELS[kind]


def asset_label(kind: str) -> str:
    return ASSET_LABELS[kind]


def child_kinds(parent_kind: str | None) -> tuple[str, ...]:
    return tuple(kind for kind in SPACE_KINDS if parent_kind in ALLOWED_PARENTS[kind])


def matrix_message(kind: str) -> str:
    return f"这里不能放{SPACE_LABELS[kind]}"


def cannot_place_message(kind: str) -> str:
    return f"{ASSET_LABELS[kind]}不能放在这里"


def placement_allowed(asset_kind: str, space_kind: str, root_kind: str) -> bool:
    if space_kind == "rack":
        return asset_kind in {"server", "switch", "firewall"}
    if space_kind == "warehouse":
        return asset_kind in {"server", "switch", "firewall", "disk"}
    if space_kind == "cabinet":
        if root_kind == "warehouse":
            return asset_kind in {"server", "switch", "firewall", "disk"}
        if root_kind == "office":
            return asset_kind == "disk"
        return False
    if space_kind in {"office", "desk"}:
        return asset_kind == "disk"
    return False


def parse_int(text: str) -> int | None:
    if _INT_TEXT.fullmatch(text or "") is None:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def parse_id(text: str) -> tuple[str, int | None]:
    if text == "":
        return "empty", None
    if _ID_TEXT.fullmatch(text or "") is None:
        return "bad", None
    try:
        return "ok", int(text)
    except (TypeError, ValueError):
        return "bad", None


def ascii_id(text: str) -> int | None:
    state, value = parse_id(text or "")
    if state != "ok":
        return None
    return value


def children_of(parents: dict[int, int | None]) -> dict[int | None, list[int]]:
    children: dict[int | None, list[int]] = {}
    for space_id, parent_id in parents.items():
        children.setdefault(parent_id, []).append(space_id)
    return children


def depth_from(space_id: int, parents: dict[int, int | None]) -> int:
    seen: set[int] = set()
    current: int | None = space_id
    depth = 0
    while current is not None and current not in seen:
        seen.add(current)
        depth += 1
        parent = parents.get(current)
        if parent is None:
            break
        current = parent
    return depth


def subtree(root_id: int, children: dict[int | None, list[int]]) -> list[int]:
    ordered: list[int] = []
    stack = [root_id]
    while stack:
        current = stack.pop()
        ordered.append(current)
        stack.extend(reversed(children.get(current, [])))
    return ordered


def distance(node_id: int, root_id: int, parents: dict[int, int | None]) -> int:
    steps = 0
    seen: set[int] = set()
    current = node_id
    while current != root_id:
        steps += 1
        if current in seen:
            break
        seen.add(current)
        parent = parents.get(current)
        if parent is None:
            break
        current = parent
    return steps


def is_self_or_descendant(space_id: int, node_id: int, parents: dict[int, int | None]) -> bool:
    seen: set[int] = set()
    current: int | None = node_id
    while current is not None and current not in seen:
        if current == space_id:
            return True
        seen.add(current)
        parent = parents.get(current)
        if parent is None:
            return False
        current = parent
    return False


def exceeds_depth(node_id: int, new_parent_id: int | None, parents: dict[int, int | None], children: dict[int | None, list[int]]) -> bool:
    base = 1 if new_parent_id is None else depth_from(new_parent_id, parents) + 1
    for current in subtree(node_id, children):
        if base + distance(current, node_id, parents) > MAX_DEPTH:
            return True
    return False


def root_id(space_id: int, parents: dict[int, int | None]) -> int:
    seen: set[int] = set()
    current = space_id
    while current not in seen:
        seen.add(current)
        parent = parents.get(current)
        if parent is None:
            return current
        current = parent
    return current


def u_span(start: int, height: int) -> tuple[int, int]:
    return start, start + height - 1


def intervals_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return not (left[1] < right[0] or right[1] < left[0])


def valid_ipv4(value: str) -> bool:
    """只接受 ASCII 十进制。Unicode 数字和其它非 ASCII 一律非法，且不抛异常。"""
    try:
        parts = str(value).split(".")
    except Exception:
        return False
    if len(parts) != 4:
        return False
    for part in parts:
        if not part or any(char < "0" or char > "9" for char in part):
            return False
        if len(part) > 1 and part.startswith("0"):
            return False
        try:
            number = int(part)
        except (TypeError, ValueError):
            return False
        if number > 255:
            return False
    return True


def normalize_mac(value: str) -> str | None:
    if _MAC_PLAIN.fullmatch(value) or _MAC_COLON.fullmatch(value) or _MAC_DASH.fullmatch(value):
        hex_digits = re.sub(r"[:-]", "", value).lower()
        return ":".join(hex_digits[index : index + 2] for index in range(0, 12, 2))
    return None


def filename_part(name: str) -> str:
    chars = []
    for char in name:
        if char in _FILENAME_BAD or ord(char) <= 0x1F:
            chars.append("_")
        else:
            chars.append(char)
    return "".join(chars)


def content_disposition(ascii_name: str, utf8_name: str) -> str:
    encoded = quote(utf8_name, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"
