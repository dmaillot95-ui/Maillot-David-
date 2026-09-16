#!/usr/bin/env python3
"""CEREBRON VECTOR-ZIP Ω
Zero-paid-API local semantic compression prototype.

Design goals:
- keep exact source text externally addressable by SHA-256;
- derive compact lexical vectors locally (no external embeddings API);
- retrieve only relevant chunks for active context;
- measure compression/retrieval efficiency without claiming lossless semantic reconstruction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]+", re.UNICODE)


def tokenize(text: str):
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def chunk_text(text: str, max_chars: int = 1400):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur = [], []
    size = 0
    for p in paras:
        extra = len(p) + (2 if cur else 0)
        if cur and size + extra > max_chars:
            out.append("\n\n".join(cur))
            cur, size = [], 0
        cur.append(p)
        size += extra
    if cur:
        out.append("\n\n".join(cur))
    return out


def hashed_vector(text: str, dims: int = 256):
    counts = Counter(tokenize(text))
    v = [0.0] * dims
    for tok, c in counts.items():
        h = int(hashlib.sha256(tok.encode()).hexdigest()[:16], 16)
        idx = h % dims
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        v[idx] += sign * (1.0 + math.log(c))
    norm = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x / norm for x in v]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def summarize(text: str, max_chars: int = 280):
    s = re.sub(r"\s+", " ", text).strip()
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars]
    last = max(cut.rfind('. '), cut.rfind('; '), cut.rfind(': '))
    if last > max_chars // 2:
        cut = cut[: last + 1]
    return cut + " …"


def build_index(root: Path, output: Path, dims: int = 256, max_chars: int = 1400):
    rows = []
    source_chars = 0
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in {'.md','.txt','.py','.json','.yml','.yaml'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        source_chars += len(text)
        for i, chunk in enumerate(chunk_text(text, max_chars=max_chars)):
            rows.append({
                'chunk_id': f'{path.as_posix()}#{i}',
                'path': path.as_posix(),
                'ordinal': i,
                'source_sha256': hashlib.sha256(chunk.encode()).hexdigest(),
                'summary': summarize(chunk),
                'vector': hashed_vector(chunk, dims),
                'chars': len(chunk),
            })
    payload = {
        'format':'CEREBRON_VECTOR_ZIP_V1',
        'dims':dims,
        'source_root':str(root),
        'chunks':rows,
        'stats':{
            'files_indexed':len({r['path'] for r in rows}),
            'chunks':len(rows),
            'source_chars':source_chars,
            'index_json_chars':0,
        }
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(',',':'))
    payload['stats']['index_json_chars'] = len(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


def retrieve(index_path: Path, query: str, top_k: int = 5):
    data = json.loads(index_path.read_text(encoding='utf-8'))
    qv = hashed_vector(query, data['dims'])
    scored = [(dot(qv, r['vector']), r) for r in data['chunks']]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{'score':round(s,6), **{k:v for k,v in r.items() if k!='vector'}} for s,r in scored[:top_k]]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('root')
    b.add_argument('output')
    b.add_argument('--dims', type=int, default=256)
    b.add_argument('--max-chars', type=int, default=1400)
    q = sub.add_parser('query')
    q.add_argument('index')
    q.add_argument('query')
    q.add_argument('--top-k', type=int, default=5)
    args = ap.parse_args()
    if args.cmd == 'build':
        p = build_index(Path(args.root), Path(args.output), args.dims, args.max_chars)
        print(json.dumps(p['stats'], indent=2))
    else:
        print(json.dumps(retrieve(Path(args.index), args.query, args.top_k), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
