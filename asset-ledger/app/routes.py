from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain import (
    PAGE_SIZE,
    ROOT_KINDS,
    ascii_id,
    asset_label,
    child_kinds,
    content_disposition,
    filename_part,
    space_label,
)
from app.models import Asset, Space
from app.present import (
    assets_in_space_scope,
    excel_bytes,
    location_text,
    ordered_spaces,
    rack_rows,
    recent_assets,
    space_path,
)
from app.services import (
    FormError,
    all_assets,
    all_spaces,
    asset_form_defaults,
    asset_to_form,
    clean_form,
    delete_asset,
    delete_space,
    filtered_assets,
    legal_spaces_for,
    needs_place_hint,
    save_asset,
    save_space,
    space_to_form,
    ASSET_FORM_KEYS,
    SPACE_FORM_KEYS,
)
from app.templating import templates

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def page(request: Request, name: str, status_code: int = 200, **context):
    context.setdefault("error", "")
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def missing(request: Request, message: str):
    return page(request, "not_found.html", status_code=404, error=message)


def _maps(db: Session):
    spaces = all_spaces(db)
    assets = all_assets(db)
    space_by_id = {space.id: space for space in spaces}
    asset_by_id = {asset.id: asset for asset in assets}
    paths = {space.id: space_path(space, space_by_id) for space in spaces}
    return spaces, assets, space_by_id, asset_by_id, paths


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    _spaces, assets, space_by_id, asset_by_id, _paths = _maps(db)
    return page(
        request,
        "home.html",
        space_count=len(_spaces),
        asset_count=len(assets),
        disk_count=sum(1 for asset in assets if asset.kind == "disk"),
        recent=[
            {
                "id": asset.id,
                "code": asset.code,
                "name": asset.name,
                "kind_label": asset_label(asset.kind),
                "location": location_text(asset, space_by_id, asset_by_id),
            }
            for asset in recent_assets(assets)
        ],
    )


@router.get("/spaces")
def space_list(request: Request, db: Session = Depends(get_db)):
    spaces, _assets, _space_by_id, _asset_by_id, paths = _maps(db)
    rows = [
        {"id": space.id, "name": space.name, "kind": space.kind, "kind_label": space_label(space.kind), "depth": depth, "path": path}
        for space, depth, path in ordered_spaces(spaces)
    ]
    form = {key: "" for key in SPACE_FORM_KEYS}
    return page(
        request,
        "spaces.html",
        rows=rows,
        form=form,
        root_kinds=[(kind, space_label(kind)) for kind in ROOT_KINDS],
        paths=paths,
    )


@router.post("/spaces")
async def space_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    raw = clean_form(form, SPACE_FORM_KEYS)
    try:
        space = save_space(db, None, raw)
    except FormError as exc:
        spaces, _assets, _a, _b, paths = _maps(db)
        rows = [
            {"id": item.id, "name": item.name, "kind": item.kind, "kind_label": space_label(item.kind), "depth": depth, "path": path}
            for item, depth, path in ordered_spaces(spaces)
        ]
        return page(
            request,
            "spaces.html",
            status_code=400,
            error=exc.message,
            rows=rows,
            form=raw,
            root_kinds=[(kind, space_label(kind)) for kind in ROOT_KINDS],
            paths=paths,
        )
    return RedirectResponse(f"/spaces/{space.id}", status_code=303)


def _space_context(db: Session, space: Space, form: dict, error: str = ""):
    spaces, assets, space_by_id, asset_by_id, paths = _maps(db)
    children = [
        {"id": item.id, "name": item.name, "kind_label": space_label(item.kind)}
        for item in spaces
        if item.parent_id == space.id
    ]
    scoped = assets_in_space_scope(space.id, spaces, assets)
    child_options = [(kind, space_label(kind)) for kind in child_kinds(space.kind)]
    parent_options = [{"id": item.id, "path": paths[item.id]} for item in spaces]
    rack = []
    if space.kind == "rack" and space.rack_height:
        here = [asset for asset in assets if asset.location_space_id == space.id]
        rack = rack_rows(space.rack_height, here)
    return {
        "error": error,
        "space": space,
        "kind_label": space_label(space.kind),
        "path": paths.get(space.id, space.name),
        "form": form,
        "children": children,
        "child_kinds": child_options,
        "parent_options": parent_options,
        "assets": [
            {
                "id": asset.id,
                "code": asset.code,
                "name": asset.name,
                "kind_label": asset_label(asset.kind),
                "location": location_text(asset, space_by_id, asset_by_id),
            }
            for asset in scoped
        ],
        "rack_rows": rack,
        "child_height": "42" if child_options == [("rack", "机柜")] else "",
        "space_kinds": [(kind, space_label(kind)) for kind in ("room", "rack", "warehouse", "office", "cabinet", "desk")],
    }


