# Harness configuration result — no inference started

**Classification:** `invalid_configuration` (prompt-construction path), not a model/runtime result.

The initial guarded server wrapper failed before starting `turboquant-serve`, because `transformers.AutoTokenizer.from_pretrained(..., trust_remote_code=True)` attempted to validate Laguna's nested `rope_parameters` through Transformers 5.17 before TurboQuant's Laguna compatibility shim was active. It raised `AttributeError: 'float' object has no attribute 'get'` during config validation.

No model process, request, prefill, decode, swap delta, or cache metric exists for this arm. The wrapper has been corrected to count the checkpoint's `tokenizer.json` directly through the Rust `tokenizers` binding and a checked-in no-thinking rendering of the model template. The corrected run will use a fresh arm directory.

Raw traceback: `prompt-build.log`.
