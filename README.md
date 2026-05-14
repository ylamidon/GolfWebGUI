# NeuroGolf Lab

[ Python 3.10+ ] [ FastAPI ] [ React ] [ ONNX ] [ ARC-AGI ] [ Headless Agents ]

NeuroGolf Lab is a browser-based ARC task viewer and visual ONNX graph editor. It lets you inspect ARC-style grid tasks, build candidate ONNX graphs by connecting nodes, validate against visible training examples, and push passing artifacts to a Hugging Face model repository.

The project is designed for two workflows:

- Human-in-the-loop solving in the web GUI.
- Headless AI-agent attempts through the same `/api/export` validation gate.

## Features

- Lazy-loads `task001` through `task400` from static JSON.
- Visual graph editor with named input handles and keyboard deletion.
- Dark UI with resizable task-preview and graph sections.
- Backend compiler for practical ARC primitives: constants, masks, arithmetic, reductions, coordinate grids, crop/slice, pad, concat, transpose, tile, resize, and convolution.
- Strict backend validation with ONNX Runtime before artifact upload.
- Hugging Face artifact push only after validation passes.
- Headless CLI for agents that posts graph JSON to the same export endpoint.

## Quick Start

```bash
python3 -m pip install -r requirements.txt
cd client
npm install
npm run build
cd ..
bash start.sh
```

`start.sh` will create `.env` from `.env.example` if needed, explain the required keys, and prompt for missing values.

Default local URL:

```text
http://127.0.0.1:8081
```

## Configuration

Create `.env` in the project root. Do not commit it.

Required for exporting artifacts:

```bash
HF_TOKEN="hf_..."
HF_REPO_ID="your-hf-username/neurogolf-handcrafted"
```

`HF_REPO_ID` must start with the Hugging Face username for `HF_TOKEN`. The server blocks export if those do not match, so a cloned setup cannot silently upload ONNX files to another user's repo.

Runtime settings:

```bash
HOST="127.0.0.1"
PORT="8081"
PUBLIC_HOSTNAME=""
```

Optional private values:

```bash
CLOUDFLARE_API_TOKEN=""
GITHUB_TOKEN=""
```

Recommended deployment: run the app on localhost and expose it through a protected tunnel such as Cloudflare Tunnel plus Cloudflare Access. Do not commit `.env`.

## Web GUI Workflow

1. Select an ARC task from the left panel.
2. Inspect the input/output examples.
3. Add nodes from the palette or quick-add dropdown.
4. Wire nodes with the named handles shown on each node.
5. Select nodes to edit shape, constants, and ONNX attributes.
6. Select nodes or edges and press `Delete` or `Backspace` to remove them.
7. Click `Export ONNX`.
8. The backend compiles, validates with ONNX Runtime, and uploads only if validation passes.

Useful first graph for a color remap:

```text
Input -> Equal(input, const color) -> Where(mask, const replacement, input) -> Output
```

## Headless Agent Workflow

Agents should use `scripts/agent_export.py`. This does not write ONNX directly; it submits graph JSON to the live backend.

Color remap shortcut:

```bash
python3 scripts/agent_export.py --task task276 --color-remap '{"6":2}'
```

Graph JSON:

```bash
python3 scripts/agent_export.py --task task010 --graph graph.json
```

The helper fills `trainingPairs` from the task JSON when they are not already present, posts to `/api/export`, and exits nonzero if validation or upload fails.

## Supported Nodes

Core:

```text
Input Output Constant Cast Identity
Equal Greater Less Not And Where
Add Sub Mul Div ReduceSum ArgMax
```

Spatial and coordinate:

```text
RowIndex ColIndex Slice Pad Concat Transpose Tile Resize Conv
```

All tensors are static, and the default ARC canvas is `[1,1,30,30]`.

## Kaggle Workflow

This app produces validated ONNX artifacts. Use the Kaggle CLI only after you have assembled the required competition submission package.

Typical Kaggle CLI flow:

```bash
kaggle competitions files -c neurogolf-2026
kaggle competitions submit -c neurogolf-2026 -f submission.zip -m "validated NeuroGolf Lab artifacts"
kaggle competitions submissions -c neurogolf-2026
```

Keep Kaggle credentials outside this repo, normally in `~/.kaggle/kaggle.json`.

## Public Repo Safety

Ignored by default:

```text
.env
.env.*
node_modules/
client/dist/
*.log
*.tar.gz
*.zip
__pycache__/
.pytest_cache/
```

Before publishing, run:

```bash
git status --short --ignored
grep -RInE 'hf''_[A-Za-z0-9]|GITHUB_TOKEN|CLOUDFLARE_API_TOKEN|PRIVATE KEY|[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=client/node_modules .
```

Only variable names and generic localhost examples should appear in source code. Real token values and deployment-specific hosts belong only in ignored local files.

## Development Checks

```bash
python3 -m pytest -q
cd client && npm run build
```

## License

Choose and add a license before relying on this as an open-source project.
