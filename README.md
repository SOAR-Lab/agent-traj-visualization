# TraceView

TraceView is a Streamlit application for visualizing step-by-step agent trajectories as directed graphs over `Thought`, `Action`, and `Result` nodes. The app supports AutoCodeRover-style traces and uploaded user traces, and lets you inspect:

- step-level action categories
- labeled semantic relations between trajectory elements
- reconstructed trajectory text for each step
- final patch outcome metadata

The result is an interactive trace viewer for studying how an agent moves through a software engineering task, where it stays aligned, where it loops, and where it diverges or breaks down.

## Quick Start

If you only need the shortest path:

```powershell
uv sync
uv run streamlit run traceview.py
```

Then:

1. pick a task from the sidebar
2. start in `Detailed` mode
3. click a node to inspect its text and attached relations
4. switch to `Iteration` mode to see the compressed phase-level trajectory

## Current Status

The active application is:

- `traceview.py`

That file is only a thin Streamlit entrypoint. The actual implementation lives under:

- `traceview_app/`

Older Python versions of the project were moved into:

- `archive/python_prototypes/`

TraceView should be treated as the canonical version of the repo.

## What The App Does

For a selected task, the app combines four kinds of information:

1. A CSV that assigns an action category to each step.
2. Several CSVs that assign a relation label to specific edge families.
3. A reconstructed text log containing the original `Thought`, `Action`, and `Result` content for each step.
4. A JSON file containing patch outcome metadata.

From those sources it builds an interactive graph with two views:

- `Detailed` mode: one `T -> A -> R` triplet per step
- `Iteration` mode: consecutive steps with the same action category collapsed into higher-level grouped nodes

You can click any node to inspect the underlying text and the labeled relations attached to that node or grouped phase.

## Main Features

- Step-level trajectory graph over `Thought`, `Action`, and `Result`
- Relation families for:
  - `Thought -> Action`
  - `Thought -> Thought`
  - `Action -> Action`
  - `Result -> Thought`
  - `Result -> Action`
- Optional structural edge:
  - `Action -> Result (Structural)`
- Two graph modes:
  - `Detailed`
  - `Iteration`
- Relation filters:
  - only bad relations
  - only loop-ish relations
  - only no-influence relations
- Adjustable graph layout controls:
  - step spacing
  - lane gap
  - node size
  - label length
  - edge label visibility
- Inline inspector or separate inspector page
- Patch result summary with PASS/FAIL marking on the final result node
- Relation metrics summary across the selected task

## Repository Layout

```text
agent-traj-visualization/
|- traceview.py
|- README.md
|- pyproject.toml
|- uv.lock
|- schema.txt
|- llm_label_demo.ipynb
|- traceview_app/
|  |- app.py
|  |- constants.py
|  |- formatting.py
|  |- graph_builder.py
|  |- inspector_ui.py
|  |- iteration_context.py
|  |- iteration_ui.py
|  |- labeling_common_ui.py
|  |- labeling_ingest_ui.py
|  |- labeling_router.py
|  |- labeling_state.py
|  |- labeling_summary_ui.py
|  |- labeling_workspace_ui.py
|  |- layout_ui.py
|  |- models.py
|  |- node_ids.py
|  |- overview_ui.py
|  |- trajectory_parser.py
|  |- viewer_data.py
|- autocoderover_csv/
|  |- actions_categories/
|  |- thought_action/
|  |- thought_thought/
|  |- action_action/
|  |- result_thought/
|  |- result_action/
|- reconstructed_autocoderover/
|- data/
|  |- json/
|     |- results.json
|     |- normalized_trace.json
|     |- graph_trace.json
|     |- file_context.json
|     |- agraph_graph.json
|- archive/
|  |- python_prototypes/
```

## Which Files Matter For The Current App

The current Streamlit app primarily depends on:

- `traceview.py`
- `traceview_app/`
- `autocoderover_csv/`
- `reconstructed_autocoderover/`
- `data/json/results.json`

The other JSON files in `data/json/` are legacy artifacts from earlier prototypes and are not used by TraceView.

Large raw trajectory folders from earlier experiments are intentionally not included in this checkout. In particular, the archived AXE and SWE-agent prototypes refer to local folders named `AXE_logs/` and `sweagent_claude4_trajs/`, but those folders were removed from the repo because they were too large. Restore those folders locally only if you need to run the archived prototype scripts; TraceView does not require them.

## Environment And Setup

### Requirements

The project currently declares:

