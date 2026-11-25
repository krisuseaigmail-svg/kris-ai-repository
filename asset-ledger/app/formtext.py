import starlette.formparsers as formparsers

_orig_unquote_plus = formparsers.unquote_plus


def repair_utf8(value: str) -> str:
    if not isinstance(value, str) or value == "":
        return value or ""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _unquote_plus(value, encoding="utf-8", errors="replace"):
    return repair_utf8(_orig_unquote_plus(value, encoding=encoding, errors=errors))


formparsers.unquote_plus = _unquote_plus
