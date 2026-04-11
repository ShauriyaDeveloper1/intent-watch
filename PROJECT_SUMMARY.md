# IntentWatch — Project Summary

IntentWatch is a local-first, real-time AI CCTV monitoring system:
- The **backend** (FastAPI) captures video (webcam / IP webcam / video file), runs YOLO-based inference, and emits alerts.
- The **frontend** (React + Vite) shows live video, alerts, analytics, history playback, and zone configuration.
- Optional integrations add **history uploads to Supabase**, **phone notifications via Telegram**, and a minimal **“Ask AI” (RAG) assistant** over recent alerts.

## Key features (implemented)

### Real-time video + AI detection
- **Video sources**
  - Local webcam (`/video/start-camera`)
  - Uploaded video files (`/video/upload` → becomes active stream)
  - IP Webcam / network URL inputs supported (including shorthand like `10.12.26.111:8080`)
- **Live MJPEG stream** for the UI (`/video/stream`, `/video/stream/{stream_id}`)
- **Inference pipeline**
  - Ultralytics YOLO model for general detection
  - Optional dedicated weapon model(s) (primary + verify + fallback)

### Alerting + evidence
- **Alert types** (from the current backend pipeline)
  - `Weapon` (with optional verify model and anti-spam rearm/cooldown)
  - `Unattended Bag` (near-person gating + persistence)
  - `Running` (simple motion/speed estimation over tracked persons)
  - `Loitering` (stationary detection + dwell threshold)
  - `Zone` (restricted-zone entry alerts + dwell alerts for other zones)
  - `door` (IoT door sensor events)
- **Snapshot capture**
  - Cropped JPEG snapshots saved locally and served via `/alerts/snapshot/...`
  - Optional upload of snapshots to Supabase Storage
- **Phone notifications (optional)**
  - Telegram sendMessage/sendPhoto forwarding for selected alert types

### Analytics + monitoring
- **Dashboard metrics** (`/metrics`): uptime, cameras online, streams running, people detected, active alerts
- **Alert analytics** (`/alerts/analytics`): counts, severity breakdown, hourly/day trends, recent alerts
- **Runtime debug** (`/debug/runtime`): environment knobs in effect, code fingerprints, and selected model paths

### Multi-camera streams
- Primary stream id is `primary`.
- Extra streams can be started/stopped dynamically (`/video/streams/start`, `/video/streams/stop`).

### History recording + playback (local-first)
- Streams (camera or file) can be recorded into **rotating clips** under `backend/data/history/<stream_id>/<YYYY-MM-DD>/...`.
- Clips are browseable/playable in the frontend’s History page.
- Optional Supabase upload of clips + sidecar metadata, and optional Postgres metadata insertion.
- Browser playback support includes **Range requests** and an optional **MP4 → WebM** transcode on demand (`?format=webm`).

### “Ask AI (Alerts)” — minimal RAG assistant
- Backend endpoint `POST /ask` answers questions using **only the in-memory recent alert store**.
- Retrieval uses embeddings **if** `sentence_transformers` is installed; otherwise it falls back to lexical overlap.
- Answer generation uses:
  - OpenAI if `OPENAI_API_KEY` is set (or `INTENTWATCH_RAG_PROVIDER=openai`), OR
  - Ollama if configured (or `INTENTWATCH_RAG_PROVIDER=ollama`), OR
  - an extractive “based on recent alerts” response.

## Tech stack

### Backend (Python)
- FastAPI + Uvicorn
- OpenCV (capture/encode, history clip writing, optional MP4→WebM conversion)
- Ultralytics YOLOv8 + Torch/Torchvision
- python-dotenv (loads `.env` from repo root and `backend/.env`)
- Supabase client (optional)

Dependencies are declared in:
- `requirements.txt` (repo root)
- `backend/requirements.txt` (backend-pinned versions)

### Frontend (TypeScript)
- React + TypeScript + Vite
- Tailwind CSS
- Radix UI components
- MUI (icons/material)
- Recharts (charts)
- framer-motion (route transitions)

Frontend dependencies: `Frontend/package.json`

## Repo layout (high-level)

- `backend/`
  - `api/main.py` — FastAPI app, routers, CORS, `.env` loading
  - `api/stream_manager.py` — capture/inference loop + alert logic + history/snapshots
  - `api/routes/` — REST endpoints (video/alerts/history/metrics/iot/ask)
  - `data/` — local artifacts
    - `videos/` uploaded videos
    - `history/` rotating clips
    - `snaps/` alert snapshots
