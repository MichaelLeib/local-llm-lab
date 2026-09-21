# EXP-020 — Prism Ternary Bonsai 2 PTQ1_0 vs frozen Ornith Q5

## Decision

**Do not promote Bonsai 2 PTQ1_0 as the primary local Hermes agent on this 16 GiB M3 MacBook Air.**

Bonsai 2 is correct and capable in the official Prism runtime, and it has a healthy direct 32K runtime envelope. But that is insufficient for the required end-to-end Hermes use case: Hermes enforces a 64K model admission floor. At the required 64K runtime context, FP16 KV leaves only 9% free memory when idle; Q8 KV makes it loadable but the first native Hermes terminal-tool attempt timed out, increased pageouts substantially, and did not complete its file operation. It therefore does not clear the runtime/safety gate needed before autonomous coding/research evaluation.

The frozen Ornith Q5 control remains the primary candidate.

## Exact candidate

- Model: `prism-ml/Ternary-Bonsai-2-27B-gguf`
- Artifact: `Ternary-Bonsai-2-27B-PTQ1_0.gguf`
- Size: `5,946,648,928` bytes
- SHA-256: `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`
- Runtime: official Prism llama.cpp Metal arm64 release, build `10709`, commit `9a9394a89`
- Server: loopback-only `127.0.0.1:8920`
- Correctness prerequisite: Prism runtime was required; stock llama.cpp was not accepted because Bonsai 2's rotated/Hadamard ternary representation can otherwise load while producing incorrect output.

## Direct-runtime results

All successful long-context arms used `-ngl 99 -np 1 -fa on -b 128 -ub 64` after the original `-b 1024 -ub 512` arm failed safely with a Metal `Insufficient Memory` error at about 1,074 prompt tokens.

| Arm | Result | Key evidence |
|---|---|---|
| 8K FP16 KV | completed | 7,537 populated tokens; 40.08 tok/s prefill; 7.07 tok/s decode; no swap growth |
| 16K FP16 KV | completed | 15,017 populated tokens; 39.62 tok/s prefill; 7.66 GiB RSS; no swap growth |
| 32K FP16 KV | completed | 29,977 populated tokens; 38.13 tok/s prefill; 4.75 tok/s decode; 8.41 GiB RSS; 0 MB swap growth; guard did not trip |
| 32K retrieval, 128 reasoning budget | completed | Returned exact buried code `CEDAR-4827`; 18,283 populated tokens; 40.41 tok/s prefill; 6.35 tok/s decode; no swap growth |
| 64K FP16 KV load-only | runtime safety failure | 10.21 GiB RSS and 9% free memory while idle; not advanced to populated work |
| 64K Q8 KV load-only | provisional load success | 8.37 GiB RSS and 23% free memory while idle |
| 64K Q8 KV native Hermes tool loop | runtime safety failure | Hermes terminal sequence did not create `output.txt`; outer invocation exceeded 420 s; pageouts rose from 30,994 before the Q8 load arm to 33,427 while active and 33,918 after cleanup; free memory fell to 14% while active |

The 64K Q8-KV native test was a genuine Hermes invocation through an isolated `local-bonsai` profile. Requested behavior was `read input.txt -> write reverse-ordered output.txt -> reread`. Its raw transcript is `raw/hermes-native-read-transform-write-q8kv64k.txt`; it shows an unsuccessful initial `cat input.txt`, a subsequent terminal action that took 52.8 seconds, then API interruption. `output.txt` was absent after cleanup. The test does not establish a model-only tool-selection failure, but it does establish that the required 64K Hermes runtime was not healthy enough for promotion.

## Comparison implication

Frozen Ornith Q5 remains the appropriate control/primary lane because it already has native sequential tool verification at configured 64K, practical populated context around 32K, and materially healthier known 64K Hermes-loop memory behavior (+248 MB swap in its heavy loop) than Bonsai's unsuccessful Q8-KV 64K native turn.

Bonsai's direct 32K result is promising as a research/runtime datapoint, but it cannot be called a Hermes-agent win without a stable 64K-admitted native tool session. No autonomy, coding, or research capability score is claimed.

## Safety and cleanup state

- Bonsai server stopped; no listener on 8901, 8902, 8919, or 8920 was present at final check.
- Post-stop free memory recovered to 76%.
- The stale Q6 process source was an old API EXP-019 session; Q6 remains temporarily mode `000` quarantined so it cannot relaunch while that stale agent loop is still issuing commands. Ornith Q5 was untouched.
- Isolated `local-bonsai` profile exists and is bound to the Bonsai loopback endpoint with a 64K declared context, but it is **not promoted** and must not be selected for ordinary work.

## Smallest useful next experiment

Only revisit Bonsai if a runtime change can make a 64K-admitted native Hermes read/write/reread turn complete with a healthy memory/pageout envelope. Do not spend coding/research autonomy budget before that gate passes.

## Final Q4-KV / 2,048-reasoning retest

User-requested final configuration: PTQ1_0, 64K admitted context, `q4_0` K/V cache, 2,048 reasoning budget, text-only (no projector), `-b 128 -ub 64`.

This configuration **did clear functional native-tool and coding checks**, unlike the earlier Q8-KV arm:

- Server loaded at 7.16 GiB RSS; first native task completed read → reverse/write → reread in 370 s, with exact verified output `gamma\nbeta\nalpha\n`.
- A separate native coding task completed in 617 s. It created `hermes-coding-final-q4/parse_records.py` plus a nine-test `unittest` suite. Independent verification from the artifact directory passed all 9 tests.

It still **does not change the promotion decision**. The latency is impractical (more than six minutes for a trivial three-line file transformation; more than ten minutes for the small coding task), and the arm's swap rose from 731.94 MiB before launch to 1,482.44 MiB after the coding task (approximately +750 MiB), with pageouts rising from 34,670 after load to 36,791. The server was stopped before a research turn could compound this pressure. This is a functional-but-unhealthy agent configuration, not a primary Hermes lane.
