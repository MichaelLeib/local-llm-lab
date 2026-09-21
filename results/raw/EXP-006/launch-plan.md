# EXP-006 launch plan

1. Build TinyTitan release binaries in the isolated checkout.
2. Verify arm64 products and record build/toolchain output.
3. Run non-model help/version paths only.
4. Install only the pinned main Qwen3.8-Flash-Next 4-bit native model into the EXP-006 model directory on the internal Macintosh HD.
5. Monitor APFS reclaimable space, memory pressure, swap, and process state during installation.
6. Perform a conservative standalone probe before any Hermes/server work.
7. Keep EXP-005 and the default Hermes profile unchanged.
