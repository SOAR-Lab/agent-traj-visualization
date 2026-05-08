"""Shared constants and text helpers for trajectory processing."""

from __future__ import annotations

import json

from traceview_app.shared.constants import PROJECT_ROOT

UNLABELED_ACTION_LABEL = "Unlabeled"
UNLABELED_RELATION_LABEL = "Unlabeled"
VIEWER_EXPORT_CATEGORY = "Labeled trace"
LOCAL_SWEAGENT_TRAJECTORY_DIR = PROJECT_ROOT / "sweagent_claude4_trajs"
SUPPORTED_TRAJECTORY_SUFFIXES = {".traj", ".json", ".jsonl", ".log", ".txt"}


def coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, indent=2).strip()


def coerce_field_text(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(coerce_text(item) for item in value if item not in (None, "", []))
    return coerce_text(value)


def short_preview(value: str, limit: int = 140) -> str:
    normalized = " ".join(coerce_text(value).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."
