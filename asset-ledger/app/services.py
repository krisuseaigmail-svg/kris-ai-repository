from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import engine
from app.domain import (
    ALLOWED_PARENTS,
    ASSET_KINDS,
    ASSET_LABELS,
    MAX_DEPTH,
    SPACE_KINDS,
    asset_label,
    cannot_place_message,
    children_of,
    depth_from,
    exceeds_depth,
    is_self_or_descendant,
    intervals_overlap,
    matrix_message,
    normalize_mac,
    parse_id,
    parse_int,
    placement_allowed,
    root_id,
    subtree,
    u_span,
    valid_ipv4,
)
from app.models import Asset, Space

SHANGHAI = ZoneInfo("Asia/Shanghai")
SPACE_FORM_KEYS = ("name", "kind", "parent_id", "note", "rack_height")
ASSET_FORM_KEYS = (
    "code",
    "serial",
    "name",
    "kind",
    "model",
    "bmc_ip",
    "biz_ip",
    "mac",
    "location_space_id",
    "mounted_asset_id",
    "start_u",
    "height_u",
    "location_note",
    "remark",
)


class FormError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def clean_form(form, keys: tuple[str, ...]) -> dict[str, str]:
    cleaned = {}
    for key in keys:
        value = form.get(key) if hasattr(form, "get") else form[key]
        cleaned[key] = "" if value is None else str(value).strip()
    return cleaned


def translate_integrity(exc: IntegrityError) -> str:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    name = (getattr(diag, "constraint_name", None) or "") if diag is not None else ""
    blob = f"{name} {orig}".lower()
    if "uq_assets_code" in blob or "assets_code" in blob:
        return "资产编号已存在"
    if "uq_assets_serial" in blob or "assets_serial" in blob:
        return "序列号已存在"
    if "uq_spaces" in blob or "spaces_root" in blob or "spaces_child" in blob:
        return "同级已有这个名称"
    if "fk_assets_mounted" in blob or "mounted_asset" in blob:
        return "请先移出硬盘"
    if "fk_assets_location" in blob or "location_space" in blob:
        return "这里还有资产"
    if "fk_spaces_parent" in blob or "parent" in blob:
        return "下面还有空间"
    if "unique" in blob:
        return "同级已有这个名称"
    return "这里还有资产"


def reset_data() -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE assets, spaces RESTART IDENTITY CASCADE"))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FormError(translate_integrity(exc)) from exc


def _guard(db: Session, fn):
    try:
        return fn()
    except FormError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise FormError(translate_integrity(exc)) from exc


def all_spaces(db: Session) -> list[Space]:
    return list(db.scalars(select(Space).order_by(Space.id)))


def all_assets(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset).order_by(Asset.id)))


def has_child_spaces(db: Session, space_id: int) -> bool:
    count = db.scalar(select(func.count()).select_from(Space).where(Space.parent_id == space_id))
    return bool(count)


def has_direct_assets(db: Session, space_id: int) -> bool:
    count = db.scalar(select(func.count()).select_from(Asset).where(Asset.location_space_id == space_id))
    return bool(count)


def has_mounted_disks(db: Session, asset_id: int) -> bool:
    count = db.scalar(select(func.count()).select_from(Asset).where(Asset.mounted_asset_id == asset_id))
    return bool(count)


def _maps(spaces: list[Space]):
    by_id = {space.id: space for space in spaces}
    parents = {space.id: space.parent_id for space in spaces}
    return by_id, parents, children_of(parents)


def _sibling_name_taken(db: Session, name: str, parent_id: int | None, exclude_id: int | None) -> bool:
    stmt = select(Space.id).where(func.lower(Space.name) == name.lower())
    if parent_id is None:
        stmt = stmt.where(Space.parent_id.is_(None))
    else:
        stmt = stmt.where(Space.parent_id == parent_id)
    if exclude_id is not None:
        stmt = stmt.where(Space.id != exclude_id)
    return db.scalar(stmt) is not None


def _code_taken(db: Session, code: str, exclude_id: int | None) -> bool:
    stmt = select(Asset.id).where(func.lower(Asset.code) == code.lower())
    if exclude_id is not None:
        stmt = stmt.where(Asset.id != exclude_id)
    return db.scalar(stmt) is not None


def _serial_taken(db: Session, serial: str, exclude_id: int | None) -> bool:
    stmt = select(Asset.id).where(func.lower(Asset.serial) == serial.lower())
    if exclude_id is not None:
        stmt = stmt.where(Asset.id != exclude_id)
    return db.scalar(stmt) is not None


