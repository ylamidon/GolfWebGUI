#!/usr/bin/env python3
"""Headless NeuroGolf Lab export helper for agents.

This intentionally uses the same /api/export path as the GUI. It does not
write ONNX directly.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASK_DIRS = [ROOT / "client" / "dist" / "tasks", ROOT / "client" / "public" / "tasks"]


def load_task(task_id: str) -> dict[str, Any]:
    for task_dir in TASK_DIRS:
        path = task_dir / f"{task_id}.json"
        if path.exists():
            return json.loads(path.read_text())
    raise SystemExit(f"could not find {task_id}.json in {[str(path) for path in TASK_DIRS]}")


def color_remap_graph(task_id: str, mapping: dict[str, int]) -> dict[str, Any]:
    nodes = [
        {"id": "input_1", "type": "op", "position": {"x": 70, "y": 80}, "data": {"label": "input_1", "opType": "Input", "shape": "1,1,30,30"}},
    ]
    edges = []
    current = "input_1"
    x_pos = 250
    for index, (source_color, target_color) in enumerate(mapping.items(), start=1):
        match_id = f"const_match_{source_color}_{index}"
        value_id = f"const_value_{target_color}_{index}"
        equal_id = f"equal_{index}"
        where_id = f"where_{index}"
        nodes.extend(
            [
                {"id": match_id, "type": "op", "position": {"x": x_pos, "y": 40}, "data": {"label": match_id, "opType": "Constant", "shape": "1,1,30,30", "value": str(source_color)}},
                {"id": value_id, "type": "op", "position": {"x": x_pos, "y": 170}, "data": {"label": value_id, "opType": "Constant", "shape": "1,1,30,30", "value": str(target_color)}},
                {"id": equal_id, "type": "op", "position": {"x": x_pos + 180, "y": 70}, "data": {"label": equal_id, "opType": "Equal", "shape": "1,1,30,30"}},
                {"id": where_id, "type": "op", "position": {"x": x_pos + 360, "y": 95}, "data": {"label": where_id, "opType": "Where", "shape": "1,1,30,30"}},
            ]
        )
        edges.extend(
            [
                {"id": f"eq{index}a", "source": "input_1", "target": equal_id, "targetHandle": "a"},
                {"id": f"eq{index}b", "source": match_id, "target": equal_id, "targetHandle": "b"},
                {"id": f"wh{index}c", "source": equal_id, "target": where_id, "targetHandle": "condition"},
                {"id": f"wh{index}t", "source": value_id, "target": where_id, "targetHandle": "true"},
                {"id": f"wh{index}f", "source": current, "target": where_id, "targetHandle": "false"},
            ]
        )
        current = where_id
        x_pos += 220
    nodes.append({"id": "output_1", "type": "op", "position": {"x": x_pos + 200, "y": 95}, "data": {"label": "output_1", "opType": "Output", "shape": "1,1,30,30"}})
    edges.append({"id": "out", "source": current, "target": "output_1", "targetHandle": "input"})
    return {"projectName": f"agent-{task_id}", "taskId": task_id, "nodes": nodes, "edges": edges}


def post_export(host: str, payload: dict[str, Any]) -> tuple[int, str]:
    url = host.rstrip("/") + "/api/export"
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a NeuroGolf graph through the live backend export gate.")
    parser.add_argument("--host", default="http://127.0.0.1:8081", help="NeuroGolf Lab backend URL")
    parser.add_argument("--task", required=True, help="task id, for example task276")
    parser.add_argument("--graph", help="path to graph JSON payload or nodes/edges JSON")
    parser.add_argument("--color-remap", help='quick graph builder mapping JSON, for example \'{"6":2}\'')
    args = parser.parse_args()

    task_id = args.task.lower()
    if args.color_remap:
        payload = color_remap_graph(task_id, json.loads(args.color_remap))
    elif args.graph:
        payload = json.loads(Path(args.graph).read_text())
        payload.setdefault("taskId", task_id)
        payload.setdefault("projectName", f"agent-{task_id}")
    else:
        raise SystemExit("provide --graph or --color-remap")

    payload["trainingPairs"] = payload.get("trainingPairs") or load_task(task_id).get("train", [])
    status, body = post_export(args.host, payload)
    print(status)
    print(body)
    if status >= 400:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
