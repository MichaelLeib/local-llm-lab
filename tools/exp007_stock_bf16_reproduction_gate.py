#!/usr/bin/env python3
"""EXP-007 stock BF16→MLX affine reproduction gate.

Acquires only selected official Qwen3.6 BF16 tensors via SafeTensors HTTP ranges,
then compares mlx-vlm-0.4.4's MLX affine quantizer output to corresponding range
slices of the frozen stock MLX source. No model is loaded for inference.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import mlx.core as mx
import numpy as np

ROOT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab')
OUT = ROOT / 'results/raw/EXP-007'
PROV = OUT / 'quantizer-provenance'
CACHE = PROV / 'stock-bf16-reproduction-gate'
HEADERS_PATH = OUT / 'source/safetensors-headers.json'

BASE_REPO = 'Qwen/Qwen3.6-35B-A3B'
MLX_REPO = 'mlx-community/Qwen3.6-35B-A3B-4bit'
MLX_REV = '38740b847e4cb78f352aba30aa41c76e08e6eb46'
UA = {'User-Agent': 'Local-LLM-Lab-EXP-007/1.0'}

# One full-attention block spans all tested projection geometries. The expert
# samples exercise the two packed BF16 source layouts (fused gate+up and down)
# and all three runtime expert projections across two distant layer/index pairs.
REQUESTED = [
    ('attention', 'model.language_model.layers.3.self_attn.q_proj.weight'),
    ('attention', 'model.language_model.layers.3.self_attn.k_proj.weight'),
    ('attention', 'model.language_model.layers.3.self_attn.v_proj.weight'),
    ('attention', 'model.language_model.layers.3.self_attn.o_proj.weight'),
]
EXPERT_SLICES = [(3, 0), (39, 255)]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve(repo: str, rev: str, path: str) -> str:
    return f'https://huggingface.co/{repo}/resolve/{rev}/{path}'


def fetch(url: str, start: int | None = None, end: int | None = None, attempts: int = 3) -> tuple[bytes, dict, str]:
    headers = dict(UA)
    if start is not None:
        headers['Range'] = f'bytes={start}-{end}'
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as response:
                data = response.read()
                meta = dict(response.headers)
                status = getattr(response, 'status', None)
                if start is not None and status != 206:
                    raise RuntimeError(f'expected HTTP 206 for range, got {status}')
                if start is not None and len(data) != end - start + 1:
                    raise RuntimeError(f'range length {len(data)} != expected {end-start+1}')
                return data, meta | {'_status': status, '_attempt': attempt}, response.geturl()
        except Exception as exc:  # deterministic bounded retries
            last = repr(exc)
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f'fetch failed after {attempts} attempts: {last}')


def safetensors_header(repo: str, rev: str, shard: str) -> dict:
    url = resolve(repo, rev, shard)
    prefix, _, _ = fetch(url, 0, 7)
    n = int.from_bytes(prefix, 'little')
    raw, _, _ = fetch(url, 8, 7 + n)
    parsed = json.loads(raw)
    return {
        'file': shard,
        'header_bytes': n,
        'header_sha256': sha(raw),
        'tensors': {k: {'dtype': v['dtype'], 'shape': v['shape'], 'offsets': v['data_offsets']}
                    for k, v in parsed.items() if k != '__metadata__'},
    }


def bf16_to_mx(payload: bytes, shape: list[int]) -> mx.array:
    expected = int(np.prod(shape)) * 2
    if len(payload) != expected:
        raise ValueError(f'BF16 payload length {len(payload)} != {expected}')
    # SafeTensors BF16 is little-endian IEEE bfloat16. Preserve its exact bit
    # pattern by viewing U16 words as bfloat16 rather than converting through F32.
    words = np.frombuffer(payload, dtype='<u2').copy().reshape(shape)
    return mx.array(words).view(mx.bfloat16)


def mlx_bytes(values: tuple[mx.array, mx.array, mx.array]) -> list[bytes]:
    # MLX does not expose ndarray-style .tobytes(). Saving a tiny SafeTensors
    # container gives the canonical MLX serialization bytes we compare remotely.
    temp = CACHE / 'generated.safetensors'
    mx.save_safetensors(str(temp), {'weight': values[0], 'scales': values[1], 'biases': values[2]})
    raw = temp.read_bytes()
    n = int.from_bytes(raw[:8], 'little')
    h = json.loads(raw[8:8+n])
    body = 8 + n
    return [raw[body + h[k]['data_offsets'][0]:body + h[k]['data_offsets'][1]]
            for k in ('weight', 'scales', 'biases')]


def official_to_mlx_key(name: str) -> tuple[str, int | None]:
    prefix = 'model.language_model.'
    if not name.startswith(prefix):
        raise ValueError(name)
    logical = name[len(prefix):]
    if not logical.endswith('.weight'):
        raise ValueError(f'expected a weight tensor name: {name}')
    logical = logical[:-len('.weight')]
    marker = '.mlp.experts.'
    if marker not in logical:
        return 'language_model.model.' + logical, None
    before, rest = logical.split(marker, 1)
    expert, suffix = rest.split('.', 1)
    return 'language_model.model.' + before + '.mlp.switch_mlp.' + suffix, int(expert)


def target_part(name: str, expert: int | None, component: str, stock_headers: dict) -> tuple[str, dict, int, int]:
    key, mapped_expert = official_to_mlx_key(name)
    if mapped_expert != expert:
        raise ValueError('expert mapping mismatch')
    _, record = stock_headers[key + '.' + component]
    start, end = record['offsets']
    if expert is None:
        return key + '.' + component, record, start, end
    shape = record['shape']
    if shape[0] != 256:
        raise ValueError(f'expected expert-major tensor, got {shape}')
    item_bytes = (end - start) // shape[0]
    return key + '.' + component, record, start + expert * item_bytes, start + (expert + 1) * item_bytes


def compare_to_stock_mlx(generated: list[bytes], key: str, expert: int | None,
                         stock_headers: dict, stock_shards: dict) -> list[dict]:
    components = []
    for component, generated_bytes in zip(('weight', 'scales', 'biases'), generated):
        target = key + '.' + component
        target_shard, record = stock_headers[target]
        start, end = record['offsets']
        if expert is not None:
            if record['shape'][0] != 256:
                raise ValueError(f'expected expert-major stock tensor for {target}, got {record["shape"]}')
            item = (end - start) // 256
            start, end = start + expert * item, start + (expert + 1) * item
        hbytes = stock_shards[target_shard]['header_bytes']
        remote, rinfo, rfinal = fetch(resolve(MLX_REPO, MLX_REV, target_shard),
                                      8 + hbytes + start, 8 + hbytes + end - 1)
        components.append({
            'component': component, 'stock_mlx_tensor': target, 'stock_mlx_shard': target_shard,
            'stock_mlx_safetensors_offsets': [start, end],
            'generated_bytes': len(generated_bytes), 'generated_sha256': sha(generated_bytes),
            'reference_sha256': sha(remote), 'exact_bytes_equal': generated_bytes == remote,
            'range_transport': {'status': rinfo['_status'], 'attempt': rinfo['_attempt'], 'final_url': rfinal,
                                'content_range': rinfo.get('Content-Range')},
        })
    return components


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit('use the pinned EXP-007 Python environment')
    CACHE.mkdir(parents=True, exist_ok=True)
    # Establish exact official base snapshot now; previous EXP-005 metadata pins
    # the converted MLX revision but did not record the upstream BF16 revision.
    api, _, _ = fetch('https://huggingface.co/api/models/' + urllib.parse.quote(BASE_REPO, safe='/'))
    base_rev = json.loads(api)['sha']
    index_data, _, _ = fetch(resolve(BASE_REPO, base_rev, 'model.safetensors.index.json'))
    index = json.loads(index_data)
    selected = [n for _, n in REQUESTED]
    for layer, _ in EXPERT_SLICES:
        selected.extend([
            f'model.language_model.layers.{layer}.mlp.experts.gate_up_proj',
            f'model.language_model.layers.{layer}.mlp.experts.down_proj',
        ])
    missing = [n for n in selected if n not in index['weight_map']]
    if missing:
        raise RuntimeError(f'official index missing expected tensors: {missing}')
    base_shards = sorted({index['weight_map'][n] for n in selected})
    base_headers = {s: safetensors_header(BASE_REPO, base_rev, s) for s in base_shards}

    cached = json.loads(HEADERS_PATH.read_text())['headers']['stock']
    stock_shards = {entry['file']: entry for entry in cached}
    stock_tensors = {name: (entry['file'], tensor)
                     for entry in cached for name, tensor in entry['tensors'].items()}
    rows = []
    for category, name in REQUESTED:
        shard = index['weight_map'][name]
        bf = base_headers[shard]['tensors'][name]
        if bf['dtype'] != 'BF16':
            raise RuntimeError(f'{name} is {bf["dtype"]}, not BF16')
        start, end = bf['offsets']
        http_start = 8 + base_headers[shard]['header_bytes'] + start
        http_end = 8 + base_headers[shard]['header_bytes'] + end - 1
        payload, info, final = fetch(resolve(BASE_REPO, base_rev, shard), http_start, http_end)
        local = CACHE / ('base-' + name.replace('.', '_') + '.bf16')
        local.write_bytes(payload)

        source = bf16_to_mx(payload, bf['shape'])
        generated = mlx_bytes(tuple(mx.quantize(source, group_size=64, bits=4, mode='affine')))
        expert = int(name.split('.mlp.experts.')[1].split('.', 1)[0]) if '.mlp.experts.' in name else None
        target_components = []
        for component, generated_bytes in zip(('weight', 'scales', 'biases'), generated):
            key, ref, rstart, rend = target_part(name, expert, component, stock_tensors)
            target_shard = stock_tensors[key][0]
            hbytes = stock_shards[target_shard]['header_bytes']
            remote, rinfo, rfinal = fetch(resolve(MLX_REPO, MLX_REV, target_shard), 8+hbytes+rstart, 8+hbytes+rend-1)
            target_components.append({
                'component': component, 'stock_mlx_tensor': key, 'stock_mlx_shard': target_shard,
                'stock_mlx_safetensors_offsets': [rstart, rend],
                'generated_bytes': len(generated_bytes), 'generated_sha256': sha(generated_bytes),
                'reference_sha256': sha(remote), 'exact_bytes_equal': generated_bytes == remote,
                'range_transport': {'status': rinfo['_status'], 'attempt': rinfo['_attempt'], 'final_url': rfinal,
                                    'content_range': rinfo.get('Content-Range')},
            })
        rows.append({
            'category': category, 'official_bf16_tensor': name, 'official_base_shard': shard,
            'official_shape': bf['shape'], 'bf16_bytes': len(payload), 'bf16_sha256': sha(payload),
            'bf16_file': str(local.relative_to(ROOT)),
            'base_transport': {'status': info['_status'], 'attempt': info['_attempt'], 'final_url': final,
                               'content_range': info.get('Content-Range')},
            'quantizer': {'implementation': 'mlx.core.quantize', 'group_size': 64, 'bits': 4, 'mode': 'affine'},
            'components': target_components,
            'all_components_exact': all(x['exact_bytes_equal'] for x in target_components),
        })

    # Official BF16 stores routed experts batched by layer. Fetching just one
    # expert's contiguous slice validates the exact streamed-expert layouts
    # without downloading any complete 256-expert tensor.
    for layer, expert in EXPERT_SLICES:
        for source_suffix, outputs in (
            ('gate_up_proj', (('gate_proj', 0), ('up_proj', 1))),
            ('down_proj', (('down_proj', None),)),
        ):
            name = f'model.language_model.layers.{layer}.mlp.experts.{source_suffix}'
            shard = index['weight_map'][name]
            bf = base_headers[shard]['tensors'][name]
            if bf['dtype'] != 'BF16' or bf['shape'][0] != 256:
                raise RuntimeError(f'unexpected routed-expert BF16 layout for {name}: {bf}')
            start, end = bf['offsets']
            per_expert = (end - start) // 256
            http_start = 8 + base_headers[shard]['header_bytes'] + start + expert * per_expert
            http_end = http_start + per_expert - 1
            payload, info, final = fetch(resolve(BASE_REPO, base_rev, shard), http_start, http_end)
            local = CACHE / f'base-layer{layer:02d}-expert{expert:03d}-{source_suffix}.bf16'
            local.write_bytes(payload)
            source = bf16_to_mx(payload, bf['shape'][1:])
            for projection, half in outputs:
                value = source if half is None else source[half * (source.shape[0] // 2):(half + 1) * (source.shape[0] // 2)]
                generated = mlx_bytes(tuple(mx.quantize(value, group_size=64, bits=4, mode='affine')))
                stock_key = f'language_model.model.layers.{layer}.mlp.switch_mlp.{projection}'
                components = compare_to_stock_mlx(generated, stock_key, expert, stock_tensors, stock_shards)
                rows.append({
                    'category': 'routed_expert', 'official_bf16_tensor': name,
                    'official_bf16_slice': {'expert': expert, 'projection': projection, 'source_layout': bf['shape']},
                    'official_base_shard': shard, 'official_shape': list(value.shape),
                    'bf16_bytes': len(payload) if source_suffix == 'down_proj' else len(payload) // 2,
                    'bf16_container_slice_bytes': len(payload), 'bf16_sha256': sha(payload),
                    'bf16_file': str(local.relative_to(ROOT)),
                    'base_transport': {'status': info['_status'], 'attempt': info['_attempt'], 'final_url': final,
                                       'content_range': info.get('Content-Range')},
                    'quantizer': {'implementation': 'mlx.core.quantize', 'group_size': 64, 'bits': 4, 'mode': 'affine'},
                    'components': components,
                    'all_components_exact': all(x['exact_bytes_equal'] for x in components),
                })
    report = {
        'experiment': 'EXP-007', 'gate': 'stock_bf16_to_mlx_affine_reproduction',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'pinned_environment': {'mlx_vlm': '0.4.4', 'wheel_sha256': '3ff86ea738ab1914dc1b07e4fa5d4cc34bec5909e540692cfad0af808af13c11',
                               'mlx': '0.32.1', 'mlx_lm': '0.31.3'},
        'official_base': {'repo': BASE_REPO, 'revision': base_rev, 'index_sha256': sha(index_data), 'selected_shards': base_shards},
        'reference_mlx': {'repo': MLX_REPO, 'revision': MLX_REV},
        'selected_tensor_count': len(rows), 'selected_bf16_bytes': sum(r['bf16_bytes'] for r in rows),
        'rows': rows,
        'all_components_exact': all(r['all_components_exact'] for r in rows),
        'interpretation': 'Exact match establishes only the selected tensor/sample conversion contract. A mismatch does not invalidate EXP-007; it requires the Stock Hybrid Control branch before Carnice acquisition.',
    }
    (PROV / 'stock-bf16-to-mlx-reproduction.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'base_revision': base_rev, 'tensors': len(rows), 'bf16_bytes': report['selected_bf16_bytes'],
                      'all_components_exact': report['all_components_exact'],
                      'exact_rows': sum(r['all_components_exact'] for r in rows)}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
