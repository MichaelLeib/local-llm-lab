# EXP-016 North candidate dossier

Candidate: CohereLabs/North-Mini-Code-1.0
Pinned source revision: d11e61a842617a22dc328552fa5bb86231ee4f37
Architecture: Cohere2MoeForCausalLM / cohere2_moe; 30B total / approximately 3B active; 49 layers; hidden size 2048; 32 attention heads / 4 KV heads; 128 experts; top-8; sliding window 4096 with full-attention layers; source max position 500000 (model card advertises 256K context).

4-bit discovery gate: unsloth/North-Mini-Code-1.0-GGUF pinned revision e306bb4bf0df610f5471d97a01de2b6e0b24d356 exposes MXFP4_MOE at 18,662,121,568 bytes and UD-Q4_K_M at 19,203,186,784 bytes. These exceed the measured practical 16 GiB envelope (ERNIE MLX 11.4 GB projected 17.2 GB working set; Instella 10.47 GB Q4 produced severe pressure and swap), so a 4-bit North acquisition is not justified for a feasibility launch.

Fallback representation: unsloth/North-Mini-Code-1.0-GGUF, pinned revision e306bb4bf0df610f5471d97a01de2b6e0b24d356, North-Mini-Code-1.0-UD-Q3_K_M.gguf, remote size 14,213,013,600 bytes. This is the strongest available 3-bit fallback after the 4-bit practical-memory gate. The upstream README states that cohere2moe requires llama.cpp PR #24260 until merged; the isolated ExpertCache source pinned at 7e1e28cae36d41fe7bbe9dae7c9625de6565c063 already contains cohere2moe graph/parser support and will be built/used only in this experiment tree.

Runtime plan: conservative GGUF standalone probe with ctx 512, physical ubatch 1, CPU MoE if needed, loopback-only. Stop on severe memory pressure or Metal OOM. No coding/research-quality tests; API/tool smoke only if a stable, practically usable runtime arm survives.
