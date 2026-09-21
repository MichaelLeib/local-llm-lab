# EXP-006 inference gate

## User approval required

**Do not launch TinyTitanCLI, TinyTitanServer, or any model-using benchmark until the user explicitly authorizes inference.**

The prepared scripts enforce this with:

```text
EXP006_ALLOW_INFERENCE=I_APPROVE_EXP006_INFERENCE
```

The installer/repacker is allowed to finish because it is model acquisition and verification, not inference. No server, CLI generation, Hermes request, or model-using test may start before approval.

## Safe preparation already allowed

- Build and inspect binaries
- Verify arm64 products
- Verify the completed model receipt
- Check disk, swap, memory pressure, and competing processes
- Create raw output directories and run manifests
- Prepare commands and scripts
- Create an isolated Hermes profile without starting a server

## First approved action

After approval, run the no-generation preflight, then the deterministic short standalone probe:

```bash
EXP006_ALLOW_INFERENCE=I_APPROVE_EXP006_INFERENCE \
  results/raw/EXP-006/run-probe-gated.sh
```

The script must refuse to run unless the model directory contains both `manifest.json` and `verified-install.json`, no competing local model process is present, and the approval marker is exact.