@router.get("/spaces/{space_id}")
def space_detail(request: Request, space_id: int, db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if space is None:
        return missing(request, "没有这个空间")
    return page(request, "space.html", **_space_context(db, space, space_to_form(space)))


@router.post("/spaces/{space_id}")
async def space_update(request: Request, space_id: int, db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if space is None:
        return missing(request, "没有这个空间")
    form = clean_form(await request.form(), SPACE_FORM_KEYS)
    try:
        save_space(db, space, form)
    except FormError as exc:
        db.rollback()
        current = db.get(Space, space_id)
        return page(request, "space.html", status_code=400, **_space_context(db, current, form, exc.message))
    return RedirectResponse(f"/spaces/{space.id}", status_code=303)


@router.post("/spaces/{space_id}/delete")
async def space_remove(request: Request, space_id: int, db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if space is None:
        return missing(request, "没有这个空间")
    form = await request.form()
    confirm = "" if form.get("confirm") is None else str(form.get("confirm")).strip()
    try:
        delete_space(db, space, confirm)
    except FormError as exc:
        db.rollback()
        current = db.get(Space, space_id)
        return page(request, "space.html", status_code=400, **_space_context(db, current, space_to_form(current), exc.message))
    return RedirectResponse("/spaces", status_code=303)


@router.post("/spaces/{space_id}/children")
async def space_add_child(request: Request, space_id: int, db: Session = Depends(get_db)):
    parent = db.get(Space, space_id)
    if parent is None:
        return missing(request, "没有这个空间")
    form = clean_form(await request.form(), SPACE_FORM_KEYS)
    form["parent_id"] = str(parent.id)
    try:
        child = save_space(db, None, form)
    except FormError as exc:
        return page(request, "space.html", status_code=400, **_space_context(db, parent, space_to_form(parent), exc.message))
    return RedirectResponse(f"/spaces/{child.id}", status_code=303)


def _xlsx_response(payload: bytes, ascii_name: str, utf8_name: str) -> Response:
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition(ascii_name, utf8_name)},
    )


@router.get("/spaces/{space_id}/export.xlsx")
def space_export(request: Request, space_id: int, db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if space is None:
        return missing(request, "没有这个空间")
    spaces = all_spaces(db)
    assets = all_assets(db)
    rows = assets_in_space_scope(space_id, spaces, assets)
    name = f"资产台账-{filename_part(space.name)}.xlsx"
    return _xlsx_response(excel_bytes(rows, spaces, assets), "asset-ledger-space.xlsx", name)


def _asset_form_context(db: Session, form: dict, error: str = "", asset: Asset | None = None):
    spaces = all_spaces(db)
    assets = all_assets(db)
    space_by_id = {space.id: space for space in spaces}
    asset_by_id = {item.id: item for item in assets}
    paths = {space.id: space_path(space, space_by_id) for space in spaces}
    kind = form.get("kind") or "server"
    options = legal_spaces_for(kind, spaces)
    selected_space = form.get("location_space_id") or ""
    selected_id = ascii_id(selected_space)
    if selected_id is not None and selected_id in space_by_id and all(item.id != selected_id for item in options):
        options = [space_by_id[selected_id], *options]
    servers = [item for item in assets if item.kind == "server" and (asset is None or item.id != asset.id)]
    selected_mount = form.get("mounted_asset_id") or ""
    mount_id = ascii_id(selected_mount)
    if mount_id is not None and mount_id in asset_by_id and all(item.id != mount_id for item in servers):
        servers = [asset_by_id[mount_id], *servers]
    return {
        "error": error,
        "form": form,
        "asset": asset,
        "space_options": [{"id": space.id, "path": paths[space.id], "kind_label": space_label(space.kind)} for space in options],
        "server_options": [{"id": item.id, "code": item.code, "name": item.name} for item in servers],
        "place_hint": needs_place_hint(kind, spaces, assets),
        "kind_options": [(item, asset_label(item)) for item in ("server", "switch", "firewall", "disk")],
    }


@router.get("/assets")
def asset_list(
    request: Request,
    kind: str = "",
    space_id: str = "",
    q: str = "",
    page_index: int = Query(1, alias="page"),
    db: Session = Depends(get_db),
):
    spaces, assets, space_by_id, asset_by_id, paths = _maps(db)
    rows = filtered_assets(db, kind, space_id, q)
    current = page_index if page_index >= 1 else 1
    start = (current - 1) * PAGE_SIZE
    visible = rows[start : start + PAGE_SIZE]
    return page(
        request,
        "assets.html",
        rows=[
            {
                "id": asset.id,
                "code": asset.code,
                "serial": asset.serial,
                "name": asset.name,
                "kind_label": asset_label(asset.kind),
                "location": location_text(asset, space_by_id, asset_by_id),
                "bmc_ip": asset.bmc_ip or "",
                "biz_ip": asset.biz_ip or "",
                "mac": asset.mac or "",
            }
            for asset in visible
        ],
        total=len(rows),
        page_no=current,
        page_count=max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE),
        kind=kind,
        space_id=space_id,
        q=q,
        space_options=[{"id": space.id, "path": paths[space.id]} for space in spaces],
        kind_options=[("", "全部")] + [(item, asset_label(item)) for item in ("server", "switch", "firewall", "disk")],
        asset_total=len(assets),
    )


@router.get("/assets/new")
def asset_new(request: Request, kind: str = "server", db: Session = Depends(get_db)):
    form = asset_form_defaults(kind)
    return page(request, "asset_form.html", **_asset_form_context(db, form))


@router.get("/assets/export.xlsx")
def asset_export(
    kind: str = "",
    space_id: str = "",
    q: str = "",
    db: Session = Depends(get_db),
):
    spaces = all_spaces(db)
    assets = all_assets(db)
    rows = filtered_assets(db, kind, space_id, q)
    filtered = bool(kind.strip() or space_id.strip() or q.strip())
    if filtered:
        return _xlsx_response(excel_bytes(rows, spaces, assets), "asset-ledger-filter.xlsx", "资产台账-筛选.xlsx")
    return _xlsx_response(excel_bytes(rows, spaces, assets), "asset-ledger.xlsx", "资产台账.xlsx")


@router.post("/assets")
async def asset_create(request: Request, db: Session = Depends(get_db)):
    form = clean_form(await request.form(), ASSET_FORM_KEYS)
    try:
        asset = save_asset(db, None, form)
    except FormError as exc:
        return page(request, "asset_form.html", status_code=400, **_asset_form_context(db, form, exc.message))
    return RedirectResponse(f"/assets/{asset.id}", status_code=303)


@router.get("/assets/{asset_id}")
def asset_detail(request: Request, asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        return missing(request, "没有这个资产")
    _spaces, _assets, space_by_id, asset_by_id, _paths = _maps(db)
    return page(
        request,
        "asset.html",
        location=location_text(asset, space_by_id, asset_by_id),
        kind_label=asset_label(asset.kind),
        **_asset_form_context(db, asset_to_form(asset), asset=asset),
    )


@router.post("/assets/{asset_id}")
async def asset_update(request: Request, asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        return missing(request, "没有这个资产")
    form = clean_form(await request.form(), ASSET_FORM_KEYS)
    try:
        save_asset(db, asset, form)
    except FormError as exc:
        db.rollback()
        current = db.get(Asset, asset_id)
        _spaces, _assets, space_by_id, asset_by_id, _paths = _maps(db)
        return page(
            request,
            "asset.html",
            status_code=400,
            location=location_text(current, space_by_id, asset_by_id),
            kind_label=asset_label(current.kind),
            **_asset_form_context(db, form, exc.message, current),
        )
    return RedirectResponse(f"/assets/{asset.id}", status_code=303)


@router.post("/assets/{asset_id}/delete")
async def asset_remove(request: Request, asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if asset is None:
        return missing(request, "没有这个资产")
    try:
        delete_asset(db, asset)
    except FormError as exc:
        db.rollback()
        current = db.get(Asset, asset_id)
        _spaces, _assets, space_by_id, asset_by_id, _paths = _maps(db)
        return page(
            request,
            "asset.html",
            status_code=400,
            location=location_text(current, space_by_id, asset_by_id),
            kind_label=asset_label(current.kind),
            **_asset_form_context(db, asset_to_form(current), exc.message, current),
        )
    return RedirectResponse("/assets", status_code=303)