- Python `>=3.14`

The local environment in this repo is using:

- Python `3.14.3`

Primary runtime dependencies include:

- `streamlit`
- `streamlit-agraph`
- `pandas`

### Install With `uv`

If you use `uv`, the simplest setup is:

```powershell
uv sync
```

Then run the app with:

```powershell
uv run streamlit run traceview.py
```

### Install Without `uv`

If you prefer a plain virtual environment, create one and install the dependency set declared in `pyproject.toml`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install dotenv google-genai ipykernel jsonlines pandas pandas-stubs plotly streamlit streamlit-agraph tqdm
```

Then run:

```powershell
streamlit run traceview.py
```

## Running The App

From the project root:

```powershell
streamlit run traceview.py
```

If you already have a local virtual environment in this checkout:

```powershell
.venv\Scripts\streamlit.exe run traceview.py
```

After launch, the app opens a browser page where you can:

1. choose a task file from the sidebar
2. switch between `Detailed` and `Iteration` graph mode
3. filter relation types
4. adjust graph layout settings
5. click nodes to inspect the underlying content

## Relationship Labeling

The `Labeling` page provides a staged annotation workflow for raw agent traces. It accepts uploaded `.traj`, `.json`, `.jsonl`, `.log`, and `.txt` files, or a `.zip` containing supported trace files. If a local `sweagent_claude4_trajs/` folder exists, the page can also load that folder directly.

The labeler parses each trajectory into Thought / Action / Result steps and generates the same relationship families used by the graph viewer:

- `Thought -> Action`
- `Thought -> Thought`
- `Action -> Action`
- `Result -> Thought`
- `Result -> Action`

After ingest, the page shows annotation progress, a completion summary, and a single-run workspace. The workspace label table lets users edit the relationship label column and export either a JSON evidence record or a zip of viewer-compatible relation CSVs. Label options are constrained by relationship family; unedited rows remain `Unlabeled` and export as blank relation labels.

## Data Model And Naming Convention

The app assumes that a single task is identified by a shared filename stem.

Example:

- `django__django-11099.csv`
- `django__django-11099.txt`

The stem is:

- `django__django-11099`

That stem is used to align:

- the action category CSV
- the relation-label CSVs
- the reconstructed log
- the patch outcome entry in `results.json`

### GitHub Link Convention

If the filename stem matches:

- `owner__repo-pullRequestNumber`

the app derives a GitHub pull request URL automatically.

Example:

- `django__django-11099`
  becomes
- `https://github.com/django/django/pull/11099`

When GitHub exposes a linked bug report in the pull request body, the app also shows a separate bug report link. This lookup uses GitHub's public API and is cached for 24 hours. Some tasks do not have a separate issue link available, so the bug report button is shown only when it can be resolved.

## Expected Input Files

### 1. Action Category CSV

Location:

- `autocoderover_csv/actions_categories/<task>.csv`

Required columns:

- `iteration`
- `category`

Example:

```csv
iteration,category
0,Search
1,Explain
2,Locate
3,Generate Fix
```

This file drives:

- the set of displayed steps
- the action-node color
- the grouped-node construction in iteration mode

### 2. Relation Label CSVs

Locations:

- `autocoderover_csv/thought_action/<task>.csv`
- `autocoderover_csv/thought_thought/<task>.csv`
- `autocoderover_csv/action_action/<task>.csv`
- `autocoderover_csv/result_thought/<task>.csv`
- `autocoderover_csv/result_action/<task>.csv`

Required schema:

- exactly one column named `label`

Example:

```csv
label
Alignment
Misalignment
Misalignment
Alignment
```

Each row index is interpreted as a source step index. The destination step is determined by the relation family:

- `Thought -> Action`: same step
- `Thought -> Thought`: next step
- `Action -> Action`: next step
- `Result -> Thought`: next step
- `Result -> Action`: next step

If a relation file is missing for a task, the app treats that family as empty instead of crashing.

### 3. Reconstructed Log

Location:

- `reconstructed_autocoderover/<task>.txt`

Expected format:

- repeated `Iteration N` blocks
- each block contains `Thought:`, `Action:`, and `Result:` sections

Example shape:

```text
Iteration 0

Thought:
...

Action:
...

Result:
...
```

The parser is rule-based and extracts the text content for those three sections per iteration.

If the log file is missing or malformed, the graph still renders, but the inspector may show empty content.

### 4. Patch Results JSON

Location:

- `data/json/results.json`

Expected shape:

