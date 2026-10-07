# IntentWatch

**IntentWatch** is a local-first, full-stack AI surveillance platform for monitoring live camera feeds and uploaded videos. It combines a FastAPI backend, OpenCV video processing, Ultralytics YOLO inference, and a React dashboard to detect suspicious activity, generate alerts, record evidence, and review security events.

> **Project status:** Active development. IntentWatch is intended for education, prototyping, and controlled security experiments. It should not be treated as a replacement for trained security personnel or a certified safety system.

## Highlights

- **Real-time video monitoring** from a local webcam, uploaded video, or IP/network camera source.
- **YOLO-powered detection** with support for a general model and optional dedicated weapon models.
- **Behavior and intent signals** including weapon detection, unattended bags, running, loitering, restricted-zone entry, zone dwell, and IoT door events.
- **Live MJPEG streaming** with detection overlays through the browser dashboard.
- **Alert management** with severity, camera/stream metadata, cooldowns, snapshots, analytics, and browser notifications.
- **Multi-stream support** with a primary stream and dynamically managed additional streams.
- **Local history recording** with rotating clips, browser playback, Range request support, and optional WebM transcoding.
- **Optional Supabase integration** for storing recorded clips, snapshots, and clip metadata.
- **Optional Telegram notifications** for selected high-priority alerts.
- **Ask AI** endpoint for questions about recent in-memory alerts using lexical or embedding retrieval and optional OpenAI/Ollama generation.
- **Zone configuration** from the frontend using normalized coordinates.
- **Demo inference tools** for testing image detection without starting a real-time stream.

## Architecture

```text
Camera / video file / IP webcam
              │
              ▼
     OpenCV capture pipeline
              │
              ▼
       StreamManager worker
       ├── YOLO object detection
       ├── behavior and zone rules
       ├── alert cooldowns/persistence
       ├── snapshots and history clips
       └── optional Supabase/Telegram integrations
              │
              ▼
          FastAPI backend
       REST API + MJPEG streams
              │
              ▼
       React + Vite dashboard
  live feed · alerts · analytics · history
  zones · settings · Ask AI
```

The frontend starts and controls streams through the typed API client in `Frontend/src/services/api.ts`. The backend routes requests to `StreamManager`, which captures frames, runs inference, applies temporal and spatial rules, stores recent alerts in memory, and exposes the resulting stream and metadata to the dashboard.

## Technology stack

### Backend

- Python
- FastAPI and Uvicorn
- OpenCV for capture, encoding, recording, and playback
- Ultralytics YOLOv8 and PyTorch/Torchvision
- NumPy
- `python-dotenv` for environment configuration
- Optional Supabase client and Telegram notifications

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Radix UI and Material UI components/icons
- Recharts for analytics
- Framer Motion for page transitions
- React Router

## Repository layout

```text
intent-watch/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app, CORS, environment loading, routers
│   │   ├── stream_manager.py    # Capture, inference, alerts, snapshots, history
│   │   ├── rag.py               # Recent-alert retrieval and answer generation
│   │   ├── phone_notify.py      # Optional Telegram forwarding
│   │   └── routes/
│   │       ├── video.py         # Video sources, streams, and zones
│   │       ├── alerts.py        # Live alerts, analytics, snapshots
│   │       ├── history.py       # Recorded clips and retention
│   │       ├── metrics.py       # Runtime dashboard metrics
│   │       ├── iot.py           # Door sensor and IoT endpoints
│   │       ├── ask.py           # Ask AI endpoint
│   │       └── demo.py          # Demo image inference endpoints
│   ├── data/                    # Local videos, history clips, and snapshots
│   ├── yolov8n.pt               # Default YOLO checkpoint
│   ├── requirements.txt         # Pinned backend dependencies
│   ├── requirements-gpu-cu124.txt
│   └── requirements-rag.txt     # Optional RAG dependencies
├── Frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/           # Dashboard, feed, alerts, history, zones, settings
│   │   │   └── components/      # Layout and reusable UI components
│   │   └── services/
│   │       ├── api.ts           # Typed backend API client
│   │       └── alertNotifications.ts
│   └── package.json
├── scripts/                     # YOLO dataset validation and training tools
├── tools/                       # Small video/model sanity utilities
├── docs/                        # Deployment, IoT, and architecture documentation
├── .env.example                 # Backend environment template
├── setup.ps1                    # First-time Windows setup
├── start-backend.ps1            # Start FastAPI only
├── start-frontend.ps1           # Start Vite only
├── start-intentwatch.ps1        # Start both services
├── QUICKSTART.md                # Short setup guide
└── INTEGRATION.md               # Detailed integration notes
```

