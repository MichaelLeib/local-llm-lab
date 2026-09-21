#!/usr/bin/env python3
"""Generate a deterministic ~6K-token Laguna prompt before an isolated run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tokenizers import Tokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--target-tokens", type=int, default=6144)
args = ap.parse_args()

model = Path(args.model)
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
# Do not use AutoTokenizer here: current Transformers validates Laguna's nested
# rope_parameters before TurboQuant's compatibility shim is installed. The
# checkpoint has a standard serialized tokenizer.json, and this direct loader
# gives the exact BPE count without importing the model config.
tok = Tokenizer.from_file(str(model / "tokenizer.json"))

header = (
    "You are a precise coding assistant. Read the deterministic engineering log below. "
    "At the end, summarize the invariants in three bullets.\n\n"
)
unit = (
    "[record {i:04d}] Component atlas-{i:04d} accepts records in strict order. "
    "Invariant A: validate input before mutation. Invariant B: preserve byte offsets. "
    "Invariant C: on failure return the original state unchanged. "
    "The test fixture value is MAPLE-{i:04d}-ORBIT and its checksum label is stable.\n"
)
text = header
n = 0
while True:
    candidate = text + unit.format(i=n)
    # Exact no-thinking rendering for this checkpoint's checked-in template.
    rendered = (
        "〈|EOS|〉<system>You are a helpful, conversationally-fluent assistant made by Poolside. "
        "You are here to be helpful to users through natural language conversations.</system>\n"
        f"<user>{candidate}</user>\n<assistant></think>"
    )
    count = len(tok.encode(rendered).ids)
    if count >= args.target_tokens:
        text = candidate
        break
    text = candidate
    n += 1

out.write_text(text, encoding="utf-8")
meta = {
    "target_tokens": args.target_tokens,
    "actual_rendered_tokens": count,
    "record_units": n + 1,
    "rendered_chars": len(rendered),
    "user_prompt_chars": len(text),
    "tokenizer_class": tok.__class__.__name__,
}
out.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
print(json.dumps(meta, indent=2))
