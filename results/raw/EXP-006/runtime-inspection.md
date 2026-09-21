# EXP-006 runtime inspection

## Identity

- Historical name: NVMAI
- Current name: TinyTitan
- Repository: https://github.com/Pummelchen/TinyTitan
- NVMAI URL currently resolves to the same repository/content.
- Tested commit: `008510e2753cc16a674cb75169ba3133cf56fa4e`
- TinyTitan is a focused fork of Turbo Fieldfare/Slipstream lineage.

## Host compatibility observed

- macOS 27.0, build 26A428
- Mac15,13, Apple M3, 8 cores, 16 GiB unified memory
- Swift 6.4, arm64 target
- Command Line Tools selected at `/Library/Developer/CommandLineTools`
- No competing local model process was running during inspection

The repository's own guard requires macOS 26+ and Swift 6.4+, both satisfied.

## Flash-Next support

The current tree explicitly supports `qwen38flash` / Qwen3.8-Flash-Next 125B-A6B. The implementation declares:

- `qwen38flash` model family
- 48 layers
- 512 routed experts, top-10 routing
- Gated-DeltaNet plus sparse-indexed attention
- hyper-connection residual streams
- hashed n-gram/PLE embedding table
- separate optional native MTP draft-head install

The runtime model profile has a shipped 4-bit row with a 12 GiB expert-cache budget, no predictive prefetch, 4096-token prefill chunks, and wired expert cache. The profile comments report approximately 5.8 tok/s on the maintainer's 24 GB base 8-core M3 MacBook Pro for 4-bit Flash-Next, but that is an external claim and not an EXP-006 measurement.

## APIs and Hermes relevance

TinyTitan exposes loopback APIs for:

- OpenAI Chat Completions
- OpenAI Responses
- Anthropic Messages
- streaming
- client-authorized function tools
- prompt-state reuse / previous response handling

This is promising for Hermes, but actual Hermes compatibility remains an EXP-006 gate. The server is loopback-only and has no authentication; it must not be exposed beyond localhost.

## Model source and disk architecture

TinyTitan pins `RockTalk/Qwen3.8-Flash-Next-MLX-4bit` at revision `478474da92599ad0cf9f8bd447e658b29cb8480a`. The pinned repository contains a large separate `ngram_table.bin` plus model shards and tokenizer/config files. The runtime source declares:

- main approximate download: 173,825,909,304 bytes
- main installed footprint: 174,228,562,488 bytes
- reserve: 4 GiB
- optional MTP draft: approximately 1.47 GB download / 1.48 GB installed

The installer streams supported sources through the repacker and does not use the official 360 GB BF16 conversion path for the initial native install.

## Phase-2 decision

Proceed to a clean TinyTitan release build and then a supervised main 4-bit native install under `results/raw/EXP-006/model/`. Do not download the optional MTP draft or official BF16 checkpoint until the main install and runtime gate pass.