- `Frontend/`
  - `src/services/api.ts` — typed client for backend endpoints
  - `src/app/pages/` — Dashboard, LiveFeed, Analytics, AlertsLog, History, Zones, Settings
- `scripts/` — model training + dataset tooling
- `datasets/` — YOLO dataset YAMLs + dataset archives
- `docs/` — hardware + architecture notes

## How to run (local)

### Recommended
1) One-time setup:
- `./setup.ps1`

2) Start backend + frontend:
- `./start-intentwatch.ps1`

Frontend:
- http://localhost:5173

Backend:
- http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### Backend only
- `./start-backend.ps1`

### Frontend only
- `./start-frontend.ps1`

## Backend API map

### Root
- `GET /` — health-ish root response

### Video (`/video/*`)
- `POST /video/upload` — upload a video file and start streaming it
- `POST /video/start-camera` — start webcam (or IP webcam if configured)
- `POST /video/start` — start stream from `source` (webcam/numeric id/path/url)
- `POST /video/stop` — stop primary stream
- `GET /video/status` — primary stream status
- `GET /video/status/{stream_id}` — per-stream status
- `GET /video/streams` — list known/running streams
- `POST /video/streams/start` — start extra stream `{stream_id, source}`
- `POST /video/streams/stop` — stop extra stream `{stream_id}`
- `GET /video/stream` — MJPEG stream for primary
- `GET /video/stream/{stream_id}` — MJPEG stream for a stream id
- `POST /video/zones` — set normalized zones for primary
- `POST /video/zones/{stream_id}` — set zones for a specific stream
- `GET /video/debug/models` — diagnostics for selected model checkpoints

### Alerts (`/alerts/*`)
- `GET /alerts/live` — live/bounded in-memory alerts
- `GET /alerts/analytics` — aggregated analytics + recent alerts
- `POST /alerts/clear` — clear alert store
- `GET /alerts/snapshot/{stream_id}/{date}/{filename}` — serve a saved snapshot JPEG

### History (`/history/*`)
- `GET /history/streams` — streams with local history
- `GET /history/dates?stream_id=...` — dates that have clips for a stream
- `GET /history/clips?stream_id=...&date=YYYY-MM-DD` — list clips for that day
- `GET /history/clip/{stream_id}/{date}/{filename}` — stream a clip (supports Range)
- `DELETE /history/clip/{stream_id}/{date}/{filename}` — delete a clip (+ cached transcode)
- `GET /history/supabase/status` — reports if Supabase is configured/enabled

### Metrics / debug
- `GET /metrics` — system metrics for the dashboard
- `GET /debug/runtime` — runtime + env + model diagnostics

### IoT (`/iot/*`)
- `GET /iot/ping` — basic ping
- `POST /iot/door` — door events (open/closed/tamper), optional shared-secret header

### AI
- `POST /ask` — ask a question about recent alerts (RAG-style)

## Runtime workflow (end-to-end)

1) Frontend starts a stream (webcam or video) → backend `StreamManager` starts a worker.
2) Worker captures frames (OpenCV), resizes, runs YOLO inference.
3) Pipeline applies:
   - Temporal persistence + cooldowns
   - Weapon gating (near-person heuristics, max area ratio, optional verify model)
   - Behavior logic (running/loitering/bag)
   - Zone logic (restricted entry + dwell)
4) Worker emits alerts into the in-memory store.
5) Frontend polls alerts and analytics; Live Feed shows the MJPEG stream.
6) Optional: save snapshots, record rotating clips, upload to Supabase, send Telegram notifications.

Architecture diagrams (PlantUML) live in:
- `docs/architecture/ARCHITECTURE-C4-Container.puml`
- `docs/architecture/PIPELINE-IntentWatch.puml`

## Configuration (high-value environment variables)

### Networking / UI integration
- `INTENTWATCH_BACKEND_HOST`, `INTENTWATCH_BACKEND_PORT` — used by start scripts
- `VITE_API_URL` — frontend → backend base URL (see `Frontend/.env.example`)
- `INTENTWATCH_CORS_ORIGINS` — comma-separated extra CORS origins
- `INTENTWATCH_CORS_ORIGIN_REGEX` — regex override (dev-only option)

