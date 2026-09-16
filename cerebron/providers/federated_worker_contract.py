#!/usr/bin/env python3
"""CEREBRON Ω universal worker contract for heterogeneous compute providers.

This module defines a provider-neutral task/result schema. External providers are
strictly opt-in and MUST NOT be called unless explicitly enabled by environment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import json
import time
import uuid


@dataclass
class WorkerTask:
    task_id: str
    domain: str
    prompt: str
    expected_output_schema: str = "text"
    evidence_required: bool = True
    budget_eur: float = 0.0
    provider_hint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, domain: str, prompt: str, **kwargs: Any) -> "WorkerTask":
        return cls(task_id=f"task-{uuid.uuid4().hex[:16]}", domain=domain, prompt=prompt, **kwargs)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class WorkerResult:
    task_id: str
    provider: str
    worker_id: str
    ok: bool
    result: str
    evidence: Optional[Dict[str, Any]]
    runtime_s: float
    cost_eur: float
    error: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Timer:
    def __enter__(self):
        self.started = time.time()
        self.elapsed_s = 0.0
        return self

    def elapsed(self) -> float:
        self.elapsed_s = time.time() - self.started
        return self.elapsed_s

    def __exit__(self, exc_type, exc, tb):
        self.elapsed()


def validate_zero_euro(task: WorkerTask) -> None:
    if task.budget_eur > 0:
        raise RuntimeError("Paid execution disabled by default: budget_eur must be 0 unless explicitly redesigned.")
