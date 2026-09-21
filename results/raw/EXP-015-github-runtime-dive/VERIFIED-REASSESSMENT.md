# EXP-015 — verifizierte Neubewertung: SSD-Expert-Streaming für Nemotron 3 Nano auf einem M3 mit 16 GB

**Status:** Architektur- und Quellcodeprüfung abgeschlossen; **keine lokale Inferenz, kein Modelldownload und kein Lane-Wechsel** durchgeführt.

## Entscheidung

Der belastbarste Ausgangspunkt ist **nicht** ein hypothetischer Verbund aus mehreren unabhängigen Projekten. Für eine Apple-Silicon-Implementierung ist **[jundot/omlx](https://github.com/jundot/omlx)** der einzige bislang verifizierte Codepfad, der alle zentralen Schichten in einem zusammenhängenden MLX-Stack enthält:

1. Nemotron-H-Modellpatch,
2. dateibasierter, mehrteiliger Safetensors-Expertenzugriff,
3. begrenzter Resident-Expert-Cache über `resident_fraction`,
4. asynchroner I/O-Pfad sowie Cache-Metriken,
5. Tests für partielle Residency, Mehr-Shard-Checkpoints und numerische Gleichheit.

**Nicht übernehmen:** CUDA-/PyTorch-orientierte Offload-Engines als Runtime-Basis. Sie sind nützliche Designreferenzen, lösen jedoch nicht die Metal/MLX-Ausführung auf diesem Mac.

## Lokale, reproduzierbare Quellcodeprüfung

Geprüfter Checkout:

- Repository: `https://github.com/jundot/omlx.git`
- Commit: `95d5bf0b613098726de5f992d8085a311d9da39b`
- Lizenz: Apache-2.0

Der ausgeführte statische Audit hat **alle** folgenden Prüfungen bestanden:

| Prüfung | Ergebnis | Lokale Evidenz |
|---|---:|---|
| Safetensors-basierter Expertenspeicher | bestanden | `omlx/patches/moe_expert_offload.py` enthält `CheckpointExpertStore` |
| Begrenzung der Expert-Residency | bestanden | API enthält `resident_fraction` |
| Asynchroner I/O-Mechanismus | bestanden | I/O-Pool ist im Offload-Patch vorhanden |
| Metriken für Offload-Verhalten | bestanden | `moe_offload_stats` vorhanden |
| Mehr-Shard-Checkpoint-Test | bestanden | `test_multi_shard` vorhanden |
| Numerischer Test bei partieller Residency | bestanden | `test_decode_bit_exact_at_partial_residency` vorhanden |
| Nemotron-H-Patch | bestanden | `omlx/patches/mlx_lm_mtp/nemotron_h_model.py` syntaktisch valide und Nemotron-H-spezifisch |
| Syntax aller vier Kernquellen | bestanden | Python-AST-Parse erfolgreich |

Die vollständige MLX-Testausführung war bewusst **nicht** möglich: Im kontrollierenden Python-Environment sind `mlx`, `mlx-lm` und `pytest` nicht installiert. Eine Installation oder ein Lauf würde den abgesicherten lokalen Modell-Lane berühren und benötigt eine explizite Freigabe.

## Externe Gegenprüfung

| Projekt | Relevanz | Urteil für den M3/16-GB-Pfad |
|---|---|---|
| [omlx](https://github.com/jundot/omlx) | Apple-Silicon/MLX, SSD-Caching, OpenAI-kompatibler Server; Apache-2.0 | **Primärer Kandidat.** Konkreter, statisch geprüfter Nemotron-H- plus Expert-Offload-Code. |
| [llama.cpp, PR #18058](https://github.com/ggml-org/llama.cpp/pull/18058) | Nemotron 3 Nano wurde upstream hinzugefügt und gemergt | **Sekundärer Kontrollpfad.** Sehr wertvoll für Konvertierung/Architekturvalidierung; nicht der geprüfte MLX-Expert-Streaming-Pfad. |
| [MoE-Infinity](https://github.com/EfficientMoE/MoE-Infinity) | CPU/GPU-Expertenoffload und Cache-Strategien; Apache-2.0 | **Designreferenz**, nicht portierbare Runtime-Basis (PyTorch/CUDA-Ausrichtung). |
| [ktransformers](https://github.com/kvcache-ai/ktransformers) | Heterogene MoE-Ausführung; Apache-2.0 | **Designreferenz**, nicht der direkte Metal/MLX-Weg. |
| [mlx-lm, Issue #980](https://github.com/ml-explore/mlx-lm/issues/980) | Beschreibt Prefix-Cache-Risiken bei Hybrid-/SSM-Architekturen | **Risikogate:** Mehrturn-/Prefix-Cache bei Hybridmodellen darf nicht als funktionierend angenommen werden. |

## Wichtigste Korrektur gegenüber der Vorhypothese

Die bisherigen Namen „TurboQuant-MLX“, „Mference“ und „Metal-SSD-llm“ dürfen **nicht** als bereits integrierte, validierte Produktionspipeline dargestellt werden. Für den angefragten Mac ist derzeit nur der oMLX-Pfad mit tatsächlich überprüfbaren Implementierungsartefakten ausreichend belegt. Die anderen Projekte können erst nach einem eigenen Source-Audit und einer klaren Metal-Kompatibilitätsprüfung in Betracht kommen.

## Technisches Risiko für 64–128K Kontext

Nemotron 3 Nano ist ein Hybridmodell. Daher gilt unabhängig vom Expert-Streaming:

- Expert-Offload reduziert das Gewichtsresident-Problem, nicht automatisch alle Kontextzustände.
- 64K bzw. 128K ist erst gewonnen, wenn **Laden**, **Prefill**, **Decode**, **Cache-Korrektheit**, **Memory Pressure** und **Swap** in einem echten Lauf gemessen wurden.
- Der bekannte MLX-Cache-Risikobereich für Hybrid-/SSM-Modelle macht Prefix-Reuse zu einem eigenen Akzeptanzkriterium, nicht zu einer Annahme.

## Nächstes kleinstes sinnvolles Experiment — nur nach Freigabe

Eine **isolierte 8K-Validierung** des oMLX-Pfads, noch nicht 64K:

1. separierte Umgebung exakt mit dem OMLX-Pin (`mlx==0.32.2` und dem im Checkout referenzierten `mlx-lm`-Commit), ohne die aktuelle Hermes-Lane zu ersetzen;
2. Modellformat und Nemotron-H-Patch laden;
3. zunächst `resident_fraction` in einem konservativen Raster messen;
4. für jeden Punkt protokollieren: RSS, macOS Memory Pressure, Swap-Differenz, Prefill-Tokens/s, Decode-Tokens/s, Expert-Hits/Misses und Ausgabe-Gleichheit;
5. nur bei einem sauberen 8K-Lauf auf 32K, dann 64K erweitern; 128K ausschließlich bei klarer RAM-/Swap-Reserve.

Dies erfordert eine explizite Zustimmung, weil dabei lokale Inferenz gestartet und der einzige erlaubte resident Model-Lane berührt würde.
