"""Viewer data loading and parsing helpers."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from traceview_app.shared.constants import (
    ACTIONS_CATEGORIES_CAT_COL,
    ACTIONS_CATEGORIES_FOLDER,
    ACTIONS_CATEGORIES_ITER_COL,
    BAD_RELS,
    CATEGORY_COLOR,
    LABELER_VIEWER_EXPORTS_PATH,
    LOOPISH_RELS,
    LOGS_DIR,
    REL_LABEL_COL,
    REL_SPECS,
    ROOT,
)
from traceview_app.shared.models import OverviewRow


def normalize_rel(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    return text[:1].upper() + text[1:] if text else ""


def shorten(text: str, length: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= length else text[: length - 1] + "…"


def category_color(category: str) -> str:
    key = (category or "").strip().lower()
    return CATEGORY_COLOR.get(key, "#4C78A8")


def list_task_files() -> list[str]:
    base = ROOT / ACTIONS_CATEGORIES_FOLDER
    if not base.exists():
        return []
    return sorted(path.name for path in base.glob("*.csv"))


@st.cache_data
def load_categories(filename: str) -> pd.DataFrame:
    path = ROOT / ACTIONS_CATEGORIES_FOLDER / filename
    df = pd.read_csv(path)

    required = {ACTIONS_CATEGORIES_ITER_COL, ACTIONS_CATEGORIES_CAT_COL}
    if not required.issubset(df.columns):
        raise ValueError(
            f"{path} must contain columns {sorted(required)}. Found: {list(df.columns)}"
        )

    df = df[[ACTIONS_CATEGORIES_ITER_COL, ACTIONS_CATEGORIES_CAT_COL]].copy()
    df[ACTIONS_CATEGORIES_ITER_COL] = df[ACTIONS_CATEGORIES_ITER_COL].astype(int)
    df[ACTIONS_CATEGORIES_CAT_COL] = df[ACTIONS_CATEGORIES_CAT_COL].astype(str)
    return df.sort_values(ACTIONS_CATEGORIES_ITER_COL).reset_index(drop=True)


@st.cache_data
def load_relation_labels(folder: str, filename: str) -> pd.DataFrame:
    path = ROOT / folder / filename
    if not path.exists():
        return pd.DataFrame(columns=[REL_LABEL_COL])

    df = pd.read_csv(path)
    if list(df.columns) != [REL_LABEL_COL]:
        raise ValueError(
            f"{path} must have exactly one column named '{REL_LABEL_COL}'. "
            f"Found: {list(df.columns)}"
        )

    df[REL_LABEL_COL] = df[REL_LABEL_COL].fillna("").astype(str)
    return df


def corresponding_log_path(csv_filename: str) -> Path:
    return LOGS_DIR / Path(csv_filename).with_suffix(".txt").name


@st.cache_data
def parse_reconstructed_log(path: Path) -> dict[int, dict[str, str]]:
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\bIteration\s+(\d+)\b", text)
    if len(parts) < 3:
        return {}

    parsed: dict[int, dict[str, str]] = {}
    delim_line = re.compile(r"^\s*[-=_]{3,}\s*$")

    def strip_trailing_delims(section: str) -> str:
        if not section:
            return ""
        lines = section.splitlines()
        while lines and (lines[-1].strip() == "" or delim_line.match(lines[-1])):
            lines.pop()
        return "\n".join(lines).strip()

    def extract_section(chunk: str, name: str, next_names: list[str]) -> str:
        match = re.search(rf"{name}:\s*(.*)", chunk, flags=re.DOTALL)
        if not match:
            return ""

        remaining = match.group(1)
        cut_positions = []
        for next_name in next_names:
            next_match = re.search(rf"\n{next_name}:\s*", remaining)
            if next_match:
                cut_positions.append(next_match.start())
        if cut_positions:
            remaining = remaining[: min(cut_positions)]
        return strip_trailing_delims(remaining)

    for index in range(1, len(parts) - 1, 2):
        try:
            iteration = int(parts[index])
        except ValueError:
            continue

        chunk = parts[index + 1].replace("\r\n", "\n")
        thought = extract_section(chunk, "Thought", ["Action", "RESULT", "Result"])
        action = extract_section(chunk, "Action", ["RESULT", "Result", "Thought"])
        result = extract_section(chunk, "Result", ["Thought", "Action"])
        if not result:
            result = extract_section(chunk, "RESULT", ["Thought", "Action"])

        parsed[iteration] = {
            "thought": thought,
            "action": action,
            "result": result,
        }

    return parsed


@st.cache_data
def load_results(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_labeler_export_metadata(path: Path = LABELER_VIEWER_EXPORTS_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    runs = payload.get("runs")
    if isinstance(runs, dict):
        return {
            str(filename): meta
            for filename, meta in runs.items()
            if isinstance(meta, dict)
        }

    return {
        str(filename): meta
        for filename, meta in payload.items()
        if isinstance(meta, dict)
    }


def get_patch_categories(task_id: str, results: dict) -> list[str]:
    if not results:
        return []

    matched = []
    for key, values in results.items():
        if task_id in set(values):
            matched.append(key)
    return matched


def task_reference_from_filename(filename: str) -> tuple[str, str, str] | None:
    stem = Path(filename).stem
    match = re.match(r"(.+)__(.+)-(\d+)$", stem)
    if not match:
        return None
    return match.groups()


def pull_request_url_from_filename(filename: str) -> str | None:
    reference = task_reference_from_filename(filename)
    if not reference:
        return None
    owner, repo, pull_number = reference
    return f"https://github.com/{owner}/{repo}/pull/{pull_number}"


def _extract_linked_issue_number(
    text: str,
    owner: str,
    repo: str,
    pull_number: str,
) -> str | None:
    if not text:
        return None

    keyword = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
    owner_repo = rf"(?:{re.escape(owner)}/{re.escape(repo)})?"
    patterns = [
        rf"\b{keyword}\s+https://github\.com/{re.escape(owner)}/{re.escape(repo)}/issues/(\d+)",
        rf"\b{keyword}\s+{owner_repo}#(\d+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            issue_number = match.group(1)
            if issue_number != pull_number:
                return issue_number
    return None


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def bug_report_url_from_filename(filename: str) -> str | None:
    reference = task_reference_from_filename(filename)
    if not reference:
        return None

    owner, repo, pull_number = reference
    request = Request(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TraceView",
        },
    )
    try:
        with urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    issue_number = _extract_linked_issue_number(
        payload.get("body", ""),
        owner,
        repo,
        pull_number,
    )
    if not issue_number:
        return None
    return f"https://github.com/{owner}/{repo}/issues/{issue_number}"


def derive_primary_patch_status(matched_categories: list[str]) -> str:
    priority = [
        ("resolved", "RESOLVED"),
        ("test_timeout", "TEST TIMEOUT"),
        ("test_errored", "TEST ERRORED"),
        ("no_apply", "PATCH NOT APPLIED"),
        ("no_generation", "NO GENERATION"),
        ("install_fail", "INSTALL FAIL"),
        ("reset_failed", "RESET FAILED"),
        ("applied", "APPLIED"),
        ("generated", "GENERATED"),
        ("with_logs", "HAS LOGS"),
    ]

    for key, label in priority:
        if key in matched_categories:
            return label

    return "UNKNOWN"


@st.cache_data
def build_overview_rows(
    task_files: tuple[str, ...],
    results_path: Path,
) -> list[OverviewRow]:
    results = load_results(results_path)
    labeler_exports = load_labeler_export_metadata()
    rows: list[OverviewRow] = []

    for filename in task_files:
        export_meta = labeler_exports.get(filename, {})
        is_labeler_export = bool(export_meta)
        task_id = str(export_meta.get("task_id") or Path(filename).stem)
        cat_df = load_categories(filename)
        ordered_categories = (
            cat_df.sort_values(ACTIONS_CATEGORIES_ITER_COL)[ACTIONS_CATEGORIES_CAT_COL]
            .astype(str)
            .tolist()
        )
        max_iteration = int(cat_df[ACTIONS_CATEGORIES_ITER_COL].max())

        relation_counts: Counter[str] = Counter()
        first_flagged_iteration: int | None = None

        for family in REL_SPECS:
            relation_frame = load_relation_labels(family, filename)
            if relation_frame.empty:
                continue

            for index, row in relation_frame.iterrows():
                relation = normalize_rel(row[REL_LABEL_COL])
                if not relation:
                    continue
                relation_counts[relation] += 1
                if relation in BAD_RELS and first_flagged_iteration is None:
                    first_flagged_iteration = int(index)

        if is_labeler_export:
            matched_patch_categories = []
            patch_status = "UNKNOWN"
            outcome = "unscored"
        else:
            matched_patch_categories = get_patch_categories(task_id, results)
            patch_status = derive_primary_patch_status(matched_patch_categories)
            if not matched_patch_categories:
                outcome = "unscored"
            else:
                outcome = "pass" if patch_status == "RESOLVED" else "fail"
        flagged_relations = sorted(
            relation
            for relation in relation_counts
            if relation in BAD_RELS or relation in LOOPISH_RELS
        )

        rows.append(
            {
                "filename": filename,
                "task_id": task_id,
                "agent_name": str(export_meta.get("agent_name") or "autocoderover"),
                "outcome": outcome,
                "patch_status": patch_status,
                "matched_patch_categories": matched_patch_categories,
                "iteration_count": max_iteration + 1,
                "categories": ordered_categories,
                "relation_counts": dict(relation_counts),
                "flagged_relations": flagged_relations,
                "first_flagged_iteration": first_flagged_iteration,
                "pull_request_url": (
                    None if is_labeler_export else pull_request_url_from_filename(filename)
                ),
            }
        )

    return rows
