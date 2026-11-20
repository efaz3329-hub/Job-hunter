"""Load rules: config/rules.default.json overlaid with config/my-rules.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = ROOT / "config" / "rules.default.json"
USER_RULES = ROOT / "config" / "my-rules.json"


def merge_rules(base: dict, override: dict) -> dict:
    out = dict(base)
    append = set(base.get("append_keys", []))
    for key, val in override.items():
        if key.startswith("_"):
            continue
        if key in append and isinstance(out.get(key), list) and isinstance(val, list):
            out[key] = out[key] + [v for v in val if v not in out[key]]
        elif key in append and isinstance(out.get(key), dict) and isinstance(val, dict):
            out[key] = {**out[key], **val}
        elif isinstance(out.get(key), dict) and isinstance(val, dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def load_rules(path: str | Path | None = None) -> dict:
    rules = json.loads(DEFAULT_RULES.read_text(encoding="utf-8"))
    user = Path(path) if path else USER_RULES
    if user.exists():
        rules = merge_rules(rules, json.loads(user.read_text(encoding="utf-8")))
    return rules
