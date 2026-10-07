# Definition of Done — Verification & Evidence Checklist

**Candidate:** Husnain  
**Branch:** `dev-test01`  

---

## Verification Checklist

- [x] **1. Endpoint returns correct counts, checked against a known task.**  
  *Evidence:* Verified against database task #1 (`Street-Camera-01`) returning `car: 1`, and task #3 (`Road`) returning `car: 1, traffic lights: 1`. Endpoint returns structured counts matching database records.
- [x] **2. Page renders the graph, with the empty and error cases covered.**  
  *Evidence:* Handled via Ant Design in `analytics-page.tsx`. Tasks with zero annotations display `<Empty description="No annotations found for this task..." />`. Failed requests or disconnected streams display an error `<Alert message="Failed to Load Analytics..." />`.
- [x] **3. Objective measured, 5 runs, raw output saved.**  
  *Evidence:* Executed 5 consecutive runs documented in `docs/Objectives.md`. Raw output: `[21.47, 22.29, 21.72, 22.23, 21.53] ms`. Median: `21.72 ms`, Spread: `0.82 ms`.
- [x] **4. Target met, or missed with the reason written down.**  
  *Evidence:* Target was `<= 50.00 ms`. Achieved median was `21.72 ms` (Target MET).
- [x] **5. Authentication and task access permissions enforced.**  
  *Evidence:* Unauthenticated requests rejected with `401 Unauthorized` (verified). Requests by users without task authorization rejected with `403 Forbidden` via `TaskPermission` check (verified).
- [x] **6. Filter or grouping beyond plain count implemented with rationale.**  
  *Evidence:* Grouped by `image_count` (unique frames containing class) alongside `annotation_count`. Rationale: Prevents class spatial clustering bias in training datasets.
- [x] **7. Graph updates live as annotations change, over WebSocket.**  
  *Evidence:* WebSocket consumer on `ws://localhost:8080/api/test/analytics/ws/{task_id}/` receives push broadcasts via Redis Pub/Sub triggered by CVAT `add_plugin` hooks on `patch_job_data` / `put_job_data`.
- [x] **8. Page recovers when the connection drops and comes back.**  
  *Evidence:* Implemented in `use-analytics-websocket.ts` using 30s heartbeat ping/pong and capped exponential backoff reconnection (`1s → 1.5s → 2.25s ... 15s`).
- [x] **9. Decision record written inside Plan.**  
  *Evidence:* Documented in `docs/Plan.md` covering WebSocket vs. Polling, CVAT plugin hooks vs. `post_save`, and database aggregation vs. in-memory processing.
- [x] **10. Everything I did not finish is listed.**  
  *Evidence:* Cross-task comparative analytics and multi-month historical trend forecasts were deferred to v2.0 (documented in `docs/Plan.md`).
