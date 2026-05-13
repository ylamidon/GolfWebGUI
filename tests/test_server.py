import unittest

from server import ExportPayload, ValidationError, compile_graph, validate_model


def identity_payload(output_grid=None):
    source = [[0, 1], [2, 3]]
    return ExportPayload(
        projectName="test",
        taskId="task001",
        nodes=[
            {"id": "input_1", "type": "op", "data": {"opType": "Input", "shape": "1,1,30,30"}},
            {"id": "identity_1", "type": "op", "data": {"opType": "Identity", "shape": "1,1,30,30"}},
            {"id": "output_1", "type": "op", "data": {"opType": "Output", "shape": "1,1,30,30"}},
        ],
        edges=[
            {"source": "input_1", "target": "identity_1"},
            {"source": "identity_1", "target": "output_1"},
        ],
        trainingPairs=[{"input": source, "output": output_grid or source}],
    )


def color_remap_payload():
    source = [[6, 6, 7, 6], [6, 6, 7, 7], [7, 7, 6, 7]]
    target = [[2, 2, 7, 2], [2, 2, 7, 7], [7, 7, 2, 7]]
    return ExportPayload(
        projectName="color-remap",
        taskId="task276",
        nodes=[
            {"id": "input_1", "type": "op", "data": {"opType": "Input", "shape": "1,1,30,30"}},
            {"id": "const_6", "type": "op", "data": {"opType": "Constant", "shape": "1,1,30,30", "value": "6"}},
            {"id": "const_2", "type": "op", "data": {"opType": "Constant", "shape": "1,1,30,30", "value": "2"}},
            {"id": "equal_1", "type": "op", "data": {"opType": "Equal", "shape": "1,1,30,30"}},
            {"id": "where_1", "type": "op", "data": {"opType": "Where", "shape": "1,1,30,30"}},
            {"id": "output_1", "type": "op", "data": {"opType": "Output", "shape": "1,1,30,30"}},
        ],
        edges=[
            {"source": "input_1", "target": "equal_1", "targetHandle": "a"},
            {"source": "const_6", "target": "equal_1", "targetHandle": "b"},
            {"source": "equal_1", "target": "where_1", "targetHandle": "condition"},
            {"source": "const_2", "target": "where_1", "targetHandle": "true"},
            {"source": "input_1", "target": "where_1", "targetHandle": "false"},
            {"source": "where_1", "target": "output_1", "targetHandle": "input"},
        ],
        trainingPairs=[{"input": source, "output": target}],
    )


class ServerCompilerTests(unittest.TestCase):
    def test_compile_and_validate_identity_graph(self):
        payload = identity_payload()
        model = compile_graph(payload)
        result = validate_model(model, payload)
        self.assertEqual(result["train"], "passed")
        self.assertEqual(result["shape"], "passed")
        self.assertEqual(result["colors"], "passed")

    def test_rejects_banned_ops(self):
        payload = ExportPayload(
            projectName="bad",
            taskId="task001",
            nodes=[
                {"id": "input_1", "type": "op", "data": {"opType": "Input", "shape": "1,1,30,30"}},
                {"id": "loop_1", "type": "op", "data": {"opType": "Loop", "shape": "1,1,30,30"}},
                {"id": "output_1", "type": "op", "data": {"opType": "Output", "shape": "1,1,30,30"}},
            ],
            edges=[
                {"source": "input_1", "target": "loop_1"},
                {"source": "loop_1", "target": "output_1"},
            ],
            trainingPairs=[{"input": [[0]], "output": [[0]]}],
        )
        with self.assertRaisesRegex(ValueError, "Banned ONNX operation"):
            compile_graph(payload)

    def test_rejects_malformed_graph_edges(self):
        payload = identity_payload()
        payload.edges = [{"source": "missing", "target": "identity_1"}]
        with self.assertRaisesRegex(ValueError, "edge source"):
            compile_graph(payload)

    def test_validation_failure_reports_mismatch(self):
        payload = identity_payload(output_grid=[[9, 9], [9, 9]])
        model = compile_graph(payload)
        with self.assertRaisesRegex(ValidationError, "Strict Equivalence failed"):
            validate_model(model, payload)

    def test_named_input_slots_compile_color_remap(self):
        payload = color_remap_payload()
        model = compile_graph(payload)
        result = validate_model(model, payload)
        self.assertEqual(result["train"], "passed")

    def test_rejects_duplicate_named_input_slot(self):
        payload = color_remap_payload()
        payload.edges[1]["targetHandle"] = "a"
        with self.assertRaisesRegex(ValueError, "multiple edges for input slot 'a'"):
            compile_graph(payload)


if __name__ == "__main__":
    unittest.main()
