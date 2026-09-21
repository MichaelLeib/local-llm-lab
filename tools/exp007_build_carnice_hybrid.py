#!/usr/bin/env python3
"""Build EXP-007 Carnice Hybrid without loading a language model.

The Carnice hybrid is an APFS clone of the validated Carnice Hybrid. Only all full-attention Q/K/V/O
resident records are replaced using remote official Qwen BF16 ranges quantized by
the pinned mlx-vlm-0.4.4 environment's MLX affine pipeline. Routed experts are
left byte-for-byte untouched. It is a control for Carnice's future sparse delta,
not a claim of historical bit identity.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import mlx.core as mx
import numpy as np

ROOT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab')
OUT = ROOT / 'results/raw/EXP-007'
PROV = OUT / 'quantizer-provenance'
CONTROL = OUT / 'carnice-hybrid/Carnice-Qwen3.6-MoE-35B-A3B.gturbo'
SOURCE = ROOT / 'results/raw/EXP-007/stock-hybrid-control/qwen36-stock-hybrid-control.gturbo'
BASE_REPO = 'samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B'
BASE_REV = 'd86a0cea3cd6794a294ad72a08598294249c761e'
BASE_INDEX_SHA256 = '41b9356101ebf8e7519e150dc811f80c4226e727301fbb032b890f006ed0be83'
FULL_LAYERS = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39)
PROJECTIONS = ('q_proj', 'k_proj', 'v_proj', 'o_proj')
UA = {'User-Agent': 'Local-LLM-Lab-EXP-007/1.0'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def url(path: str) -> str:
    return f'https://huggingface.co/{BASE_REPO}/resolve/{BASE_REV}/{path}'


def fetch(start: int, end: int, path: str, attempts: int = 3) -> tuple[bytes, dict]:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url(path), headers=UA | {'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = r.read()
                if getattr(r, 'status', None) != 206 or len(data) != end - start + 1:
                    raise RuntimeError(f'bad range response status={getattr(r,"status",None)} size={len(data)}')
                return data, {'status': r.status, 'attempt': attempt, 'content_range': r.headers.get('Content-Range'),
                              'final_url': r.geturl()}
        except Exception as exc:
            last = repr(exc)
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f'{path} {start}-{end} failed: {last}')


def header(path: str) -> dict:
    first, _ = fetch(0, 7, path)
    n = int.from_bytes(first, 'little')
    raw, _ = fetch(8, 7 + n, path)
    parsed = json.loads(raw)
    return {'header_bytes': n, 'header_sha256': digest(raw),
            'tensors': {k: {'dtype': v['dtype'], 'shape': v['shape'], 'offsets': v['data_offsets']}
                        for k, v in parsed.items() if k != '__metadata__'}}


def bf16_mx(payload: bytes, shape: list[int]) -> mx.array:
    if len(payload) != int(np.prod(shape)) * 2:
        raise ValueError('BF16 range size/shape mismatch')
    return mx.array(np.frombuffer(payload, dtype='<u2').copy().reshape(shape)).view(mx.bfloat16)


def output_bytes(values: tuple[mx.array, mx.array, mx.array], scratch: Path) -> dict[str, bytes]:
    mx.save_safetensors(str(scratch), {'weight': values[0], 'scales': values[1], 'biases': values[2]})
    raw = scratch.read_bytes()
    n = int.from_bytes(raw[:8], 'little')
    header_data = json.loads(raw[8:8+n])
    body = 8 + n
    return {name: raw[body + header_data[name]['data_offsets'][0]:body + header_data[name]['data_offsets'][1]]
            for name in ('weight', 'scales', 'biases')}


def resident_index(path: Path) -> dict[str, dict]:
    with path.open('rb') as f:
        header = f.read(24)
        index_size, resident_size, entries = struct.unpack('<QQQ', header)
        region = header + f.read(index_size - 24)
    found = {}
    for i in range(entries):
        p = 24 + i * 72
        name_offset, name_len, dtype = struct.unpack_from('<IHB', region, p)
        file_offset, size = struct.unpack_from('<QQ', region, p + 8)
        shape = struct.unpack_from('<IIII', region, p + 24)
        scale_offset, scale_size, bias_offset, bias_size = struct.unpack_from('<QQQQ', region, p + 40)
        name = region[name_offset:name_offset + name_len].decode('utf-8')
        found[name] = {'dtype': dtype, 'weight': (file_offset, size), 'scales': (scale_offset, scale_size),
                       'biases': (bias_offset, bias_size), 'shape': shape}
    if path.stat().st_size != index_size + resident_size:
        raise RuntimeError('resident index does not account for complete file')
    return found


def metadata(path: str) -> bytes:
    req = urllib.request.Request(url(path), headers=UA)
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def main() -> int:
    if not CONTROL.is_dir() or not SOURCE.is_dir():
        raise SystemExit('stock/control .gturbo directories are missing')
    generated_dir = OUT / 'carnice-hybrid/generated-resident'
    if generated_dir.exists() or (CONTROL / 'EXP007-CONTROL-PROVENANCE.json').exists():
        raise SystemExit('control build appears already started; refusing overwrite')
    generated_dir.mkdir(parents=True)
    index_data = metadata('model.safetensors.index.json')
    if digest(index_data) != BASE_INDEX_SHA256:
        raise RuntimeError('official base index hash differs from the sampled reproduction gate')
    weight_map = json.loads(index_data)['weight_map']
    targets = [f'model.language_model.layers.{layer}.self_attn.{projection}.weight'
               for layer in FULL_LAYERS for projection in PROJECTIONS]
    missing = [name for name in targets if name not in weight_map]
    if missing:
        raise RuntimeError(f'official index lacks required Q/K/V/O tensors: {missing}')
    shards = sorted({weight_map[name] for name in targets})
    headers = {shard: header(shard) for shard in shards}
    resident_path = CONTROL / 'model_weights.bin'
    entries = resident_index(resident_path)
    rows: list[dict] = []
    scratch = generated_dir / 'mlx-output.safetensors'
    for source_name in targets:
        shard = weight_map[source_name]
        tensor = headers[shard]['tensors'][source_name]
        if tensor['dtype'] != 'BF16':
            raise RuntimeError(f'{source_name} is not BF16')
        start, end = tensor['offsets']
        hs = headers[shard]['header_bytes']
        payload, transport = fetch(8 + hs + start, 8 + hs + end - 1, shard)
        generated = output_bytes(tuple(mx.quantize(bf16_mx(payload, tensor['shape']), group_size=64,
                                                    bits=4, mode='affine')), scratch)
        target_name = 'language_model.model.' + source_name[len('model.language_model.'):]
        if target_name not in entries:
            raise RuntimeError(f'control resident index has no {target_name}')
        entry = entries[target_name]
        components = []
        for component in ('weight', 'scales', 'biases'):
            data = generated[component]
            expected_offset, expected_size = entry[component]
            if len(data) != expected_size:
                raise RuntimeError(f'{target_name}.{component}: generated {len(data)} != slot {expected_size}')
            staged = generated_dir / (target_name.replace('.', '_') + f'.{component}.bin')
            staged.write_bytes(data)
            components.append({'component': component, 'file_offset': expected_offset, 'bytes': len(data),
                               'sha256': digest(data), 'staged_file': str(staged.relative_to(ROOT))})
        rows.append({'source_bf16_tensor': source_name, 'source_shard': shard, 'shape': tensor['shape'],
                     'bf16_bytes': len(payload), 'bf16_sha256': digest(payload), 'transport': transport,
                     'resident_tensor': target_name, 'components': components})
    # All source ranges and generated components are present before the clone is
    # mutated. This prevents a failed download from producing a partial control.
    with resident_path.open('r+b', buffering=0) as destination:
        for row in rows:
            for component in row['components']:
                payload = (ROOT / component['staged_file']).read_bytes()
                destination.seek(component['file_offset'])
                destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())
    # Re-hash the one changed resident file and emit a model-specific manifest.
    manifest_path = CONTROL / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    new_weight_hash = digest_file(resident_path)
    manifest['modelID'] = 'carnice-qwen3.6-moe-35b-a3b-exp007-hybrid-4bit'
    manifest['sourceSnapshotHash'] = 'sha256:' + digest(json.dumps({
        'base_repo': BASE_REPO, 'base_revision': BASE_REV, 'index_sha256': BASE_INDEX_SHA256,
        'quantizer': {'mlx_vlm': '0.4.4', 'mlx': '0.32.1', 'mlx_lm': '0.31.3',
                      'group_size': 64, 'bits': 4, 'mode': 'affine'}, 'rows': rows,
    }, sort_keys=True).encode())
    manifest['files']['model_weights.bin']['sha256'] = new_weight_hash
    manifest['files']['model_weights.bin']['size'] = resident_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    receipt = CONTROL / 'verified-install.json'
    if receipt.exists():
        receipt.unlink()  # copied receipt is path- and manifest-bound to EXP-005
    # Verify every reused expert file against the EXP-005 manifest. This is the
    # explicit artifact-level proof that the control did not alter expert bytes.
    original_manifest = json.loads((SOURCE / 'manifest.json').read_text())
    expert_checks = {}
    for rel, expected in original_manifest['files'].items():
        if rel.startswith('packed_experts/layer_'):
            actual = digest_file(CONTROL / rel)
            expert_checks[rel] = {'expected_sha256': expected['sha256'], 'actual_sha256': actual,
                                  'exact': actual == expected['sha256']}
    layout_path = CONTROL / 'packed_experts/layout.json'
    layout_hash = digest_file(layout_path)
    result = {
        'experiment': 'EXP-007', 'artifact': 'Carnice Hybrid',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'control_path': str(CONTROL), 'source_control_path': str(SOURCE),
        'base_repo': BASE_REPO, 'base_revision': BASE_REV, 'base_index_sha256': BASE_INDEX_SHA256,
        'quantizer': {'mlx_vlm': '0.4.4', 'wheel_sha256': '3ff86ea738ab1914dc1b07e4fa5d4cc34bec5909e540692cfad0af808af13c11',
                      'mlx': '0.32.1', 'mlx_lm': '0.31.3', 'group_size': 64, 'bits': 4, 'mode': 'affine'},
        'changed_tensor_count': len(rows), 'retrieved_bf16_bytes': sum(r['bf16_bytes'] for r in rows),
        'rows': rows, 'control_model_weights_sha256': new_weight_hash,
        'control_manifest_sha256': digest_file(manifest_path),
        'reused_experts_all_exact': all(v['exact'] for v in expert_checks.values()),
        'reused_expert_hashes': expert_checks,
        'reused_layout_sha256': layout_hash,
        'stock_artifact_modified': False,
        'inference_started': False,
        'next_gate': 'Reissue an isolated verified-install receipt, then require explicit approval before any local-model load/inference validation.',
    }
    (CONTROL / 'EXP007-CONTROL-PROVENANCE.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    # Generated quantized files are retained as reproducibility artifacts; no
    # full BF16 source payload is retained by this control builder.
    print(json.dumps({'changed_tensor_count': len(rows), 'retrieved_bf16_bytes': result['retrieved_bf16_bytes'],
                      'model_weights_sha256': new_weight_hash, 'reused_experts_all_exact': result['reused_experts_all_exact']}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
