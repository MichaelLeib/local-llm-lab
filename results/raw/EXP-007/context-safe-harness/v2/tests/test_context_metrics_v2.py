"""Tests for deterministic EXP-007 context-efficiency aggregation."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path("/Users/<user>/HermesProjects/Local-LLM-Lab/tools/exp007_summarize_context_metrics.py")


def load_module():
    spec = importlib.util.spec_from_file_location("exp007_context_metrics", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextMetricsTests(unittest.TestCase):
    def test_aggregates_tool_cost_repeats_and_server_telemetry(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            (run / "context-safe-tool-results.jsonl").write_text("\n".join([
                json.dumps({"tool_name": "read_file", "args": {"path": "a.ts", "offset": 1, "limit": 20}, "original_tokens": 700, "serialized_tokens": 500, "truncated": True}),
                json.dumps({"tool_name": "read_file", "args": {"path": "a.ts", "offset": 1, "limit": 20}, "original_tokens": 650, "serialized_tokens": 500, "truncated": True}),
                json.dumps({"tool_name": "search_files", "args": {"path": "src", "pattern": "needle"}, "original_tokens": 50, "serialized_tokens": 50, "truncated": False}),
                json.dumps({"tool_name": "search_files", "args": {"path": "src", "pattern": "needle"}, "original_tokens": 40, "serialized_tokens": 40, "truncated": False}),
            ]) + "\n")
            (run / "server.log").write_text(
                "request prompt=5012 cached=0 new_prompt=5012 completion=100 ttft=1s\n"
                "request prompt=11000 cached=0 new_prompt=5988 completion=200 ttft=1s\n")
            result = module.summarize(run, context_limit=16384, completion_allowance=4096)

        self.assertEqual(result["initial_prompt_tokens"], 5012)
        self.assertEqual(result["maximum_accumulated_prompt_tokens"], 11000)
        self.assertEqual(result["tool_calls_made"], 4)
        self.assertEqual(result["cumulative_tool_result_tokens"], 1090)
        self.assertEqual(result["truncated_tool_outputs"], 2)
        self.assertEqual(result["repeated_file_ranges"], 1)
        self.assertEqual(result["repeated_unrefined_searches"], 1)
        self.assertEqual(result["completion_tokens"], 300)
        self.assertTrue(result["context_limit_approached"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
