"""Ingest and progress screens for relationship labeling."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from traceview_app.constants import (
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
)
from traceview_app.labeling_common_ui import (
    render_labeling_header,
    render_parser_warnings,
)
from traceview_app.labeling_state import (
    LABELER_ERRORS_STATE_KEY,
    LABELER_PASTE_STATE_KEY,
    LABELER_PROGRESS_ADVANCED_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_UPLOAD_SIGNATURE_STATE_KEY,
    TRACE_UPLOAD_TYPES,
    active_source_meta,
    annotation_stats,
    format_size,
    labels,
    selected_trajectory,
    start_annotation_from_local_folder,
    start_annotation_from_sources,
)
from traceview_app.trajectory_parser import LOCAL_SWEAGENT_TRAJECTORY_DIR


def _render_ingest_dropzone() -> tuple[list[tuple[str, bytes]], bool] | None:
    _, upload_col, _ = st.columns([0.25, 0.5, 0.25])
    with upload_col:
        uploaded_files = st.file_uploader(
            "Drop or choose trace files",
            type=TRACE_UPLOAD_TYPES,
            accept_multiple_files=True,
            help=".jsonl, .json, .traj, .log, .txt, or .zip up to 25 MB",
        )
        st.caption("or")

        with st.popover("Paste a trace", use_container_width=True):
            pasted_trace = st.text_area(
                "Paste trace text",
                key=LABELER_PASTE_STATE_KEY,
                height=170,
                placeholder="Paste raw trace text here.",
            )
            if st.button(
                "Annotate pasted trace",
                type="primary",
                width="stretch",
                disabled=not pasted_trace.strip(),
            ):
                return [("pasted-trace.txt", pasted_trace.encode("utf-8"))], False

        if LOCAL_SWEAGENT_TRAJECTORY_DIR.exists():
            if st.button("Load local SWE-agent folder", width="stretch"):
                if start_annotation_from_local_folder():
                    st.rerun()

    if not uploaded_files:
        return None
    return [
        (uploaded_file.name, uploaded_file.getvalue())
        for uploaded_file in uploaded_files
    ], True


def render_ingest_screen() -> None:
    render_labeling_header("INGEST RAW TRACE", "Paste or upload a raw agent trace.")

    ingest_result = _render_ingest_dropzone()
    if ingest_result:
        sources, dedupe_upload = ingest_result
        upload_signature = tuple((name, len(contents)) for name, contents in sources)
        if (
            not dedupe_upload
            or upload_signature != st.session_state.get(LABELER_UPLOAD_SIGNATURE_STATE_KEY)
        ):
            st.session_state[LABELER_UPLOAD_SIGNATURE_STATE_KEY] = upload_signature
            if start_annotation_from_sources(sources):
                st.rerun()

    render_parser_warnings(
        st.session_state.get(LABELER_ERRORS_STATE_KEY, []),
        expanded=True,
    )


def _render_progress_panel(
    *,
    steps_count: int,
    candidate_count: int,
    labeled_count: int,
    progress: float,
) -> None:
    percent = round(progress * 100)
    edge_progress = labeled_count / candidate_count if candidate_count else 0
    progress_rows = pd.DataFrame(
        [
            {
                "Task": "Parsing raw trace",
                "Status": "done",
                "Detail": (
                    f"Found {steps_count} iterations, "
                    f"{steps_count * 3} turns"
                ),
            },
            {
                "Task": "Classifying node types",
                "Status": "done",
                "Detail": (
                    f"{steps_count} thoughts, "
                    f"{steps_count} actions, "
                    f"{steps_count} results"
                ),
            },
            {
                "Task": "Labeling relationships",
                "Status": "running",
                "Detail": f"{labeled_count} of {candidate_count} edges labeled",
            },
        ]
    )

    with st.container(border=True):
        st.caption("PROGRESS")
        st.progress(progress, text=f"Progress {percent}%")
        st.dataframe(progress_rows, hide_index=True, width="stretch")
        st.progress(
            edge_progress,
            text=f"Relationship labels: {labeled_count} of {candidate_count}",
        )


def render_annotating_screen() -> None:
    trajectory = selected_trajectory()
    if trajectory is None:
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
        st.rerun()

    meta = active_source_meta()
    size_label = format_size(meta.get("bytes") if isinstance(meta.get("bytes"), int) else None)
    uploaded_meta = f"{size_label} - uploaded just now" if size_label else "uploaded just now"
    render_labeling_header(
        "ANNOTATING",
        str(meta.get("name") or trajectory.source_name),
        uploaded_meta,
    )

    stats = annotation_stats(trajectory, labels())
    progress = 0.68

    _render_progress_panel(
        steps_count=len(trajectory.steps),
        candidate_count=stats.candidate_count,
        labeled_count=stats.labeled_count,
        progress=progress,
    )

    _, cancel_col = st.columns([0.9, 0.1])
    with cancel_col:
        if st.button("Cancel"):
            st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
            st.rerun()

    if not st.session_state.get(LABELER_PROGRESS_ADVANCED_STATE_KEY, False):
        st.session_state[LABELER_PROGRESS_ADVANCED_STATE_KEY] = True
        time.sleep(0.8)
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_COMPLETE
        st.rerun()
