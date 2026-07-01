# Add ONNX file upload/import

## Context

NeuroGolf Lab currently lets the user re-import a graph only from ONNX artifacts the
tool itself already produced (`GET /api/best-graph/{task_id}` reads
`client/public/best/onnx/{task_id}.onnx` or `client/dist/best/onnx/{task_id}.onnx`,
see [server.py:827-838](../server.py#L827-L838) `_best_onnx_path` and
[server.py:841-984](../server.py#L841-L984) `onnx_to_gui_graph`). There is no way to load an
arbitrary external `.onnx` file into the GUI for editing. The user wants to be able to
upload any ONNX file and continue editing it visually, same as the existing "Load Graph"
(best-graph) flow.

The conversion logic in `onnx_to_gui_graph` (lines 849-970) already builds GUI
nodes/edges from an `onnx.ModelProto` and is not task-specific except for the file
lookup at line 842 and the `task_id`/`projectName` used in the returned metadata
(lines 972-984). This can be reused directly for uploaded bytes.

## Backend (`server.py`)

1. Refactor `onnx_to_gui_graph(task_id)`: extract the body (lines 843-984, i.e. everything
   after `model = onnx.load(path)`) into a new function
   `_onnx_model_to_gui_graph(model: onnx.ModelProto, *, project_name: str, task_id: str | None, source_label: str) -> dict`.
   `onnx_to_gui_graph` becomes a thin wrapper: resolve `path` via `_best_onnx_path`,
   `onnx.load(path)`, then call `_onnx_model_to_gui_graph(model, project_name=f"best-{task_id}-onnx", task_id=task_id, source_label=str(path.relative_to(ROOT)))`.
   This keeps `best_graph`/existing test (`tests/test_server.py` `test_best_graph_endpoint_imports_onnx_as_visual_nodes`) passing unchanged.

2. Add `POST /api/import-onnx`, multipart upload:
   ```python
   from fastapi import FastAPI, UploadFile, File, Form
   ...
   @app.post("/api/import-onnx")
   async def import_onnx(file: UploadFile = File(...), project_name: str | None = Form(None)):
       try:
           raw = await file.read()
           model = onnx.load_model_from_string(raw)
       except Exception as exc:
           return JSONResponse(status_code=400, content={"status": "failed", "reason": f"Invalid ONNX file: {exc}"})
       name = project_name or Path(file.filename or "uploaded").stem
       try:
           return _onnx_model_to_gui_graph(model, project_name=name, task_id=None, source_label=f"upload:{file.filename}")
       except Exception as exc:
           return JSONResponse(status_code=400, content={"status": "failed", "reason": str(exc)})
   ```
   - `task_id` is optional/`None` for uploads (an external file has no associated ARC task); `_onnx_model_to_gui_graph`'s returned dict sets `"taskId": task_id` (may be `None`), and `meta["source"] = source_label`.
   - Error response shape matches the existing pattern used by `export_onnx` / `best_graph` ([server.py:1180-1190](../server.py#L1180-L1190)).

3. Add `python-multipart` to [requirements.txt](../requirements.txt) (required by FastAPI for `UploadFile`/`Form`; currently absent).

4. Add a test in `tests/test_server.py` mirroring `test_best_graph_endpoint_imports_onnx_as_visual_nodes` (lines 271-282): POST the bytes of an existing fixture (`client/public/best/onnx/task001.onnx`, skip if missing) to `/api/import-onnx` via `files={"file": (...)}`, assert 200, `meta["rawOnnx"] is True`, non-empty nodes/edges, and `taskId` is `None`. Add a second test posting garbage bytes and asserting a 400 with `status: "failed"`.

## Frontend (`client/src/main.jsx`)

1. Import `FileUp` icon from `lucide-react` alongside the existing `Upload, Plus, ...` import ([client/src/main.jsx:5](../client/src/main.jsx#L5)) to visually distinguish "Import" from "Export ONNX" (which already uses `Upload`).

2. Add a hidden file input + button next to the existing "Load Graph" button
   ([client/src/main.jsx:743-746](../client/src/main.jsx#L743-L746)), available regardless of `bestTask`:
   ```jsx
   <input type="file" accept=".onnx" ref={importInputRef} style={{ display: "none" }}
          onChange={handleImportOnnxFile} />
   <button className="btn full" onClick={() => importInputRef.current?.click()}>
     <FileUp size={15} />Import ONNX
   </button>
   ```

3. Add `const importInputRef = useRef(null);` and a handler modeled on `loadBestGraph`
   ([client/src/main.jsx:554-573](../client/src/main.jsx#L554-L573)):
   ```jsx
   const handleImportOnnxFile = async (event) => {
     const file = event.target.files?.[0];
     event.target.value = "";
     if (!file) return;
     setStatus(`Importing ${file.name}`);
     const form = new FormData();
     form.append("file", file);
     try {
       const { data } = await axios.post("/api/import-onnx", form);
       setProjectName(data.projectName || file.name);
       setNodes(cloneGraph(data.nodes || []));
       setEdges(cloneGraph(data.edges || []));
       resetTransientGraphState();
       setStatus(`Imported ${file.name}: ${data.meta?.nodeCount || 0} raw nodes`);
       scheduleFitView();
     } catch (error) {
       const response = error.response?.data;
       const rawReason = response?.reason || response?.detail || error.message;
       setStatus(`Import failed: ${typeof rawReason === "string" ? rawReason : JSON.stringify(rawReason)}`);
     }
   };
   ```
   (axios sets the multipart boundary automatically when passed a `FormData` body — no manual `Content-Type` header needed.)

## Verification

- `pip install -r requirements.txt` (picks up `python-multipart`), then `python -m pytest tests/test_server.py -k onnx` to confirm the refactor keeps `test_best_graph_endpoint_imports_onnx_as_visual_nodes` green and the two new import tests pass.
- Start the backend (`python server.py` or existing run script) + `npm run dev` in `client/`, open the GUI, click "Import ONNX", pick a `.onnx` file from disk, confirm nodes/edges render and are editable, and that a bad/non-ONNX file shows a clear failure status instead of crashing.
