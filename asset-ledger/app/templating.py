from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.domain import ASSET_KINDS, ASSET_LABELS, SPACE_KINDS, SPACE_LABELS, asset_label, space_label
from app.present import format_created

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.globals["space_label"] = space_label
templates.env.globals["asset_label"] = asset_label
templates.env.globals["space_kinds"] = SPACE_KINDS
templates.env.globals["asset_kinds"] = ASSET_KINDS
templates.env.globals["space_labels"] = SPACE_LABELS
templates.env.globals["asset_labels"] = ASSET_LABELS
templates.env.globals["format_created"] = format_created
