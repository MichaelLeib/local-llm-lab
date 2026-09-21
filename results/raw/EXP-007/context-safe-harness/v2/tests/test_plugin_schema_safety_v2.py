"""Schema-safety contract: EXP-007 observation hook registers no model tool."""
import importlib.util
import unittest
from pathlib import Path

PLUGIN = Path.home() / ".hermes/profiles/exp007benchv2/plugins/exp007-context-safe-v2/__init__.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("exp007_context_safe_schema", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookOnlyRegistrationTests(unittest.TestCase):
    def test_plugin_registers_only_transform_hook(self):
        module = load_plugin()
        calls = []

        class Context:
            def register_hook(self, name, fn):
                calls.append(("hook", name, fn))
            def register_tool(self, *args, **kwargs):
                calls.append(("tool", args, kwargs))

        module.register(Context())
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0:2], ("hook", "transform_tool_result"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
