"""Shared UI formatting helpers."""

from __future__ import annotations

import re

import streamlit as st


def format_task_name(task_id: str) -> str:
    match = re.match(r"(.+)__(.+)-(\d+)$", task_id)
    if not match:
        return task_id
    _, repo, issue = match.groups()
    return f"{repo} #{issue}"


def format_step_range(steps: list[int]) -> str:
    if not steps:
        return ""
    if len(steps) == 1:
        return str(steps[0])
    return f"{steps[0]}-{steps[-1]}"


def wrapped_log_block(text: str) -> None:
    text = text or "(empty)"
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    st.code(text, language=None, wrap_lines=True)
