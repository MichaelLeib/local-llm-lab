# EXP-006 comparison record

Do not fill measured fields until the corresponding approved run completes.

| Metric | EXP-005 Qwen3.6 + Slipstream | EXP-006 Qwen3.8-Flash-Next + TinyTitan |
|---|---:|---:|
| Total model capacity | 35B | 125B main + 51B n-gram table |
| Active params/token | A3B | A6B |
| Storage footprint | ~19.55 GB | ~174.23 GB installed estimate |
| Runtime resident footprint | measured per run | pending |
| Swap delta | 0 MiB clean probe/sweep; 84.38 MiB Hermes | pending |
| 273-token prefill | 9.74 s | pending |
| ~500-token prefill | 11.40 s at 546 tokens | pending |
| ~1K-token prefill | 15.14 s at 1,105 tokens | pending |
| ~2K-token prefill | 37.99 s at 2,210 tokens | pending |
| ~5K cold Hermes prefill | 107.87 s / 5,003 tokens | pending |
| Cached Hermes TTFT | 4.50 s | pending |
| Decode tok/s | 8.417 → 5.903 across sweep | pending |
| Sustained decode | pending in EXP-005 | pending |
| Terminal tool call | passed | pending |
| Subjective usability | pending formal rating | pending |

Raw EXP-005 evidence remains under `results/raw/EXP-005/`.