### Video sources
- `INTENTWATCH_WEBCAM_URL` — if set, `/video/start-camera` prefers this IP webcam URL
- `INTENTWATCH_CAMERA_DROP_STALE_FRAMES` — drop old frames for live camera latency reduction

### Weapon model selection + tuning
- `INTENTWATCH_WEAPON_MODEL_PATH` — explicit weapon model checkpoint
- `INTENTWATCH_WEAPON_VERIFY_MODEL_PATH` — optional verify model checkpoint
- `INTENTWATCH_WEAPON_ENABLE_FALLBACK`, `INTENTWATCH_WEAPON_FALLBACK_MODEL_PATH` — optional fallback model
- `INTENTWATCH_WEAPON_LABELS` — allowlist (default includes pistol/knife/gun/rifle/weapon/firearm)
- `INTENTWATCH_WEAPON_CONF`, `INTENTWATCH_WEAPON_KNIFE_CONF`, `INTENTWATCH_WEAPON_PERSIST_FRAMES`
- `INTENTWATCH_WEAPON_REARM_SECONDS`, `INTENTWATCH_WEAPON_CLEAR_SECONDS`

### Zones
- `INTENTWATCH_ZONE_DWELL_SECONDS`, `INTENTWATCH_ZONE_COOLDOWN_SECONDS`

### History (clips)
- `INTENTWATCH_HISTORY_ENABLED`
- `INTENTWATCH_HISTORY_CLIP_SECONDS`
- `INTENTWATCH_HISTORY_UPLOAD_SUPABASE`
- `INTENTWATCH_HISTORY_BUCKET`, `INTENTWATCH_HISTORY_TABLE`
- Retention worker: `INTENTWATCH_HISTORY_RETENTION_ENABLED`, `INTENTWATCH_HISTORY_RETENTION_DAYS`, `INTENTWATCH_HISTORY_CLEANUP_INTERVAL_HOURS`

### Snapshots
- `INTENTWATCH_SNAPSHOTS_ENABLED`
- `INTENTWATCH_SNAPSHOT_UPLOAD_SUPABASE`
- `INTENTWATCH_SNAPSHOT_BUCKET`

### Supabase (optional)
- `INTENTWATCH_SUPABASE_ENABLED` (default true)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (preferred) / `SUPABASE_KEY` / `SUPABASE_ANON_KEY`

### Phone alerts (optional)
- `INTENTWATCH_PHONE_ALERTS_ENABLED`
- `INTENTWATCH_PHONE_ALERT_TYPES` (defaults to `weapon,unattended bag`)
- `INTENTWATCH_TELEGRAM_ENABLED`
- `INTENTWATCH_TELEGRAM_BOT_TOKEN`, `INTENTWATCH_TELEGRAM_CHAT_ID`

### RAG / Ask AI (optional)
- `INTENTWATCH_RAG_PROVIDER` (`openai` / `ollama` / empty)
- `OPENAI_API_KEY`, `INTENTWATCH_OPENAI_MODEL`
- `INTENTWATCH_OLLAMA_URL`, `INTENTWATCH_OLLAMA_MODEL`
- `INTENTWATCH_RAG_EMBED_MODEL` (only used if `sentence_transformers` is installed)

## Training workflow (YOLO)

Training entry points in `scripts/`:
- `scripts/train_weapon_types_img800_e60.py` — train weapon-type model with:
  - per-epoch mAP reporting callback
  - `--resume-from` checkpoint support
  - optional `--no-amp` (helpful on GPUs that produce NaN losses)
  - optional mAP-based early stopping (`--map-patience`, `--map-warmup-epochs`)
- `scripts/train_weapon_verify_v8s.py` — train a binary “verify” model (person/weapon)

Output checkpoints are typically under `runs_weapon/<run_name>/weights/{best,last}.pt`.

## Notes / known limitations
- The frontend **Settings** page currently stores preferences in browser localStorage but is not fully wired to backend tuning knobs.
- Embedding-based retrieval for RAG requires installing `sentence_transformers` (not included in `backend/requirements.txt` by default).
- The PlantUML C4 diagram mentions “DeepSORT”, and `deep-sort-realtime` exists in `requirements.txt`, but the current backend tracking logic uses a lightweight in-process approach (no DeepSORT module import).

## Primary docs
- `README.md` — overview + run instructions
- `QUICKSTART.md` — 3-step quick start
- `INTEGRATION.md` — integration details + Supabase + phone alerts

- `docs/IOT_DOOR_SENSOR.md` — ESP8266 door sensor integration
