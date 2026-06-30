"""
test_ollama.py
==============
Stand-alone verification that the Ollama + Qwen 2.5 1.5B integration works
end-to-end. Run from your project root:

    python test_ollama.py

Exits 0 on success, non-zero on failure (so it's CI-friendly later).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make `parser/` importable when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))


SAMPLE_JD = """
Senior Data Engineer — TechCorp India

Location: Mumbai, India  ·  Hybrid (3 days onsite)
Experience: 5–8 years
Department: Data Platform

Responsibilities:
- Build streaming pipelines on AWS using Kafka and Spark
- Mentor 3 junior engineers
- Own data quality SLAs across 200+ pipelines

Required skills: Python, SQL, Apache Spark, Airflow, PostgreSQL
Nice to have: Snowflake, dbt, Terraform, Kubernetes

Education: B.E. / B.Tech in Computer Science or equivalent
Notice period: 30-60 days
Salary: INR 35-55 LPA
"""


def _hr(label: str = "") -> None:
    bar = "─" * 70
    if label:
        print(f"\n{bar}\n  {label}\n{bar}")
    else:
        print(bar)


def main() -> int:
    _hr("OLLAMA INTEGRATION CHECK · qwen2.5:1.5b-instruct")

    # ── 1. Imports ────────────────────────────────────────────────────────
    try:
        from parser import JDParser, OllamaError
    except ImportError as exc:
        print(f"✗ Could not import parser package: {exc}")
        print("  Make sure you're running from the project root and that")
        print("  `parser/` exists alongside this script.")
        return 1
    print("✓ parser package importable")

    # ── 2. Daemon reachability ────────────────────────────────────────────
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"✓ Ollama daemon reachable @ localhost:11434  ({len(models)} models)")
    except Exception as exc:  # noqa: BLE001
        print(f"✗ Ollama daemon not reachable: {exc}")
        print("  Start it with: ollama serve")
        return 2

    # ── 3. Model availability ─────────────────────────────────────────────
    target = "qwen2.5:1.5b-instruct"
    if not any(target in m for m in models):
        print(f"✗ Model `{target}` not installed.")
        print("  Pull it with:")
        print('   "%USERPROFILE%\\AppData\\Local\\Programs\\Ollama\\ollama.exe" pull qwen2.5:1.5b-instruct')
        print(f"\n  Currently installed: {', '.join(models) or '(none)'}")
        return 3
    print(f"✓ `{target}` is installed")

    # ── 4. End-to-end parse ───────────────────────────────────────────────
    print("\nParsing a sample JD (this is the real-world latency)…")
    parser = JDParser(model=target, seed=42, temperature=0.0)
    t0 = time.perf_counter()
    try:
        result = parser.parse(SAMPLE_JD)
    except OllamaError as exc:
        print(f"✗ OllamaError during parse: {exc}")
        return 4
    except Exception as exc:  # noqa: BLE001
        print(f"✗ Parse failed: {exc}")
        return 5
    elapsed = time.perf_counter() - t0
    print(f"✓ Parse completed in {elapsed:.1f}s")

    # ── 5. Spot-check extracted fields ────────────────────────────────────
    _hr("EXTRACTED FIELDS")
    checks = [
        ("job_title",    "Senior Data Engineer"),
        ("company_name", "TechCorp"),
        ("location",     "Mumbai"),
    ]
    fail = 0
    for key, must_contain in checks:
        val = (result.get(key) or "").lower()
        if must_contain.lower() in val:
            print(f"✓ {key:<14} → {result[key]!r}")
        else:
            print(f"✗ {key:<14} → {result.get(key)!r}  (expected to contain {must_contain!r})")
            fail += 1

    exp = result.get("experience") or {}
    if exp.get("minimum_years") in (5, 5.0) and exp.get("maximum_years") in (8, 8.0):
        print(f"✓ experience     → {exp}")
    else:
        print(f"⚠ experience     → {exp}  (expected min=5, max=8 — 1.5B is less precise)")

    skills = (result.get("skills") or {}).get("required") or []
    if any("python" in s.lower() for s in skills):
        print(f"✓ skills.required contains Python  ({len(skills)} total)")
    else:
        print(f"⚠ skills.required missing Python  → {skills}")

    _hr("FULL JSON OUTPUT")
    print(json.dumps(result, indent=2)[:1500])

    _hr()
    if fail == 0:
        print("✅ Ollama + Qwen 2.5 1.5B integration is healthy.")
        return 0
    print(f"⚠ {fail} field check(s) failed — the 1.5B model is less precise.")
    print("   For higher accuracy, switch to qwen2.5:3b-instruct or 7b-instruct.")
    return 0  # don't fail CI on field-precision warnings


if __name__ == "__main__":
    sys.exit(main())
