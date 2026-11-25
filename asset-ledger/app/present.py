from __future__ import annotations

from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from openpyxl import Workbook

from app.domain import (
    EXCEL_HEADERS,
    asset_label,
    children_of,
    depth_from,
    root_id,
    space_label,
    subtree,
)
from app.models import Asset, Space

SHANGHAI = ZoneInfo("Asia/Shanghai")


def format_created(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=SHANGHAI)
    return value.astimezone(SHANGHAI).strftime("%Y-%m-%d %H:%M")


def parent_map(spaces: list[Space]) -> dict[int, int | None]:
    return {space.id: space.parent_id for space in spaces}


def space_path(space: Space, by_id: dict[int, Space]) -> str:
    parts = []
    seen: set[int] = set()
    current: Space | None = space
    while current is not None and current.id not in seen:
        seen.add(current.id)
        parts.append(current.name)
        if current.parent_id is None:
            break
        current = by_id.get(current.parent_id)
    return " / ".join(reversed(parts))


def ordered_spaces(spaces: list[Space]) -> list[tuple[Space, int, str]]:
    by_id = {space.id: space for space in spaces}
    children: dict[int | None, list[Space]] = {}
    for space in spaces:
        children.setdefault(space.parent_id, []).append(space)
    for kids in children.values():
        kids.sort(key=lambda item: (item.name.lower(), item.name, item.id))
    rows: list[tuple[Space, int, str]] = []

    def walk(parent_id: int | None, depth: int) -> None:
        for space in children.get(parent_id, []):
            rows.append((space, depth, space_path(space, by_id)))
            walk(space.id, depth + 1)

    walk(None, 0)
    return rows


def location_text(asset: Asset, by_id: dict[int, Space], assets_by_id: dict[int, Asset]) -> str:
    if asset.mounted_asset_id is not None:
        host = assets_by_id.get(asset.mounted_asset_id)
        if host is None:
            return "服务器"
        return f"服务器 {host.code}"
    space = by_id.get(asset.location_space_id)
    if space is None:
        return ""
    return space_path(space, by_id)


def rack_rows(height: int, assets: list[Asset]) -> list[dict]:
    occupied: dict[int, Asset] = {}
    for asset in assets:
        if asset.start_u is None or asset.height_u is None:
            continue
        for unit in range(asset.start_u, asset.start_u + asset.height_u):
            occupied[unit] = asset
    return [{"u": unit, "asset": occupied.get(unit)} for unit in range(height, 0, -1)]


def scope_ids(space_id: int, spaces: list[Space]) -> set[int]:
    parents = parent_map(spaces)
    return set(subtree(space_id, children_of(parents)))


def assets_in_space_scope(space_id: int, spaces: list[Space], assets: list[Asset]) -> list[Asset]:
    scope = scope_ids(space_id, spaces)
    servers = {asset.id for asset in assets if asset.kind == "server" and asset.location_space_id in scope}
    chosen = []
    for asset in assets:
        if asset.location_space_id in scope or asset.mounted_asset_id in servers:
            chosen.append(asset)
    chosen.sort(key=lambda asset: (asset.code.lower(), asset.code, asset.id))
    return chosen


def _host_bits(asset: Asset, by_id: dict[int, Space], assets_by_id: dict[int, Asset]):
    if asset.mounted_asset_id is not None:
        host = assets_by_id.get(asset.mounted_asset_id)
        path = ""
        code = ""
        if host is not None:
            code = host.code
            space = by_id.get(host.location_space_id) if host.location_space_id else None
            if space is not None:
                path = space_path(space, by_id)
        return "服务器", path, None, None, code
    space = by_id.get(asset.location_space_id)
    if space is None:
        return "", "", None, None, ""
    start = asset.start_u if space.kind == "rack" else None
    height = asset.height_u if space.kind == "rack" else None
    return space_label(space.kind), space_path(space, by_id), start, height, ""


def excel_bytes(assets: list[Asset], spaces: list[Space], lookup: list[Asset] | None = None) -> bytes:
    by_id = {space.id: space for space in spaces}
    assets_by_id = {asset.id: asset for asset in (lookup or assets)}
    rows = sorted(assets, key=lambda asset: (asset.code.lower(), asset.code, asset.id))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "资产"
    sheet.append(list(EXCEL_HEADERS))
    for asset in rows:
        host_kind, path, start_u, height_u, mounted_code = _host_bits(asset, by_id, assets_by_id)
        sheet.append(
            [
                asset.code,
                asset.serial,
                asset.name,
                asset_label(asset.kind),
                asset.model,
                host_kind,
                path,
                start_u,
                height_u,
                mounted_code or None,
                asset.bmc_ip,
                asset.biz_ip,
                asset.mac,
                asset.location_note,
                asset.remark,
                format_created(asset.created_at),
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def recent_assets(assets: list[Asset], limit: int = 20) -> list[Asset]:
    return sorted(assets, key=lambda asset: (asset.created_at, asset.id), reverse=True)[:limit]


def space_depth(space: Space, spaces: list[Space]) -> int:
    return depth_from(space.id, parent_map(spaces))


def root_kind_of(space: Space, spaces: list[Space]) -> str:
    by_id = {item.id: item for item in spaces}
    parents = parent_map(spaces)
    return by_id[root_id(space.id, parents)].kind
