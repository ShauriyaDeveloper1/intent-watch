# Public Internet Deployment (Vercel Frontend + GPU Backend)

This guide assumes:

- Frontend is deployed to **Vercel** (HTTPS).
- Backend (FastAPI) must be reachable on the **public internet over HTTPS**.
- The YOLO models (`.pt`) are loaded by the backend from local disk paths.

## What to deploy where

### Frontend

- Deploy the `Frontend/` project to Vercel.
- Set `VITE_API_URL` in Vercel project env vars to your backend public origin, for example:
  - `https://api.yourdomain.com`

### Backend + AI models (recommended: same machine)

The backend process runs the AI inference in-process, so you deploy them together.

Recommended platform:

- **Linux GPU VM** (Ubuntu 22.04/24.04) with an **NVIDIA GPU**.

Why:

- Real-time YOLO + MJPEG streaming needs a long-running process.
- Public PaaS platforms (Vercel/Netlify/etc.) do not provide CUDA GPUs for Python inference.

Common choices:

- Azure GPU VM, AWS GPU instance, GCP GPU VM, or a GPU hosting provider.

## Minimum production checklist

- HTTPS in front of backend (no mixed-content issues with Vercel)
- Restrict CORS to your Vercel domain
- Some form of access control (API key / Basic Auth / Cloudflare Access)
- Persistent disk for `backend/data/` (history/snapshots)

## Step-by-step: GPU VM (Ubuntu) + Caddy (HTTPS reverse proxy)

### 1) VM prerequisites

- Install NVIDIA drivers and confirm GPU is visible:

```bash
nvidia-smi
```

### 2) Copy the repo onto the VM

Use `git clone` or upload the project folder.

### 3) Install backend dependencies in a venv

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# GPU build of PyTorch + pinned deps
python -m pip install -r backend/requirements-gpu-cu124.txt
```

Notes:

- `backend/requirements-gpu-cu124.txt` installs CUDA wheels from the PyTorch CUDA index.
- Ensure the VM’s NVIDIA driver supports CUDA 12.4 runtime.

### 4) Place your trained model weights on the VM

This repo ships `backend/yolov8n.pt` (main model).

For weapon-type alerts, you must also deploy a trained `best.pt` (from your training outputs). You have two options:

Option A (keep training outputs):

- Copy your `runs/` and/or `runs_weapon/` folders to the VM.

Option B (cleaner):

- Copy the specific weight files to a dedicated folder (recommended), e.g. `models/weapon/best.pt`.

Then set:

- `INTENTWATCH_WEAPON_MODEL_PATH=/absolute/path/to/best.pt`
- Optional: `INTENTWATCH_WEAPON_VERIFY_MODEL_PATH=/absolute/path/to/verify/best.pt`

### 5) Configure CORS for your Vercel frontend

Set one of:

- `INTENTWATCH_CORS_ORIGINS=https://your-vercel-app.vercel.app`

or dev-only wildcard:

- `INTENTWATCH_CORS_ORIGIN_REGEX=.*`

### 6) Run the backend on localhost (behind a reverse proxy)

Example:

```bash
source .venv/bin/activate
cd backend
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 7) Add HTTPS with Caddy

Install Caddy and create `/etc/caddy/Caddyfile`:

```caddyfile
api.yourdomain.com {
  reverse_proxy 127.0.0.1:8000
}
```

Caddy will automatically request a Let’s Encrypt certificate (your DNS must point to the VM).

### 8) Point Vercel frontend to backend

In Vercel:

- `VITE_API_URL = https://api.yourdomain.com`

Redeploy the frontend.

## Optional: basic access control (recommended)

Since the backend is public, you should protect it.

Easy options:

- Put Basic Auth in Caddy
- Use Cloudflare Tunnel + Cloudflare Access
- Add an API key check at the reverse proxy layer

## Troubleshooting

### MJPEG stream doesn’t load on the public site

- Backend must be HTTPS (Vercel site is HTTPS; browsers block HTTP mixed content).
- Ensure CORS includes your Vercel origin.

### Weapon type doesn’t show for uploaded videos

