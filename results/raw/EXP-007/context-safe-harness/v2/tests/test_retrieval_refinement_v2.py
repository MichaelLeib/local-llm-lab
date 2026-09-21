import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-007/context-safe-harness/v2/exp007_retrieval_refinement.py')


def load_module():
    spec = importlib.util.spec_from_file_location('exp007_refinement', SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetrievalRefinementTests(unittest.TestCase):
    def test_classifies_explicit_file_followup_and_unrefined_search(self):
        m = load_module()
        result = m.derive([
            {'tool_name': 'read_file', 'args': {'path': 'a.ts', 'offset': 1}, 'truncated': True},
            {'tool_name': 'read_file', 'args': {'path': 'a.ts', 'offset': 80}, 'truncated': False},
            {'tool_name': 'search_files', 'args': {'pattern': 'needle'}, 'truncated': True},
            {'tool_name': 'search_files', 'args': {'pattern': 'needle'}, 'truncated': False},
        ])
        self.assertEqual(result['counts']['bounded_results'], 2)
        self.assertEqual(result['counts']['explicit_file_offset_followup'], 1)
        self.assertEqual(result['counts']['unrefined_repeat'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
