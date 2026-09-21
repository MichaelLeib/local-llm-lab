# Publishing policy — what goes into the public repo

This repository is **public** (github.com/MichaelLeib/local-llm-lab). Any
agent — any model size — may contribute results, but every contribution must
pass `./publish.sh` before it reaches GitHub. **Never `git push` directly.**

## Allowed (general system information)

Hardware model, chip, memory size, OS version, GPU/ANE utilization, memory
pressure, swap, port numbers, timings, tok/s, quantization names, model IDs,
tool output, benchmark JSON/logs. All of this is fine and needed.

## Never commit

| Item | Reason |
|---|---|
| `backups/` directories | workspace snapshots with **live session secrets** (`secret:`, `password_hash:`, `username:`) and private project code |
| `worktrees/`, `oracles/known-good.patch`, `*.bundle`, `MyChattyKit*` | private HermesMobile/myChatty repository code |
| `*.gguf`, `*.safetensors`, `*.bin` weights, `packed_experts/`, tokenizer blobs >1MB | model binaries don't belong in git |
| `source/`, `node_modules/`, `site-packages/`, `.venv*/`, vendored clones | third-party material, not our results |
| raw logs >50MB when a curated sibling exists | keep repo small (EXP-016 pattern) |

These are also `.gitignore`d — `git add -A` cannot pick them up.

## Personal data — scrubbed mechanically by `publish.sh`

If any tracked file contains these, the script rewrites them automatically:

| Pattern | Replacement | Why |
|---|---|---|
| `/Users/michaelleib` | `/Users/<user>` | macOS username in recorded paths / command dumps |
| `100.85.108.51` | `100.x.x.x.51` | Tailnet (Tailscale CGNAT) address |
| `michaelleib` (bare) | `<user>` | ps user columns, `ls -l` owner fields |

So: **yes, always** — a `michaelleib` path in a result file is fine to save
locally; `publish.sh` rewrites it before commit. Never hand-write real
usernames or Tailnet IPs into new *summary* docs; use the placeholders there.

## Other things to avoid writing into results (not auto-scrubbed!)

These have no known safe placeholder, so agents must simply not record them:

- real email addresses (use `user@localhost` in examples)
- API keys / tokens of any format (`hf_…`, `ghp_…`, `sk-…`, Bearer tokens)
- serial numbers, hardware UUIDs, MAC addresses
- other people's names or usernames
- password/session hashes from any config snapshot

## Workflow for contributing results (any model)

```bash
cd ~/HermesProjects/Local-LLM-Lab
# ... run experiment, write results into results/raw/EXP-XXX-*/
./publish.sh "EXP-024: <short description>"
```

The script fails closed: if residue remains after scrubbing, nothing is
committed or pushed. Commit identity is forced to the noreply address
(`73171570+MichaelLeib@users.noreply.github.com`) regardless of machine
git config — never override it.