"""Deterministic tests for the EXP-007 bounded-observation hook.

These tests exercise the hook directly: no model server or candidate is started.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path("/Users/<user>/HermesProjects/Local-LLM-Lab")
PLUGIN = Path.home() / ".hermes/profiles/exp007bench/plugins/exp007-context-safe/__init__.py"
TOKENIZER = ROOT / "results/raw/EXP-007/stock-hybrid-control/qwen36-stock-hybrid-control.gturbo/tokenizer/tokenizer.json"


def load_plugin():
    spec = importlib.util.spec_from_file_location("exp007_context_safe", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def token_count(module, value):
    return len(module._tokenizer(str(TOKENIZER)).encode(value).ids)


class ContextSafeOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.metrics = Path(self.temp.name) / "metrics.jsonl"
        self.previous = os.environ.get("EXP007_CONTEXT_SAFE_METRICS_PATH")
        os.environ["EXP007_CONTEXT_SAFE_METRICS_PATH"] = str(self.metrics)
        self.module = load_plugin()

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("EXP007_CONTEXT_SAFE_METRICS_PATH", None)
        else:
            os.environ["EXP007_CONTEXT_SAFE_METRICS_PATH"] = self.previous
        self.temp.cleanup()

    def read_metric(self):
        return json.loads(self.metrics.read_text().strip())

    def test_file_read_is_bounded_and_paginates(self):
        source = "\n".join(f"{n}|line-{n} " + "x" * 80 for n in range(240, 740))
        raw = json.dumps({"content": source, "total_lines": 1842, "file_size": len(source)})

        transformed = self.module.transform_tool_result("read_file", {"path": "src/large.ts", "offset": 240, "limit": 500}, raw)
        payload = json.loads(transformed)

        self.assertIn("[EXP-007 bounded observation:", payload["content"])
        self.assertIn("Request offset=", payload["content"])
        self.assertTrue(payload["exp007_context_safe"]["truncated"])
        self.assertLessEqual(token_count(self.module, transformed), self.module.MAX_RESULT_TOKENS)
        record = self.read_metric()
        self.assertEqual(record["tool_name"], "read_file")
        self.assertLessEqual(record["serialized_tokens"], self.module.MAX_RESULT_TOKENS)

    def test_search_caps_match_records_and_reports_omission(self):
        matches = [{"path": f"src/f{n}.ts", "line": n, "content": "needle"} for n in range(80)]
        raw = json.dumps({"total_count": 80, "matches": matches, "matches_format": "json"})

        transformed = self.module.transform_tool_result("search_files", {"pattern": "needle"}, raw)
        payload = json.loads(transformed)

        self.assertEqual(len(payload["matches"]), self.module.MAX_SEARCH_MATCHES)
        self.assertEqual(payload["exp007_context_safe"]["omitted_matches"], 80 - self.module.MAX_SEARCH_MATCHES)
        self.assertLessEqual(token_count(self.module, transformed), self.module.MAX_RESULT_TOKENS)

    def test_search_files_list_is_capped_like_matches(self):
        files = [{"path": f"src/f{n}.ts", "size": n} for n in range(80)]
        raw = json.dumps({"total_count": 80, "files": files, "warning": "broad search"})

        transformed = self.module.transform_tool_result("search_files", {"pattern": "needle"}, raw)
        payload = json.loads(transformed)

        self.assertLessEqual(len(payload["files"]), self.module.MAX_SEARCH_MATCHES)
        self.assertGreater(payload["exp007_context_safe"]["omitted_matches"], 0)
        self.assertLessEqual(token_count(self.module, transformed), self.module.MAX_RESULT_TOKENS)

    def test_terminal_preserves_head_tail_exit_and_explicit_omission(self):
        output = "FIRST_RELEVANT\n" + ("middle diagnostic\n" * 4000) + "LAST_RELEVANT"
        raw = json.dumps({"output": output, "exit_code": 7, "error": None})

        transformed = self.module.transform_tool_result("terminal", {"command": "synthetic"}, raw)
        payload = json.loads(transformed)

        self.assertIn("FIRST_RELEVANT", payload["output"])
        self.assertIn("LAST_RELEVANT", payload["output"])
        self.assertIn("[EXP-007 bounded observation:", payload["output"])
        self.assertEqual(payload["exit_code"], 7)
        self.assertLessEqual(token_count(self.module, transformed), self.module.MAX_RESULT_TOKENS)

    def test_small_result_is_unchanged_but_instrumented(self):
        raw = json.dumps({"output": "ok", "exit_code": 0, "error": None})

        transformed = self.module.transform_tool_result("terminal", {"command": "true"}, raw)

        self.assertEqual(transformed, raw)
        record = self.read_metric()
        self.assertFalse(record["truncated"])
        self.assertEqual(record["original_tokens"], record["serialized_tokens"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