- Confirm CUDA is available on the VM: `python -c "import torch; print(torch.cuda.is_available())"`
- Ensure `INTENTWATCH_WEAPON_MODEL_PATH` points to the trained weapon model.

### Uploads fail on large videos

- Configure your reverse proxy upload/body-size limits (platform-specific).

## Hackathon notes (fastest reliable demo)

- CPU-only free tiers (like typical Azure Student B-series) can run the backend, but real-time inference will be slow and choppy.
- If you already have a local NVIDIA laptop/PC, the simplest path is:
  - Run the backend on the GPU machine.
  - Expose it over HTTPS using **Cloudflare Tunnel** (or another tunnel) so the Vercel site can call it without mixed-content.
  - Set `VITE_API_URL` on Vercel to the tunnel HTTPS URL.
- If you need everything in the cloud, use a **short-lived GPU VM** for the demo window.

## Option: Local GPU backend + Cloudflare Tunnel (Windows)

This is the recommended hackathon deployment when you have a local NVIDIA machine.

### 1) Run the backend locally

From the repo root (PowerShell):

```powershell
Set-Location D:\intent-watch

# Allow the Vercel frontend origin (replace with your Vercel domain)
$env:INTENTWATCH_CORS_ORIGINS = "https://YOUR-VERCEL-APP.vercel.app"

./start-backend.ps1
```

Confirm it works locally:

- Open `http://127.0.0.1:8000/` and check you see JSON.

### 2) Install and start Cloudflare Tunnel

Install `cloudflared` (pick one):

- Winget:

```powershell
winget install --id Cloudflare.cloudflared -e
```

- Or download from Cloudflare and place `cloudflared.exe` on your PATH.

Quick tunnel (no DNS, temporary URL):

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

This prints a public HTTPS URL like `https://<random>.trycloudflare.com`.

### 3) Point Vercel to the tunnel URL

In your Vercel project env vars:

- `VITE_API_URL = https://<random>.trycloudflare.com`

Redeploy the frontend.

### 4) Stable URL (optional, recommended for anything beyond a demo)

If you want a stable custom subdomain like `https://api.yourdomain.com`, create a **named tunnel** in Cloudflare Zero Trust, map DNS to it, and configure it to forward to `http://127.0.0.1:8000`.

Notes:

- If you change your Vercel domain, update `INTENTWATCH_CORS_ORIGINS` accordingly.
- Keep the tunnel running while your demo is live.

## Accuracy / false-positive tuning

These are quick knobs that help for demos without retraining:

- Weapon false positives
  - Keep weapon verification enabled (`INTENTWATCH_WEAPON_VERIFY_REQUIRED=1`).
  - Raise weapon thresholds if needed (project already defaults to stricter verification than earlier versions).
- Unattended bag sensitivity
  - Lower `INTENTWATCH_PERSON_BAG_DISTANCE_PX` if bags are incorrectly considered “attended”.
  - Raise `INTENTWATCH_BAG_THRESHOLD_SECONDS` to reduce transient alerts.
  - If the suitcase/bag detection flickers, `INTENTWATCH_BAG_MISSING_GRACE_SECONDS` lets the timer survive brief dropouts.
- Zone alerts
  - Use `severity=high` or `critical` for restricted zones (these emit immediate “restricted zone entry” alerts + snapshots).
  - Use `severity=medium/low` for monitoring zones (dwell-based alerts).

---

## Quick reference env vars

- `VITE_API_URL` (Vercel)
- `INTENTWATCH_CORS_ORIGINS` or `INTENTWATCH_CORS_ORIGIN_REGEX`
- `INTENTWATCH_WEAPON_MODEL_PATH`
- `INTENTWATCH_WEAPON_VERIFY_MODEL_PATH` (optional)
- `INTENTWATCH_WEAPON_VERIFY_REQUIRED` (1/0)
- `INTENTWATCH_BAG_THRESHOLD_SECONDS`
- `INTENTWATCH_PERSON_BAG_DISTANCE_PX`
- `INTENTWATCH_BAG_MISSING_GRACE_SECONDS`
- `INTENTWATCH_ZONE_DWELL_SECONDS`
- `INTENTWATCH_SNAPSHOTS_ENABLED`