def _lock_rack_assets(db: Session, rack_id: int) -> list[Asset]:
    db.scalars(select(Space.id).where(Space.id == rack_id).with_for_update()).all()
    return list(
        db.scalars(
            select(Asset).where(Asset.location_space_id == rack_id).order_by(Asset.id).with_for_update()
        ).all()
    )


def _max_occupied_u(rows: list[Asset], exclude_id: int | None = None) -> int:
    highest = 0
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        if row.start_u is None or row.height_u is None:
            continue
        highest = max(highest, row.start_u + row.height_u - 1)
    return highest


def _assets_remain_valid(db: Session, space_id: int, new_parent_id: int | None, by_id, parents, children) -> bool:
    moved = dict(parents)
    moved[space_id] = new_parent_id
    located = list(db.scalars(select(Asset).where(Asset.location_space_id.in_(subtree(space_id, children)))))
    for asset in located:
        host = by_id[asset.location_space_id]
        root = by_id[root_id(host.id, moved)]
        if not placement_allowed(asset.kind, host.kind, root.kind):
            return False
    return True


def save_space(db: Session, space: Space | None, form) -> Space:
    def run() -> Space:
        data = clean_form(form, SPACE_FORM_KEYS)
        name = data["name"]
        kind = data["kind"]
        note = data["note"]
        parent_raw = data["parent_id"]
        height_raw = data["rack_height"]

        if name == "":
            raise FormError("请填写名称")
        if len(name) > 100:
            raise FormError("名称过长")
        if "/" in name or "\\" in name:
            raise FormError("名称不能含斜杠")
        if len(note) > 2000:
            raise FormError("说明过长")
        if kind not in SPACE_KINDS:
            raise FormError("类型无效")
        if space is not None and kind != space.kind:
            raise FormError("类型创建后不能改")

        height_value: int | None = None
        if kind == "rack":
            if height_raw == "":
                raise FormError("请填写机柜高度")
            parsed = parse_int(height_raw)
            if parsed is None or parsed < 1 or parsed > 52:
                raise FormError("机柜高度无效")
            height_value = parsed
            if space is not None:
                locked = _lock_rack_assets(db, space.id)
                if height_value < _max_occupied_u(locked):
                    raise FormError("机柜高度小于已占用 U 位")
        elif height_raw != "":
            raise FormError("这里不使用机柜高度")

        parent_state, parent_id = parse_id(parent_raw)
        if parent_state == "bad":
            raise FormError("位置不存在")
        parent = None
        if parent_id is not None:
            parent = db.get(Space, parent_id)
            if parent is None:
                raise FormError("位置不存在")
        parent_kind = None if parent is None else parent.kind
        if parent_kind not in ALLOWED_PARENTS[kind]:
            raise FormError(matrix_message(kind))

        spaces = all_spaces(db)
        by_id, parents, children = _maps(spaces)
        if space is not None and parent_id is not None and is_self_or_descendant(space.id, parent_id, parents):
            raise FormError("不能放到自己的下级")

        if space is None:
            base = 1 if parent is None else depth_from(parent.id, parents) + 1
            if base > MAX_DEPTH:
                raise FormError("空间层级过深")
        else:
            if exceeds_depth(space.id, parent_id, parents, children):
                raise FormError("空间层级过深")
            if space.parent_id != parent_id and not _assets_remain_valid(db, space.id, parent_id, by_id, parents, children):
                raise FormError("移动后已有资产不能留在这里")

        exclude = None if space is None else space.id
        if _sibling_name_taken(db, name, parent_id, exclude):
            raise FormError("同级已有这个名称")

        target = space
        if target is None:
            target = Space(
                name=name,
                kind=kind,
                note=note or None,
                parent_id=parent_id,
                rack_height=height_value,
            )
            db.add(target)
        else:
            target.name = name
            target.note = note or None
            target.parent_id = parent_id
            target.rack_height = height_value
        _commit(db)
        return target

    return _guard(db, run)


def delete_space(db: Session, space: Space, confirm: str) -> None:
    def run() -> None:
        if confirm != "yes":
            raise FormError("请确认删除")
        if has_child_spaces(db, space.id):
            raise FormError("下面还有空间")
        if has_direct_assets(db, space.id):
            raise FormError("这里还有资产")
        db.delete(space)
        _commit(db)

    _guard(db, run)


def _optional(value: str) -> str | None:
    return value or None


