"""Iteration context summaries for collapsed graph views."""

from __future__ import annotations

import re
from collections import Counter

from traceview_app.constants import BAD_RELS, LOOPISH_RELS
from traceview_app.viewer_data import shorten
from traceview_app.models import EdgeRecord, IterationRecord

CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\((.*?)\)")
FILE_TAG_RE = re.compile(r"<file>(.*?)</file>")
PATH_RE = re.compile(
    r"(?<![\w./-])(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.-]+\.[A-Za-z0-9_]+"
)
QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')

ACTION_ALIASES = {
    "analyze": "analyze findings",
    "locate": "locate target",
    "localize": "locate target",
    "write_patch": "write patch",
    "write patch": "write patch",
    "errorresponse": "error response",
}


def _one_line(text: str) -> str:
    return " ".join((text or "").replace("\r\n", "\n").split())


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _quoted_args(text: str) -> list[str]:
    args = []
    for match in QUOTED_RE.finditer(text):
        value = match.group(1) or match.group(2)
        if value:
            args.append(value)
    return args


def _file_name(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    return normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized


def _looks_like_file_path(value: str) -> bool:
    normalized = value.replace("\\", "/").strip()
    if not normalized or re.search(r"\s", normalized):
        return False
    if any(char in normalized for char in "^$[]{}*+"):
        return False
    if "/" not in normalized:
        return False
    return bool(re.search(r"\.[A-Za-z0-9]{1,8}$", _file_name(normalized)))


def extract_file_mentions(*texts: str, limit: int = 4) -> list[str]:
    mentions = []
    for text in texts:
        if not text:
            continue
        mentions.extend(path for path in FILE_TAG_RE.findall(text) if _looks_like_file_path(path))
        mentions.extend(path for path in PATH_RE.findall(text) if _looks_like_file_path(path))
        mentions.extend(arg for arg in _quoted_args(text) if _looks_like_file_path(arg))
    return _unique(mentions)[:limit]


def _tool_label(tool_name: str) -> str:
    name = tool_name.lower()
    if "search" in name and "file" in name:
        return "search file"
    if "search" in name and "class" in name:
        return "search class"
    if "search" in name and "method" in name:
        return "search method"
    if "search" in name:
        return "search"
    if "patch" in name or "write" in name:
        return "write patch"
    return tool_name.replace("_", " ")


def summarize_action(action: str, max_len: int = 52) -> str:
    text = _one_line(action)
    if not text:
        return ""

    alias = ACTION_ALIASES.get(text.lower())
    if alias:
        return alias

    calls = CALL_RE.findall(text)
    if not calls:
        return shorten(text, max_len)

    tool_name, arg_text = calls[0]
    args = _quoted_args(arg_text)
    file_args = [arg for arg in args if _looks_like_file_path(arg)]
    non_file_args = [arg for arg in args if arg not in file_args]

    tool_label = _tool_label(tool_name)
    if file_args:
        summary = f"{tool_label} {_file_name(file_args[0])}"
    elif non_file_args:
        summary = f"{tool_label} {non_file_args[0]}"
    else:
        summary = tool_label

    if len(calls) > 1:
        summary = f"{summary} +{len(calls) - 1}"
    return shorten(summary, max_len)


def build_iteration_contexts(
    iterations: list[IterationRecord],
    log_data: dict[int, dict[str, str]],
    edge_records: list[EdgeRecord],
) -> list[IterationRecord]:
    enriched: list[IterationRecord] = []

    for iteration in iterations:
        steps = list(iteration["steps"])
        step_set = set(steps)

        action_summaries = _unique(
            [
                summarize_action(log_data.get(step, {}).get("action", ""))
                for step in steps
            ]
        )
        files = _unique(
            [
                file_path
                for step in steps
                for file_path in extract_file_mentions(
                    log_data.get(step, {}).get("thought", ""),
                    log_data.get(step, {}).get("action", ""),
                    log_data.get(step, {}).get("result", ""),
                )
            ]
        )

        relation_counts = Counter(
            edge["relation"]
            for edge in edge_records
            if edge["src_step"] in step_set or edge["dst_step"] in step_set
        )
        flagged_relations = sorted(
            relation
            for relation in relation_counts
            if relation in BAD_RELS or relation in LOOPISH_RELS
        )

        primary_action = action_summaries[0] if action_summaries else ""
        primary_file = _file_name(files[0]) if files else ""
        context_label = primary_action or primary_file
        if primary_action and primary_file and primary_file.lower() not in primary_action.lower():
            context_label = f"{primary_action} · {primary_file}"

        enriched.append(
            {
                **iteration,
                "action_summary": " | ".join(action_summaries[:2]),
                "files": files[:4],
                "context_label": context_label,
                "relation_count": sum(relation_counts.values()),
                "flagged_relations": flagged_relations,
            }
        )

    return enriched