- a JSON object whose keys are patch outcome categories
- each value is a list of task ids

Example:

```json
{
  "resolved": ["django__django-11099"],
  "generated": ["django__django-11099", "sympy__sympy-24102"],
  "no_apply": [],
  "test_errored": []
}
```

The app reduces the matched categories to a single primary status using a fixed priority order. That status is used in:

- the patch overview summary
- the PASS/FAIL styling of the final result node

## How The Graph Is Built

### Detailed Mode

In `Detailed` mode, every step `i` becomes three nodes:

- `T_i` for Thought
- `A_i` for Action
- `R_i` for Result

The graph is laid out in horizontal time order, with separate vertical lanes for thought, action, and result.

Semantic edges are then added from the relation CSVs. Each edge:

- has a fixed source and target node type based on its family
- gets its label from the normalized `label` column
- gets its color from the relation-to-color mapping

The final result node is special:

- it is enlarged relative to the other result nodes
- it is colored green and labeled `PASS` when the primary patch status is `RESOLVED`
- otherwise it is colored red and labeled `FAIL`

An optional structural edge from `Action -> Result` can also be rendered for each step.

### Iteration Mode

In `Iteration` mode, the app groups consecutive steps with the same action category into a single higher-level node.

Example:

- if steps `4`, `5`, and `6` are all `Search`
- they become one grouped node such as `I2`

Grouped nodes are labeled with:

- an `I#` identifier
- the action category name

Then the app aggregates detailed semantic edges into cross-group edges:

- all detailed edges between two grouped nodes are collected
- relation labels are counted
- the most frequent relation becomes the displayed label and color

If no semantic filter is active, gray chronological edges are also added between adjacent grouped nodes to preserve the overall sequence.

## Relation Semantics And Filters

The app normalizes relation labels by:

- trimming whitespace
- converting `_` and `-` variants to spaces
- standardizing capitalization

Several labels are grouped into higher-level visual categories:

- good flow:
  - `Alignment`
  - `Follow-up`
  - `Follow up`
  - `Refinement`
  - `Informative`
  - `Triggering`
- loop-ish:
  - `Redundancy`
  - `Repetition`
- bad:
  - `Misalignment`
  - `Misinterpretation`
  - `Contradiction`
- divergence:
  - `Divergence`
- no influence:
  - `No influence`
  - `No-influence`

Sidebar filters let you isolate:

- bad relations only
- loop-ish relations only
- no-influence relations only

These filters apply before graph edges are built.

## Using The Interface

### Sidebar

The sidebar provides:

- dataset selection
- graph mode toggle
- separate-page inspector toggle
- detailed-mode edge family selection
- detailed-mode structural edge selection
- relation filters
- layout controls
- edge-label toggle

Note:

- edge family selection is intentionally hidden in `Iteration` mode, because grouped mode shows the aggregated result of all enabled semantic families

### Main Page Sections

The main graph page contains:

1. a report/patch overview
2. a shared legend
3. a short graph guide for the current mode
4. the graph canvas
5. the inspector, or a message telling you to click a node
6. relationship metrics

### Inspector

The inspector supports two workflows:

- inline inspection below the graph
- a separate inspector page in the same browser tab

In detailed mode, clicking a node shows:

- the selected step and node type
- its action category if available
- incoming and outgoing relations touching that node
- the underlying `Thought`, `Action`, or `Result` text

In iteration mode, clicking a grouped node shows:

- the grouped iteration id
- the action category
- relations from previous grouped units
- relations to later grouped units
- the full text content for all member steps

## Relationship Metrics

The app computes task-level summary counts over the raw labeled relation records:

- total labeled relations
- counts by relationship label
- counts by edge family

These metrics are shown for the selected task regardless of whether individual relation edges are currently visible after filtering.

## Troubleshooting

### The app says "No files found"

Check that:

- `autocoderover_csv/actions_categories/` exists
- it contains one or more `.csv` files

### The graph loads but relations are missing

Check that:

- the task has matching files in the relation folders
- each relation CSV has exactly one column named `label`

### The inspector is empty

Check that:

- `reconstructed_autocoderover/<task>.txt` exists
- it contains `Iteration`, `Thought`, `Action`, and `Result` sections

### The patch result shows `UNKNOWN`

Check that:

- the task id appears in `data/json/results.json`

### The separate inspector page keeps opening

That behavior is controlled by the sidebar toggle:

- `Open inspector on separate page`

The current app persists that preference so returning from the inspector should preserve the toggle state.
