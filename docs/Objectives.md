# Measurable Objectives & Performance Report

**Discipline:** Full Stack Engineering  
**Candidate:** Husnain  
**Branch:** `dev-test01`  
**Base Commit SHA:** `0482c4793e291bc4a48808cf153fae9e88e7b8d7`  

---

## 1. System Environment & Specifications
* **Operating System:** Windows 11 (64-bit)
* **Processor (CPU):** AMD Ryzen 5 7430U with Radeon Graphics
* **Memory (RAM):** 16.0 GB
* **Cloned Commit SHA:** `0482c4793e291bc4a48808cf153fae9e88e7b8d7`
* **Stack:** Docker Compose (CVAT backend, Postgres, Redis in-memory, Traefik v3, React UI)

---

## 2. Objective Specification (MO-1)

| Field | Entry |
| :--- | :--- |
| **ID** | **MO-1** |
| **What is measured** | End-to-end response latency of the class count analytics endpoint (`GET /api/test/analytics/class-counts/?task_id=1`). |
| **How** | Python measurement client executing 5 sequential authenticated HTTP GET requests against the local API, timing roundtrip from request dispatch to complete response payload deserialization using `time.perf_counter()`. |
| **Target** | Median of 5 runs at or below **50.00 ms**. |
| **Conditions** | Local Docker stack, database populated with test tasks and annotation shapes, cache warm, no background workloads running. |
| **Not included** | Cold-start container initialization or first database connection establishment. |

---

## 3. Raw Measurement Output (5 Consecutive Runs)

```
[2026-10-07 06:25:14,832] INFO cvat.apps.test.signals: Successfully registered CVAT annotation save plugins for real-time analytics.
Run 1: 21.47 ms (status 200)
Run 2: 22.29 ms (status 200)
Run 3: 21.72 ms (status 200)
Run 4: 22.23 ms (status 200)
Run 5: 21.53 ms (status 200)
```

---

## 4. Benchmark Results & Analysis

* **Run 1:** 21.47 ms
* **Run 2:** 22.29 ms
* **Run 3:** 21.72 ms
* **Run 4:** 22.23 ms
* **Run 5:** 21.53 ms
* **Median:** **21.72 ms**
* **Minimum:** 21.47 ms
* **Maximum:** 22.29 ms
* **Spread (Max - Min):** **0.82 ms**

### Conclusion:
**Target MET.** The measured median latency of **21.72 ms** comfortably cleared the target threshold of **50.00 ms** with an exceptionally tight spread of **0.82 ms**, validating the single-pass database aggregation strategy.
