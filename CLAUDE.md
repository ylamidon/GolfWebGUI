# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NeuroGolf Lab: a browser-based ARC-AGI task viewer and visual ONNX graph editor. A human connects nodes in a
React Flow canvas to build a candidate ONNX graph for a given `taskNNN`; a FastAPI backend compiles that graph
to ONNX, validates it against the task's training pairs with ONNX Runtime, and — only if validation passes —
pushes the artifact to a Hugging Face model repo. Headless agents can do the same thing via
`scripts/agent_export.py` against the same `/api/export` endpoint. There is no path that writes ONNX files
directly; the compiler + validator is the only way artifacts get produced.

## Commands

```bash
# Backend
python3 -m pip install -r requirements.txt
python3 -m pytest -q                       # run all backend tests
python3 -m pytest tests/test_server.py -k onnx   # run a subset by keyword
bash start.sh                              # (or start.ps1 on Windows) creates .env from .env.example, then runs the app

# Frontend
cd client && npm install
cd client && npm run dev                   # vite dev server on :5173 (proxies API calls to backend)
cd client && npm run build                 # build client/dist, which server.py serves at "/"
cd client && npm run test:e2e              # Playwright e2e (set NEUROGOLF_E2E_BASE_URL, default http://127.0.0.1:8081)

# Headless agent export (backend must be running)
python3 scripts/agent_export.py --task task276 --color-remap '{"6":2}'
python3 scripts/agent_export.py --task task010 --graph graph.json
```

Default local URL: `http://127.0.0.1:8081`. Both backend tests and a frontend build should pass before
committing (see AGENTS.md).

## Architecture

- `server.py` — the entire backend: FastAPI app, the ONNX compiler (`compile_graph`), the validator
  (`validate_model`), the export/compile/run endpoints, and ONNX->GUI graph import
  (`onnx_to_gui_graph` / `_onnx_model_to_gui_graph`). There is no separate router/model/service split — read
  this file top to bottom to understand a request's full lifecycle.
- `client/src/main.jsx` — the entire frontend (React Flow canvas, node palette, inspector panel, project
  save/load, export payload preview). Single-file SPA; no component directory to search.
- `client/public/tasks/` and `client/dist/tasks/` — static `taskNNN.json` ARC task files (task001-task400),
  each with `train`/`test` grid pairs. `client/dist` is the built output served at `/` when present; `public`
  is the dev-time source. Both are gitignored — do not assume they exist on a fresh checkout without a build.
- `client/public/best/onnx/{taskId}.onnx` (and the `dist` equivalent) — reference "best submission" ONNX
  files. `GET /api/best-graph/{task_id}` loads one and converts it into GUI nodes/edges via
  `_onnx_model_to_gui_graph`, which is also reused by `POST /api/import-onnx` for arbitrary uploaded `.onnx`
  files (see `docs/onnx-import-plan.md` for the design rationale).
- `scripts/agent_export.py` — headless client for agents. Builds a graph payload (or loads one from JSON),
  fills `trainingPairs` from the local task JSON if absent, and POSTs to `/api/export`. Never writes ONNX
  directly.

### Graph JSON shape

Nodes: `{"id", "type": "op", "data": {"opType": "...", "shape": "1,1,30,30", "attrs": {...} | "attrsText": "..."}}`.
Edges: `{"source", "target", "targetHandle"}` where `targetHandle` selects a named input slot (e.g. `a`/`b` for
binary ops, `condition`/`true`/`false` for `Where`, `input` for unary ops) — see `INPUT_SLOT_ORDER` in
server.py. All tensors are static-shape; the canonical ARC canvas is `[1, 1, 30, 30]` (`CANVAS_SHAPE`).
Supported/banned ops are enumerated in `SUPPORTED_OPS` / `BANNED_OPS` in server.py — extending node support
means adding shape-inference + ONNX-attrs logic there (see `COMPILER_TODOS.md` for the planned op rollout,
organized in phases by how much shape-inference work each op needs).

### Validation gate (`/api/export`)

`compile_graph` -> `validate_model` -> `save_model` -> HF upload, in that order. `validate_model` runs three
phases (see server.py's `ValidationError` messages): Phase 1 Strict Equivalence (output must exactly match
every training pair, on the pair's own grid size), Phase 2 Canvas Test (must also run cleanly on the full
30x30 canvas), Phase 3 Color Bounds (output values must be finite, integer, and in `[0, 9]`). A graph is only
"successful" if all three pass — HF upload happens strictly after. If upload itself fails, the endpoint
returns `status: "upload_failed"` (not a validation failure) so callers can tell the difference.
`_assert_hf_repo_matches_token` blocks export if `HF_REPO_ID`'s namespace doesn't match the `HF_TOKEN` owner,
so a cloned setup can't accidentally push to someone else's repo.

`/api/compile` and `/api/run` reuse `compile_graph` but skip training-pair validation and HF upload — they're
for in-GUI compile/run-preview feedback, not for producing artifacts.

## Configuration

`.env` in project root (gitignored, created from `.env.example` by `start.sh`/`start.ps1`):
`HF_TOKEN`, `HF_REPO_ID` (must be under the token owner's namespace), `HOST`, `PORT`, `PUBLIC_HOSTNAME`, and
optionally `CLOUDFLARE_API_TOKEN`/`GITHUB_TOKEN`. Never print or commit `.env` values, tokens, or real
deployment hostnames — see the "Public Repo Safety" grep check in README.md before publishing anything.

## Working conventions (see AGENTS.md / SKILL.md for full detail)

- Prefer the GUI workflow or `scripts/agent_export.py` over hand-writing ONNX; hand-written ONNX is for
  diagnostics only.
- A candidate graph is not "done" until `/api/export` validation passes — report validation results
  explicitly rather than assuming success.
- Do not run Kaggle CLI submissions unless the user explicitly asks.
- Run `python3 -m pytest -q` and `cd client && npm run build` before considering a change complete.