def save_asset(db: Session, asset: Asset | None, form) -> Asset:
    def run() -> Asset:
        data = clean_form(form, ASSET_FORM_KEYS)
        code = data["code"]
        serial = data["serial"]
        name = data["name"]
        kind = data["kind"]
        model = data["model"]
        bmc = data["bmc_ip"]
        biz = data["biz_ip"]
        mac_raw = data["mac"]
        location_raw = data["location_space_id"]
        mounted_raw = data["mounted_asset_id"]
        start_raw = data["start_u"]
        height_raw = data["height_u"]
        location_note = data["location_note"]
        remark = data["remark"]

        if code == "":
            raise FormError("请填写资产编号")
        if len(code) > 64:
            raise FormError("资产编号过长")
        if any(char.isspace() for char in code):
            raise FormError("资产编号不能有空格")
        if serial == "":
            raise FormError("请填写序列号")
        if len(serial) > 128:
            raise FormError("序列号过长")
        if any(char.isspace() for char in serial):
            raise FormError("序列号不能有空格")
        if name == "":
            raise FormError("请填写名称")
        if len(name) > 200:
            raise FormError("名称过长")
        if len(model) > 200:
            raise FormError("型号过长")
        if len(location_note) > 200:
            raise FormError("位置备注过长")
        if len(remark) > 4000:
            raise FormError("备注过长")
        if kind not in ASSET_KINDS:
            raise FormError("类型无效")
        try:
            bmc_ok = (not bmc) or valid_ipv4(bmc)
            biz_ok = (not biz) or valid_ipv4(biz)
        except (TypeError, ValueError):
            bmc_ok = False
            biz_ok = False
        if bmc and not bmc_ok:
            raise FormError("IP 格式不正确")
        if biz and not biz_ok:
            raise FormError("IP 格式不正确")
        mac = None
        if mac_raw:
            mac = normalize_mac(mac_raw)
            if mac is None:
                raise FormError("MAC 格式不正确")
        if kind == "disk":
            if bmc:
                raise FormError("硬盘不记录 BMC")
            if biz:
                raise FormError("硬盘不记录业务 IP")
            if mac_raw:
                raise FormError("硬盘不记录 MAC")
            bmc = ""
            biz = ""
            mac = None

        location_state, location_id = parse_id(location_raw)
        mounted_state, mounted_id = parse_id(mounted_raw)
        location_present = location_state != "empty"
        mounted_present = mounted_state != "empty"
        if location_present and mounted_present:
            raise FormError("请只选择一种位置")
        if not location_present and not mounted_present:
            raise FormError("请选择位置")

        space = None
        host = None
        if location_present:
            if location_state == "bad":
                raise FormError("位置不存在")
            space = db.get(Space, location_id)
            if space is None:
                raise FormError("位置不存在")
        if mounted_present:
            if mounted_state == "bad":
                raise FormError("位置不存在")
            host = db.get(Asset, mounted_id)
            if host is None:
                raise FormError("位置不存在")

        if asset is not None and kind != "server" and has_mounted_disks(db, asset.id):
            raise FormError("请先移出硬盘")

        if mounted_present:
            if host.kind != "server":
                raise FormError("挂载目标不是服务器")
            if kind != "disk":
                raise FormError(cannot_place_message(kind))
        else:
            spaces = all_spaces(db)
            by_id, parents, _children = _maps(spaces)
            root = by_id[root_id(space.id, parents)]
            if not placement_allowed(kind, space.kind, root.kind):
                raise FormError(cannot_place_message(kind))

        on_rack = space is not None and space.kind == "rack"
        if not on_rack and (start_raw != "" or height_raw != ""):
            raise FormError("这里不使用 U 位")

        start_u = None
        height_u = None
        if on_rack:
            if start_raw == "":
                raise FormError("请填写起始 U")
            if height_raw == "":
                raise FormError("请填写占用高度")
            start_u = parse_int(start_raw)
            if start_u is None:
                raise FormError("起始 U 无效")
            height_u = parse_int(height_raw)
            if height_u is None or height_u < 1:
                raise FormError("占用高度无效")
            span = u_span(start_u, height_u)
            if start_u < 1 or span[1] > (space.rack_height or 0):
                raise FormError("U 位超出机柜")
            locked = _lock_rack_assets(db, space.id)
            for other in locked:
                if asset is not None and other.id == asset.id:
                    continue
                if other.start_u is None or other.height_u is None:
                    continue
                if intervals_overlap(span, u_span(other.start_u, other.height_u)):
                    raise FormError("U 位重叠")

        exclude = None if asset is None else asset.id
        if _code_taken(db, code, exclude):
            raise FormError("资产编号已存在")
        if _serial_taken(db, serial, exclude):
            raise FormError("序列号已存在")

        target = asset
        if target is None:
            target = Asset(created_at=datetime.now(SHANGHAI))
            db.add(target)
        target.code = code
        target.serial = serial
        target.name = name
        target.kind = kind
        target.model = _optional(model)
        target.bmc_ip = _optional(bmc) if kind != "disk" else None
        target.biz_ip = _optional(biz) if kind != "disk" else None
        target.mac = mac if kind != "disk" else None
        target.location_space_id = None if mounted_present else space.id
        target.mounted_asset_id = host.id if mounted_present else None
        target.start_u = start_u
        target.height_u = height_u
        target.location_note = _optional(location_note)
        target.remark = _optional(remark)
        _commit(db)
        return target

    return _guard(db, run)


