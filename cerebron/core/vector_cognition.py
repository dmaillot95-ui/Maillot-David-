#!/usr/bin/env python3
"""CEREBRON VECTOR-COGNITION Ω — local, auditable prototype.

This module does NOT claim AGI/superintelligence. It implements a deterministic
vector memory + cross-idea routing layer that can sit in front of multiple AI
providers. No paid API is required for the built-in test/demo.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from math import sqrt
from typing import Iterable
import json
import re

DIM = 256
KINDS = {"idea", "hypothesis", "prediction", "reasoning", "evidence", "contradiction", "invention"}


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZÀ-ÿ0-9_+-]+", text.lower())


def embed(text: str, dim: int = DIM) -> list[float]:
    """Signed feature-hash embedding: dependency-free and reproducible."""
    v = [0.0] * dim
    ts = tokens(text)
    feats = ts + [f"{ts[i]}::{ts[i+1]}" for i in range(len(ts)-1)]
    for f in feats:
        h = sha256(f.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if (h[4] & 1) == 0 else -1.0
        v[idx] += sign
    n = sqrt(sum(x*x for x in v)) or 1.0
    return [x/n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x*y for x, y in zip(a, b))


def contradiction_score(a: str, b: str) -> float:
    """Cheap explicit-negation detector; a flag, never a proof of contradiction."""
    na, nb = a.lower(), b.lower()
    neg = (" not ", " no ", " jamais ", " aucun ", " impossible ", " faux ")
    one_neg = any(x in na for x in neg) ^ any(x in nb for x in neg)
    lexical = cosine(embed(a), embed(b))
    return max(0.0, lexical) if one_neg else 0.0


@dataclass
class ThoughtAtom:
    id: str
    kind: str
    text: str
    evidence: float = 0.0
    novelty: float = 0.5
    utility: float = 0.5
    source: str = "local"

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind: {self.kind}")
        for n in ("evidence", "novelty", "utility"):
            x = getattr(self, n)
            if not 0.0 <= x <= 1.0:
                raise ValueError(f"{n} must be in [0,1]")

    @property
    def vector(self) -> list[float]:
        return embed(f"{self.kind} {self.text}")


class VectorCognition:
    def __init__(self):
        self.atoms: dict[str, ThoughtAtom] = {}

    def add(self, atom: ThoughtAtom) -> None:
        if atom.id in self.atoms:
            raise ValueError(f"duplicate id {atom.id}")
        self.atoms[atom.id] = atom

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        q = embed(query)
        rows = []
        for a in self.atoms.values():
            sim = cosine(q, a.vector)
            score = 0.55*sim + 0.20*a.evidence + 0.15*a.utility + 0.10*a.novelty
            rows.append({"id": a.id, "score": round(score, 6), "similarity": round(sim, 6), "kind": a.kind})
        return sorted(rows, key=lambda x: x["score"], reverse=True)[:k]

    def cross(self, a_id: str, b_id: str) -> dict:
        """Build a candidate relation for downstream AI/scientific checking."""
        a, b = self.atoms[a_id], self.atoms[b_id]
        sim = cosine(a.vector, b.vector)
        contra = contradiction_score(a.text, b.text)
        complement = max(0.0, 1.0 - abs(sim))
        evidence_floor = min(a.evidence, b.evidence)
        discovery = 0.40*complement + 0.25*min(a.novelty, b.novelty) + 0.20*min(a.utility, b.utility) + 0.15*evidence_floor
        return {
            "pair": [a_id, b_id],
            "semantic_similarity": round(sim, 6),
            "contradiction_flag": round(contra, 6),
            "discovery_priority": round(discovery, 6),
            "status": "CANDIDATE_NOT_PROVEN",
        }

    def route(self, query: str, providers: list[dict], k_context: int = 5) -> dict:
        """Select provider by declared capabilities/cost/reliability; no call is made."""
        context = self.retrieve(query, k_context)
        qset = set(tokens(query))
        scored = []
        for p in providers:
            caps = set(p.get("capabilities", []))
            match = len(qset & caps) / max(1, len(qset))
            reliability = float(p.get("reliability", 0.5))
            cost = float(p.get("cost", 0.0))
            enabled = bool(p.get("enabled", False))
            score = (0.55*match + 0.40*reliability - 0.05*cost) if enabled else -1.0
            scored.append({"provider": p["name"], "score": round(score, 6), "enabled": enabled})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"query": query, "context": context, "provider_ranking": scored, "selected": scored[0]["provider"] if scored and scored[0]["enabled"] else None}

    def frontier(self, limit: int = 10) -> list[dict]:
        ids = list(self.atoms)
        pairs = [self.cross(ids[i], ids[j]) for i in range(len(ids)) for j in range(i+1, len(ids))]
        return sorted(pairs, key=lambda x: x["discovery_priority"], reverse=True)[:limit]


def demo() -> dict:
    vc = VectorCognition()
    seed = [
        ThoughtAtom("I1", "idea", "Use causal graphs to separate correlation from mechanism", 0.7, 0.7, 0.9),
        ThoughtAtom("H1", "hypothesis", "A multiscale representation can expose invariants hidden at one scale", 0.3, 0.8, 0.8),
        ThoughtAtom("E1", "evidence", "Independent replication increases confidence in a result", 0.95, 0.2, 0.9),
        ThoughtAtom("C1", "contradiction", "A coherent model is not necessarily true", 0.95, 0.3, 1.0),
        ThoughtAtom("P1", "prediction", "Dynamic routing should reduce unnecessary model calls on simple tasks", 0.2, 0.7, 0.8),
        ThoughtAtom("N1", "invention", "Cross high-novelty distant concepts, then require evidence gates before promotion", 0.4, 0.9, 0.9),
    ]
    for a in seed:
        vc.add(a)
    providers = [
        {"name": "local_cpu", "capabilities": ["calculation", "retrieval", "routing", "simple"], "reliability": 0.8, "cost": 0.0, "enabled": True},
        {"name": "external_reasoner", "capabilities": ["reasoning", "proof", "science", "invention"], "reliability": 0.9, "cost": 1.0, "enabled": False},
    ]
    return {
        "engine": "CEREBRON_VECTOR_COGNITION_OMEGA_V1",
        "claims": {"superintelligence": False, "autonomous_discovery": False, "vector_crossing_prototype": True},
        "retrieval": vc.retrieve("reasoning invention evidence multiscale", 4),
        "frontier": vc.frontier(5),
        "route": vc.route("science reasoning invention", providers, 4),
        "atom_count": len(vc.atoms),
    }


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, sort_keys=True))
