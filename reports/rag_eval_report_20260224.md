# RAG Evaluation Report — Smart IELTS Mentor

**Log source:** `terminals/3.txt` (lines 10–103)  
**Working directory:** `Smart_IELTS_Mentor`  
**Recorded on:** 2026-02-24  

---

## Commands executed

```bash
./.venv/bin/python scripts/eval_rag_quality.py --max-samples 10 --judge-model gpt-4o-mini
./.venv/bin/python scripts/eval_rag_runtime.py --max-samples 20
```

| Script | Purpose |
|--------|---------|
| `eval_rag_quality.py` | Faithfulness (LLM judge), context relevance (Phase 2) |
| `eval_rag_runtime.py` | Latency (retrieval / phase1 / phase2 / total), token usage |

---

## 1. Quality summary (`eval_rag_quality.py`)

| Metric | Value |
|--------|-------|
| Essays attempted | 10 |
| Essays succeeded | 10 |
| Essays failed | 0 |
| **Faithfulness avg score (1–5)** | **4.000** |
| **Faithfulness pass rate (judge)** | **75.0%** |
| **Criteria missing citation rate** | **25.0%** |
| **Context relevance avg score (1–5)** | **3.712** |
| **High relevance ratio (score ≥ 4)** | **60.0%** |
| Avg judge latency / call | 6.803s |
| Avg judge tokens / call | 1360.7 |

### Per-essay breakdown

| Essay | faith_avg | relevance_avg |
|-------|-----------|---------------|
| 1/10 | 2.75 | 3.38 |
| 2/10 | 4.75 | 3.38 |
| 3/10 | 4.75 | 3.88 |
| 4/10 | 4.75 | 3.88 |
| 5/10 | 4.75 | 3.75 |
| 6/10 | 4.75 | 3.50 |
| 7/10 | 3.25 | 3.75 |
| 8/10 | 3.25 | 3.62 |
| 9/10 | 2.75 | 4.00 |
| 10/10 | 4.25 | 4.00 |

---

## 2. Runtime summary (`eval_rag_runtime.py`)

| Metric | Value |
|--------|-------|
| Requests attempted | 20 |
| Requests succeeded | 20 |
| Requests failed | 0 |
| **Success rate** | **100.0%** |
| **Avg retrieval latency** | **2.697s** |
| **Avg phase1 LLM latency** | **2.630s** |
| **Avg phase2 LLM latency** | **4.657s** |
| **Avg total latency** | **9.984s** |
| **P50 total latency** | **10.095s** |
| **P95 total latency** | **12.640s** |
| Avg input tokens / request | 4472.8 |
| Avg output tokens / request | 705.4 |
| **Avg total tokens / request** | **5178.2** |
| **P95 total tokens / request** | **5330.0** |

### Per-request detail (latency & tokens)

| # | latency_total | retr | p1 | p2 | tokens |
|---|---------------|------|----|----|--------|
| 1/20 | 10.66s | 3.51s | 3.00s | 4.16s | 5330 |
| 2/20 | 9.52s | 1.96s | 2.48s | 5.08s | 5147 |
| 3/20 | 10.55s | 3.27s | 2.51s | 4.77s | 5246 |
| 4/20 | 8.59s | 2.97s | 2.20s | 3.43s | 5179 |
| 5/20 | 10.25s | 2.88s | 2.28s | 5.08s | 5353 |
| 6/20 | 12.64s | 5.52s | 3.32s | 3.80s | 4971 |
| 7/20 | 11.07s | 2.09s | 2.44s | 6.53s | 5276 |
| 8/20 | 8.23s | 2.03s | 2.35s | 3.85s | 5106 |
| 9/20 | 8.89s | 1.94s | 2.53s | 4.42s | 5170 |
| 10/20 | 13.29s | 2.21s | 2.34s | 8.74s | 5136 |
| 11/20 | 10.10s | 2.20s | 2.56s | 5.33s | 5259 |
| 12/20 | 8.85s | 2.18s | 2.36s | 4.32s | 5228 |
| 13/20 | 11.62s | 4.61s | 2.38s | 4.63s | 5161 |
| 14/20 | 9.21s | 3.41s | 2.02s | 3.78s | 5087 |
| 15/20 | 8.99s | 2.00s | 2.53s | 4.46s | 5115 |
| 16/20 | 11.11s | 2.08s | 5.81s | 3.22s | 5076 |
| 17/20 | 9.60s | 2.65s | 2.37s | 4.58s | 5210 |
| 18/20 | 8.00s | 2.21s | 2.06s | 3.72s | 5077 |
| 19/20 | 10.49s | 2.25s | 2.69s | 5.56s | 5264 |
| 20/20 | 8.04s | 1.97s | 2.39s | 3.68s | 5173 |

---

## 3. Notes — Citation mismatch (log)

The log contains many lines like:

`Citation mismatch: <criterion> band X.X cited descriptor band Y.Y (index Z)`

**Common causes:**

- Descriptor evidence uses **whole bands only** (6.0, 7.0, 8.0, …) while the model assigns **half-bands** (6.5, 7.5, 8.5) → strict comparison of `criterion_band` vs `cited_band` triggers a mismatch.
- Some cases cite the wrong adjacent band (e.g. 7.5 citing 8.0) — review the prompt or relax validation (e.g. ±0.5 tolerance).

These are **validation warnings**; they did not fail the pipeline in this run.

---

## 4. Executive summary

| Area | Brief assessment |
|------|------------------|
| **Reliability** | 100% success for both quality (10/10) and runtime (20/20). |
| **Faithfulness** | Mean 4/5; 75% pass per judge — room for improvement. |
| **Relevance** | ~3.71/5; 60% of chunks score ≥4 — retrieval is usable but uneven. |
| **Citation** | 25% of criteria missing citation after parse — monitor when tuning half-bands. |
| **Latency** | ~10s average; Phase 2 LLM is typically slower than Phase 1. |
| **Token cost** | ~5.2k tokens/request on average; P95 ~5.33k. |

---