## Requirements

- Windows PowerShell for the included `.ps1` scripts
- Python 3.8 or newer; Python 3.10+ is recommended for current ML dependencies
- Node.js 16 or newer; Node.js 18+ is recommended
- npm
- A webcam, IP camera, or video file for testing
- Optional NVIDIA GPU and compatible CUDA/PyTorch installation for faster inference

## Quick start on Windows

### 1. Clone and enter the repository

```powershell
git clone https://github.com/ShauriyaDeveloper1/intent-watch.git
cd intent-watch
```

### 2. Run the setup script

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

The script creates `venv`, installs the root Python requirements, and installs the frontend dependencies.

### 3. Configure environment variables

For local development, copy the backend template:

```powershell
Copy-Item .env.example .env
```

The frontend defaults to `http://localhost:8000`. To override it, create `Frontend/.env`:

```dotenv
VITE_API_URL=http://localhost:8000
```

Leave optional integrations disabled unless you have configured their credentials.

### 4. Start the application

```powershell
.\start-intentwatch.ps1
```

The launcher opens separate terminal windows for:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- Swagger API docs: <http://localhost:8000/docs>
- ReDoc API docs: <http://localhost:8000/redoc>

To stop the application, close the backend and frontend terminal windows.

## Manual startup

If you prefer separate terminals:

### Backend

```powershell
.\venv\Scripts\Activate.ps1
uvicorn api.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd Frontend
npm run dev
```

Build the frontend for a production bundle with:

```powershell
cd Frontend
npm run build
```

## Using the dashboard

1. Open <http://localhost:5173>.
2. Use **Live Feed** to start a webcam, network camera, uploaded video, or additional stream.
3. Review detections and live alerts alongside the MJPEG stream.
4. Use **Alerts** to search, filter, inspect, and clear recent alerts.
5. Use **Analytics** and **Dashboard** to view alert trends and runtime metrics.
6. Use **History** to browse and play locally recorded clips.
7. Use **Zones** to define normalized restricted areas and dwell rules.
8. Use **Settings** to manage local dashboard preferences.
9. Use **Ask AI** when enabled to query the recent alert store.

### Testing with a video file

From **Live Feed**, upload a supported video file. The backend saves the upload, makes it the active stream, and processes it through the same inference pipeline used for live sources.

### Testing alert rules

Results depend on the selected model, camera angle, lighting, and configured thresholds. For controlled testing, use scenarios such as:

- A person remaining stationary to exercise loitering logic.
- Fast movement across the frame to exercise running detection.
- An object left unattended to exercise bag persistence logic.
- A person entering or remaining inside a configured zone.
- A compatible weapon checkpoint for weapon detection.

## Backend API overview

The complete and current API contract is available at `/docs` while the backend is running.

