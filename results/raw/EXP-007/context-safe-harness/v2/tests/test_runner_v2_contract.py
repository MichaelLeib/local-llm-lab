import unittest
from pathlib import Path

RUNNER = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-007/context-safe-harness/v2/exp007_run_blind_hermes_task_v2.sh')


class RunnerV2ContractTests(unittest.TestCase):
    def test_v2_runner_isolated_and_preserves_fixed_controls(self):
        source = RUNNER.read_text()
        self.assertIn('real-repo-ab-v2', source)
        self.assertIn('exp007benchv2', source)
        self.assertIn('context-safe-harness/v2/POLICY.md', source)
        self.assertIn('--max-context 16384', source)
        self.assertIn('--context-limit 16384 --completion-allowance 4096', source)
        self.assertIn('has_hook("transform_tool_result")', source)
        self.assertIn('context-safe-v2 hook is not loaded', source)
        self.assertIn('exp007_retrieval_refinement.py', source)
        self.assertIn('verify_v2_freeze.py', source)
        self.assertIn('v2 freeze receipt verification failed', source)
        self.assertNotIn('exp007_run_blind_hermes_task.sh"', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
