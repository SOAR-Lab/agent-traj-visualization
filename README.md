# TraceView

TraceView is a Streamlit application for labeling and visualizing step-by-step agent trajectories as directed graphs over `Thought`, `Action`, and `Result` nodes. The app supports bundled AutoCodeRover-style traces and uploaded user traces, and lets you inspect:

- step-level action categories
- labeled semantic relations between trajectory elements
- reconstructed trajectory text for each step
- final patch outcome metadata when it is available for bundled datasets

The result is an interactive trace viewer for studying how an agent moves through a software engineering task, where it stays aligned, where it loops, and where it diverges or breaks down.

## Quick Start

If you only need the shortest path:

```shell
uv sync
uv run streamlit run traceview.py
```

If you do not have `uv`, either install it from the official [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) or use Python's built-in `venv` plus `pip`:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
streamlit run traceview.py
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
streamlit run traceview.py
```

Then:

1. use `Labeling` to upload or paste a raw trajectory, label actions first, then label relationships
2. send the labeled run to `Overview`, or open an existing run from `Overview`
3. open `Analysis`, which starts in `Iteration` mode by default
4. switch to `Detailed` mode when you need the full `Thought -> Action -> Result` step graph

## Current Status

The active application is:

- `traceview.py`

That file is only a thin Streamlit entrypoint. The actual implementation lives under:

- `traceview_app/`

TraceView should be treated as the canonical version of the repo.

## Evaluation Materials

Evaluator-facing materials live in:

- `docs/evaluation_instructions.md`
- `docs/evaluation_video_script.md`
- `docs/User Survey on Trajectory Analysis Tool - Google Forms.pdf`
- `docs/images/`, which contains screenshots used by the evaluator guide
- `evaluation_samples/`, which contains short 8-step SWE-agent `.traj` fixtures
- `tools/create_evaluation_samples.py`, which regenerates those fixtures from local SWE-agent trajectories

## What The App Does

For a selected task, the app combines up to four kinds of information:

1. A CSV that assigns an action category to each step.
2. Several CSVs that assign a relation label to specific edge families.
3. A reconstructed text log containing the original `Thought`, `Action`, and `Result` content for each step.
4. A JSON file containing patch outcome metadata for bundled AutoCodeRover tasks.

From those sources it builds an interactive graph with two views:

- `Iteration` mode: consecutive steps with the same action category collapsed into higher-level grouped nodes
- `Detailed` mode: one `T -> A -> R` triplet per step

You can click any node to inspect the underlying text and the labeled relations attached to that node or grouped phase.

Uploaded user traces can be exported into the same viewer-compatible CSV structure and sent to Overview. They do not have AutoCodeRover `results.json` entries, so their patch result is shown as unscored.

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
  - `Iteration` by default
  - `Detailed`
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
- Patch result summary with PASS/FAIL marking on the final result node when result metadata is available
- Relation metrics summary across the selected task
- Raw-trace labeling workflow with action labels first, then relationship labels
- Compact labeling legends in the labeling sidebar

## Repository Layout

```text
agent-traj-visualization/
|- traceview.py
|- README.md
|- pyproject.toml
|- uv.lock
|- docs/
|  |- evaluation_instructions.md
|  |- evaluation_video_script.md
|  |- User Survey on Trajectory Analysis Tool - Google Forms.pdf
|  |- images/
|- evaluation_samples/
|  |- README.md
|  |- *.traj
|- tools/
|  |- create_evaluation_samples.py
|- schema.txt
|- llm_label_demo.ipynb
|- traceview_app/
|  |- app.py
|  |- layout_ui.py
|  |- analysis/
|  |  |- route.py
|  |  |- sidebar_ui.py
|  |  |- graph_builder.py
|  |  |- inspector_ui.py
|  |  |- iteration_ui.py
|  |  |- iteration_context.py
|  |  |- view_context.py
|  |- labeling/
|  |  |- router.py
|  |  |- ingest_ui.py
|  |  |- summary_ui.py
|  |  |- state.py
|  |  |- common_ui.py
|  |  |- workspace_ui.py
|  |  |- workspace_action_ui.py
|  |  |- workspace_relationship_ui.py
|  |  |- workspace_sidebar.py
|  |  |- workspace_shared.py
|  |- overview/
|  |  |- ui.py
|  |  |- data.py
|  |- shared/
|  |  |- constants.py
|  |  |- formatting.py
|  |  |- models.py
|  |  |- node_ids.py
|  |- trajectory/
|     |- parsers.py
|     |- relationships.py
|     |- exports.py
|     |- common.py
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
|     |- labeler_viewer_exports.json
|     |- normalized_trace.json
|     |- graph_trace.json
|     |- file_context.json
|     |- agraph_graph.json
```

## Which Files Matter For The Current App

The current Streamlit app primarily depends on:

- `traceview.py`
- `traceview_app/`
- `autocoderover_csv/`
- `reconstructed_autocoderover/`
- `data/json/results.json`
- `data/json/labeler_viewer_exports.json`

`results.json` is specific to the bundled AutoCodeRover dataset. User-uploaded trajectories sent from Labeling to Overview are tracked through `labeler_viewer_exports.json` and are treated as unscored because TraceView cannot infer patch outcomes for arbitrary uploaded logs.

The other JSON files in `data/json/` are legacy artifacts from earlier prototypes and are not used by TraceView.

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

### If You Do Not Have `uv`

You have two options:

- Install `uv` from the official [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/), then use the `uv sync` commands below.
- Use Python's built-in `venv` module and `pip`, which requires no separate project-management tool.

### Install With `uv`

If you use `uv`, the simplest setup is:

```shell
uv sync
```

Then run the app with:

```shell
uv run streamlit run traceview.py
```

### Install With `venv` And `pip`

If you prefer built-in Python tooling, create a virtual environment and install the project dependencies from `pyproject.toml`:

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Then run:

```shell
streamlit run traceview.py
```

## Running The App

From the project root:

```shell
streamlit run traceview.py
```

If you already have a local virtual environment in this checkout:

Windows PowerShell:

```powershell
.venv\Scripts\streamlit.exe run traceview.py
```

macOS/Linux:

```bash
.venv/bin/streamlit run traceview.py
```

After launch, the app opens a browser page where you can:

1. upload or paste trajectories in `Labeling`
2. send labeled trajectories to `Overview`
3. open a run in `Analysis`
4. switch between `Iteration` and `Detailed` graph mode
5. filter relation types
6. adjust graph layout settings
7. click nodes to inspect the underlying content

## Relationship Labeling

The `Labeling` page provides a staged annotation workflow for raw agent traces. It accepts pasted text, uploaded `.traj`, `.json`, `.jsonl`, `.log`, and `.txt` files, or a `.zip` containing supported trace files. If a local `sweagent_claude4_trajs/` folder exists, the page can also load that folder directly.

The labeler parses each trajectory into Thought / Action / Result steps and generates the same relationship families used by the graph viewer:

- `Thought -> Action`
- `Thought -> Thought`
- `Action -> Action`
- `Result -> Thought`
- `Result -> Action`

After ingest, the page shows annotation progress, a completion summary, and a single-run workspace. The workspace is intentionally ordered:

1. Label every action category first.
2. Continue to relationship labels.
3. Export the labeled run or send it to Overview.

The action-labeling table assigns one action category per iteration. These labels become the action-category CSV used by Overview and Analysis.

The relationship-labeling table lets users edit the relationship label column. Label options are constrained by relationship family; unedited rows remain `Unlabeled` and export as blank relation labels.

The labeling sidebar shows progress, the current step's compact legend, navigation between action and relationship labeling, and export controls once export is available.

The completion summary focuses on coverage: action-label progress, relationship-label progress, relationship distribution, behavior distribution, action-category distribution, and issue checks. It is a review page; annotations remain editable in the workspace.

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

For uploaded traces sent from Labeling to Overview, TraceView creates viewer-compatible files using a generated CSV filename and records the uploaded trace metadata separately. These runs are still aligned by filename for graph rendering, but they do not require or receive a `results.json` entry.

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
3,Generate fix
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
- the PASS/FAIL/UNSCORED styling of the final result node

This file is only used for bundled AutoCodeRover-style tasks. Uploaded user traces are shown as unscored unless matching result metadata is added manually.

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
- it is colored gray and labeled `UNSCORED` when patch metadata is unavailable
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

Then the app aggregates `Action -> Action` semantic edges into cross-group edges between collapsed iteration nodes.

If no semantic filter is active, gray chronological edges are also added between adjacent grouped nodes to preserve the overall sequence.

TraceView still contains a heuristic iteration-context extractor, but the derived context text is currently hidden from the UI because uploaded logs can come from inconsistent agent formats.

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
- graph mode toggle, defaulting to `Iteration`
- separate-page inspector toggle
- detailed-mode edge family selection
- detailed-mode structural edge selection
- relation filters
- layout controls
- edge-label toggle

Note:

- edge family selection is intentionally hidden in `Iteration` mode, because grouped mode shows cross-iteration `Action -> Action` relation edges plus chronological sequence edges

### Main Page Sections

The main graph page contains:

1. a report/patch overview
2. the graph canvas
3. the inspector, or a message telling you to click a node
4. support tabs for guide, legend, and relationship metrics

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

Derived action summaries and file-mention context for grouped iterations are currently hidden by default.

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

### The patch result shows `UNKNOWN` or `UNSCORED`

For uploaded user traces, this is expected because arbitrary uploads do not have AutoCodeRover result metadata.

For bundled AutoCodeRover tasks, check that:

- the task id appears in `data/json/results.json`

### The separate inspector page keeps opening

That behavior is controlled by the sidebar toggle:

- `Open inspector on separate page`

The current app persists that preference so returning from the inspector should preserve the toggle state.
