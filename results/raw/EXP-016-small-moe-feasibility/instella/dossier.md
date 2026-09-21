# EXP-016 Instella-MoE candidate dossier

Candidate: amd/Instella-MoE-16B-A3B-Think
Pinned source revision: 74d28c1a8425583d7805b58e2caa9c13d6b62929
Source architecture: custom InstellaMoEForCausalLM; config model_type deepseek_v3; 27 layers; hidden size 2048; 16 attention heads; Gated MLA; FarSkip-Collective; 64 routed + 2 shared experts; top-6 routed; max position 32768; vocab 128896.

Primary representation: DevQuasar/amd.Instella-MoE-16B-A3B-Think-GGUF, pinned revision 987ee1648d7e4bcb33ab98dfbf4e910b2230c30a, Q4_K_M/amd.Instella-MoE-16B-A3B-Think.f16.gguf.Q4_K_M.gguf, remote size 10,470,249,600 bytes. This is the 4-bit-first arm required by the campaign. The publisher README explicitly requires the experimental llama.cpp instella-moe branch; stock support is not assumed.

Runtime/source plan: use the isolated llama.cpp ExpertCache source pinned at 7e1e28cae36d41fe7bbe9dae7c9625de6565c063 only after confirming whether it contains Instella support. If unsupported, preserve acquisition and classify the representation as unsupported rather than silently substituting a different architecture. rapid-mlx is not assumed compatible because the source checkpoint uses custom code and Gated MLA/FarSkip.

Escalation: consider the publisher's Q3_K_M artifact (8,219,053,696 bytes) only if the Q4 runtime arm is technically supported but fails the practical memory gate. Do not run coding or research-quality evaluations. Loopback-only, one resident model, no production Hermes changes.
