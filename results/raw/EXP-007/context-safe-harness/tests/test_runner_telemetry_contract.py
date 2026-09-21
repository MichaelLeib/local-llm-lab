"""Static contract for the EXP-007 scored-run telemetry wiring."""
import unittest
from pathlib import Path

RUNNER = Path("/Users/<user>/HermesProjects/Local-LLM-Lab/tools/exp007_run_blind_hermes_task.sh")


class RunnerTelemetryContractTests(unittest.TestCase):
    def test_scored_chat_exports_metrics_path_and_writes_summary(self):
        source = RUNNER.read_text()
        self.assertIn('EXP007_CONTEXT_SAFE_METRICS_PATH="$RUN/context-safe-tool-results.jsonl"', source)
        self.assertIn('exp007_summarize_context_metrics.py', source)
        self.assertIn('--context-limit 16384 --completion-allowance 4096', source)
        self.assertIn('has_hook("transform_tool_result")', source)
        self.assertIn('context-safe hook is not loaded', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
