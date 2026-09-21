# Sanitization

Before publication, the following categories of personal/private data were
removed or excluded from this repository. General system information
(hardware model, memory, OS version, GPU/ANE utilization, port numbers) is
retained — it is required to interpret the measurements.

## Rewritten in place

| Pattern | Replacement | Occurrences |
|---|---|---|
| `/Users/<user>/...` (recorded process command lines, ps dumps) | `/Users/<user>/...` | 17,675 |
| Tailnet address `100.x.x.x.51` (Tailscale 100.x CGNAT range) | `100.x.x.x.51` | 34 |

## Excluded entirely (never committed)

- **Private workspace snapshots** — `results/raw/EXP-022-*/backups/`,
  `results/raw/EXP-023-*/backups/`,
  `results/raw/EXP-007/real-repo-ab/backups/`: these contained live session
  secrets (`secret:`, `password_hash:`, `username:`) and private project
  source (a git bundle with all refs, untracked source tarballs, frontend
  code). They are workspace captures, not experiment evidence.
- **Private code diffs** — `results/raw/EXP-007/real-repo-ab/oracles/`
  (known-good patches against a private repository) and `worktrees/`
  (checked-out working copies of that repository).
- **Model weights and derived artifacts** — `models/`, `*.gguf`,
  `*.safetensors`, tokenizer/model blobs, packed expert weights.
- **Vendored third-party source** — cloned upstream repositories captured
  during experiments (`source/` subtrees in EXP-003/004/005/015/016/017/019/020/021),
  `node_modules/`, Python virtual environments (`.venv*`, `site-packages/`),
  prebuilt binaries.
- **Raw oversized logs with curated siblings** — e.g. EXP-016
  `first-probe/stdout-stderr.log` (1.06 GB) is represented by the curated
  `first-probe-clean/` pack instead.

## Reviewed and kept

- Email addresses: only a third-party contact from a model card
  (`labs@cohere.com`).
- Matrix identifiers: generic placeholder homes (`@you:localhost`).
- Hostnames: generic device names ("Mac").
- API keys/tokens: none present; literal `sk-optiq-*` placeholders are test
  fixtures, not real credentials.