| Area | Method | Endpoint | Purpose |
| --- | --- | --- | --- |
| Health | `GET` | `/` | Backend status |
| Video | `POST` | `/video/upload` | Upload and process a video |
| Video | `POST` | `/video/start-camera` | Start the webcam/IP camera |
| Video | `POST` | `/video/start` | Start a stream from a source |
| Video | `POST` | `/video/stop` | Stop the primary stream |
| Video | `GET` | `/video/status` | Get primary stream status |
| Video | `GET` | `/video/streams` | List known streams |
| Video | `POST` | `/video/streams/start` | Start an additional stream |
| Video | `POST` | `/video/streams/stop` | Stop an additional stream |
| Video | `GET` | `/video/stream` | Primary MJPEG stream |
| Video | `GET` | `/video/stream/{stream_id}` | Stream-specific MJPEG feed |
| Zones | `POST` | `/video/zones` | Configure primary-stream zones |
| Alerts | `GET` | `/alerts/live` | Retrieve recent alerts |
| Alerts | `GET` | `/alerts/analytics` | Retrieve aggregated alert analytics |
| Alerts | `POST` | `/alerts/clear` | Clear the in-memory alert store |
| Alerts | `GET` | `/alerts/snapshot/{stream_id}/{date}/{filename}` | Retrieve an alert snapshot |
| History | `GET` | `/history/streams` | List streams with recorded history |
| History | `GET` | `/history/dates` | List recording dates |
| History | `GET` | `/history/clips` | List clips for a date |
| History | `GET` | `/history/clip/{stream_id}/{date}/{filename}` | Play a recorded clip |
| History | `DELETE` | `/history/clip/{stream_id}/{date}/{filename}` | Delete a recorded clip |
| Metrics | `GET` | `/metrics` | Dashboard/runtime metrics |
| IoT | `GET` | `/iot/ping` | Check IoT integration |
| IoT | `POST` | `/iot/door` | Submit door open/closed/tamper events |
| AI | `POST` | `/ask` | Ask about recent alerts |
| Demo | `POST` | `/demo/warmup` | Warm up the demo model |
| Demo | `POST` | `/demo/detect-image` | Run image detection without streaming |

## Configuration

The main configuration template is `.env.example`. Important options include:

### Camera and stream processing

```dotenv
INTENTWATCH_WEBCAM_URL=http://10.12.26.111:8080
INTENTWATCH_CAMERA_DROP_STALE_FRAMES=1
INTENTWATCH_FILE_REALTIME=1
```

`INTENTWATCH_WEBCAM_URL` can be a full URL or a `host:port` value for a compatible IP webcam. The stale-frame option favors low latency by processing the newest frame when inference falls behind.

### History and snapshots

```dotenv
INTENTWATCH_HISTORY_ENABLED=1
INTENTWATCH_HISTORY_CLIP_SECONDS=60
INTENTWATCH_SNAPSHOTS_ENABLED=1
```

Local history is stored below `backend/data/history/`, while alert snapshots are stored below the backend snapshot data directory. These artifacts may contain sensitive video and should be protected appropriately.

### Weapon models

```dotenv
INTENTWATCH_WEAPON_MODEL_PATH=D:/intent-watch/runs_weapon/weapon80_20/weights/best.pt
INTENTWATCH_WEAPON_VERIFY_MODEL_PATH=
INTENTWATCH_WEAPON_CONF=0.75
INTENTWATCH_WEAPON_PERSIST_FRAMES=2
INTENTWATCH_WEAPON_REARM_SECONDS=20
```

The repository includes a default `backend/yolov8n.pt` checkpoint. Dedicated weapon checkpoints are optional and can be produced by the training scripts in `scripts/`.

