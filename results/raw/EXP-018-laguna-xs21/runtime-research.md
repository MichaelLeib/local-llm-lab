# Runtime research notes

Primary test representation: `mlx-community/Laguna-XS-2.1-3bit`, uniform affine 3-bit weights with group size 64, 3.503 bpw effective and 14 GB reported disk size. The card specifies `LagunaForCausalLM`, 40 layers, 256 experts with top-8 routing, one dense first layer, hidden size 2048, 48/64 attention-head pattern, 8 KV heads, 128 head dimension, hybrid full/sliding attention (512 sliding window), partial RoPE, and 262144 context tokens. The config defaults to thinking enabled and names poolside_v1 tool/reasoning parsers.

Official Poolside documentation describes XS 2.1 as 33B total / 3B active MoE, 256K context, text-only, native interleaved reasoning and agent/chat modes, released under OpenMDW-1.1. Official GGUF Q4_K_M is 20.3 GB and requires a non-upstream Laguna llama.cpp PR, so it is not the first arm. MLX OptiQ-4bit is 20 GB / about 4.5 bpw and requires mlx-optiq because stock mlx-lm does not include the Laguna architecture; it remains an alternative only if 3-bit results justify it.

Prior evidence: EXP-010 tested a different, larger Laguna S 2.1 TurboQuant configuration (48 layers, 10 experts/token, 1M config context), not Laguna XS 2.1. Its populated 6,159-token request was safety-stopped at 13% free memory before generation. It is preserved and not treated as a direct XS result.
