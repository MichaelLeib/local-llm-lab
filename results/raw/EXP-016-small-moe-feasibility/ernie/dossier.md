# EXP-016 ERNIE candidate dossier

Candidate: baidu/ERNIE-4.5-21B-A3B-Thinking
Pinned source revision: 4341bb42644d5422859509fa25d41544c57181f8
Architecture: ernie4_5_moe; 28 layers; hidden 2560; 20 Q heads / 4 KV heads; 64 routed + 2 shared experts; top-6 routed experts; source context 131072.

Primary representation choice: community MLX 4-bit, qurk41/ERNIE-4.5-21B-A3B-Thinking-mlx-4Bit, revision b59122f1fbe19df1fe939ad4de46763265fc297, 12,277,133,662 bytes of selected weights/metadata. This is attempted first because rapid-mlx contains a native ernie4_5_moe loader and the MLX artifact is smaller than the 13,331,018,624-byte Q4_K_M GGUF. It is not assumed compatible until local load/smoke proves it.

Fallback representation: unsloth/ERNIE-4.5-21B-A3B-Thinking-GGUF, revision b1fa62d9e5864da596c78a0fb5cc02e5ffba336c, ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf, 13,331,018,624 bytes. Pinned llama.cpp ExpertCache source revision 7e1e28cae36d41fe7bbe9dae7c9625de6565c063 contains ernie4_5-moe support. The fallback is only acquired if the MLX path fails a load/runtime gate.

Runtime gate: rapid-mlx 0.14.1 / MLX 0.32.1 / mlx-lm 0.31.3. Its disk-stream registry does not contain ernie4_5_moe, so no disk-stream claim will be made for the MLX arm. Existing isolated ExpertCache Metal build is preserved at EXP-004 revision and will be copied/rebuilt only if the GGUF fallback is needed.

Safety: loopback only; one local model resident; no production Hermes configuration changes. The first probe is a short deterministic standalone readiness/correctness request, followed by cold/warm prefill and decode only if the server reaches stable idle without severe pressure/swap. Context tests classify allocatable/completable/correct/practically usable and do not constitute coding or research-quality evaluations.