def delete_asset(db: Session, asset: Asset) -> None:
    def run() -> None:
        if has_mounted_disks(db, asset.id):
            raise FormError("请先移出硬盘")
        db.delete(asset)
        _commit(db)

    _guard(db, run)


def filtered_assets(db: Session, kind: str, space_raw: str, keyword: str) -> list[Asset]:
    kind = kind.strip()
    space_raw = space_raw.strip()
    keyword = keyword.strip().lower()
    assets = all_assets(db)
    spaces = all_spaces(db)
    by_id = {space.id: space for space in spaces}
    parents = {space.id: space.parent_id for space in spaces}
    children = children_of(parents)
    scope = None
    if space_raw:
        state, space_id = parse_id(space_raw)
        if state != "ok" or space_id not in by_id:
            return []
        scope = set(subtree(space_id, children))
    servers_in_scope = set()
    if scope is not None:
        servers_in_scope = {
            asset.id
            for asset in assets
            if asset.kind == "server" and asset.location_space_id in scope
        }
    rows = []
    for asset in assets:
        if kind and asset.kind != kind:
            continue
        if scope is not None:
            in_space = asset.location_space_id in scope
            mounted_here = asset.mounted_asset_id in servers_in_scope
            if not in_space and not mounted_here:
                continue
        if keyword:
            haystack = [asset.code, asset.serial, asset.name, asset.model or ""]
            if not any(keyword in part.lower() for part in haystack):
                continue
        rows.append(asset)
    rows.sort(key=lambda asset: (asset.code.lower(), asset.code, asset.id))
    return rows


def legal_spaces_for(kind: str, spaces: list[Space]) -> list[Space]:
    by_id, parents, _children = _maps(spaces)
    found = []
    for space in spaces:
        root = by_id[root_id(space.id, parents)]
        if placement_allowed(kind, space.kind, root.kind):
            found.append(space)
    return found


def needs_place_hint(kind: str, spaces: list[Space], assets: list[Asset]) -> bool:
    if kind not in ASSET_KINDS:
        return False
    if legal_spaces_for(kind, spaces):
        return False
    if kind == "disk" and any(asset.kind == "server" for asset in assets):
        return False
    return True


def default_height(kind: str) -> str:
    if kind == "server":
        return "2"
    if kind in {"switch", "firewall"}:
        return "1"
    return ""


def asset_form_defaults(kind: str = "server") -> dict[str, str]:
    data = {key: "" for key in ASSET_FORM_KEYS}
    data["kind"] = kind if kind in ASSET_KINDS else "server"
    data["height_u"] = default_height(data["kind"])
    return data


def asset_to_form(asset: Asset) -> dict[str, str]:
    return {
        "code": asset.code,
        "serial": asset.serial,
        "name": asset.name,
        "kind": asset.kind,
        "model": asset.model or "",
        "bmc_ip": asset.bmc_ip or "",
        "biz_ip": asset.biz_ip or "",
        "mac": asset.mac or "",
        "location_space_id": "" if asset.location_space_id is None else str(asset.location_space_id),
        "mounted_asset_id": "" if asset.mounted_asset_id is None else str(asset.mounted_asset_id),
        "start_u": "" if asset.start_u is None else str(asset.start_u),
        "height_u": "" if asset.height_u is None else str(asset.height_u),
        "location_note": asset.location_note or "",
        "remark": asset.remark or "",
    }


def space_to_form(space: Space) -> dict[str, str]:
    return {
        "name": space.name,
        "kind": space.kind,
        "parent_id": "" if space.parent_id is None else str(space.parent_id),
        "note": space.note or "",
        "rack_height": "" if space.rack_height is None else str(space.rack_height),
    }