### Optional Supabase storage

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<backend-only-key>
INTENTWATCH_HISTORY_UPLOAD_SUPABASE=1
INTENTWATCH_HISTORY_BUCKET=footages
INTENTWATCH_SNAPSHOT_UPLOAD_SUPABASE=1
INTENTWATCH_SNAPSHOT_BUCKET=Snapshots
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` in the frontend or commit it to Git. See `INTEGRATION.md` for the optional `footage_clips` metadata table and storage setup.

### Optional Telegram alerts

```dotenv
INTENTWATCH_TELEGRAM_ENABLED=1
INTENTWATCH_TELEGRAM_BOT_TOKEN=<bot-token>
INTENTWATCH_TELEGRAM_CHAT_ID=<chat-id>
INTENTWATCH_PHONE_ALERT_TYPES=weapon,unattended bag
```

Telegram forwarding is opt-in and should be configured only on the backend.

### Ask AI RAG flow (optional)

The `POST /ask` endpoint uses an optional retrieval-augmented flow around recent backend context:

- **Retrieved context:** a snapshot of recent in-memory alerts (up to `max_alerts`, default 1000). For questions mentioning history clips/video/footage, recent local history clip metadata is also appended.
- **Retrieval strategy:** in-memory top-`k` retrieval (default 5) using embedding similarity when `sentence-transformers` is installed (`backend/requirements-rag.txt`), otherwise lexical overlap scoring. If retrieval returns no matches but alerts exist, it falls back to the most recent alerts.
- **Answer generation:** optional provider-based generation with OpenAI or Ollama; if no provider response is available, the endpoint returns an extractive answer built directly from retrieved alert context.

### Optional Ask AI providers

```dotenv
INTENTWATCH_RAG_PROVIDER=openai
OPENAI_API_KEY=<key>
INTENTWATCH_OPENAI_MODEL=<model>
```

Alternatively, configure Ollama with `INTENTWATCH_RAG_PROVIDER=ollama`, `INTENTWATCH_OLLAMA_URL`, and `INTENTWATCH_OLLAMA_MODEL`. Without an external provider, the endpoint can return an extractive answer based on recent alerts. Embedding retrieval requires the optional dependencies in `backend/requirements-rag.txt`.

## Model training and dataset utilities

The `scripts/` directory includes utilities for validating YOLO labels, inspecting dataset statistics, preparing train/validation splits, checking label quality, and training weapon detection/verification models.

Examples:

```powershell
python scripts/dataset_stats.py
python scripts/validate_dataset.py
python scripts/train_weapon_types_img800_e60.py --help
python scripts/train_weapon_verify_v8s.py --help
```

Training outputs are typically written under `runs_weapon/<run_name>/weights/`. Keep large datasets and generated checkpoints out of commits unless they are intentionally part of the project.

## Documentation

- [`QUICKSTART.md`](QUICKSTART.md) — short setup and troubleshooting guide
- [`INTEGRATION.md`](INTEGRATION.md) — frontend/backend integration, Supabase, history, and Telegram details
- [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) — implementation inventory and API map
- [`docs/IOT_DOOR_SENSOR.md`](docs/IOT_DOOR_SENSOR.md) — ESP8266/reed-switch door sensor integration
- [`docs/DEPLOY_PUBLIC.md`](docs/DEPLOY_PUBLIC.md) — public deployment notes
- [`docs/architecture/`](docs/architecture/) — PlantUML architecture diagrams

## Troubleshooting

### PowerShell blocks scripts

Run the following in the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### Backend imports fail

Activate the virtual environment and reinstall dependencies:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend dependencies are missing

```powershell
cd Frontend
npm install
npm run dev
```

### Frontend cannot reach the backend

- Confirm the backend is running at `http://localhost:8000`.
- Check `Frontend/.env` and `VITE_API_URL`.
- Review browser developer tools for failed requests or CORS errors.
- Review the backend terminal and `/docs` for route availability.

### Video or model loading fails

- Confirm the camera or uploaded file is accessible.
- Verify that `backend/yolov8n.pt` or the configured custom checkpoint exists.
- Try a smaller input video or lower resolution.
- Use the GPU-specific requirements file only with a compatible CUDA/PyTorch setup.

### Ports are already in use

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force
```

## Security and privacy notes

- Keep camera URLs, Supabase service-role keys, Telegram tokens, and API keys out of source control.
- Treat local recordings and snapshots as sensitive data.
- Restrict public deployment with authentication, HTTPS, network controls, and appropriate retention policies before exposing the system to untrusted users.
- AI detections are probabilistic; validate alerts before taking consequential action.
- Obtain consent and follow applicable laws and organizational policies when recording or analyzing people.

## Contributing

1. Create a feature branch.
2. Keep secrets, generated recordings, datasets, and model outputs out of commits unless intentionally required.
3. Update the relevant documentation when changing API routes or environment variables.
4. Test the backend and frontend locally.
5. Open a pull request with a clear description of the change.

## License

This project is available under the [MIT License](LICENSE).

---

Built with Python, FastAPI, React, TypeScript, OpenCV, and YOLOv8.
