# IntentWatch — Demo Deployment (Vercel + Colab + ngrok)

Target architecture:

Frontend (Vercel)
→ Backend API (Google Colab + ngrok)
→ YOLO inference (GPU in Colab)
→ IoT device (ESP8266 → `POST /iot/door`)

This setup is designed for a reliable, repeatable demo.

---

## 0) One-time accounts / keys

- Create an ngrok account and copy your **auth token**.
- (Optional) If you want IoT authentication: pick a shared secret for `INTENTWATCH_IOT_SHARED_SECRET`.

---

## 1) Backend on Colab (recommended demo-safe mode)

### A. Start a new Colab notebook

- Runtime → Change runtime type → **GPU**.

### B. Clone the repo

In a Colab cell:

```bash
!git clone https://github.com/Sarthak1Developer/intent-watch.git
%cd intent-watch
```

If your repo is private, use a GitHub token or upload a zip.

### C. Install Colab-friendly dependencies

```bash
!pip install -r deploy/colab/requirements-colab.txt
```

Notes:
- This file intentionally **does not** pin/install `torch` so you keep Colab’s CUDA torch.

### D. Configure demo mode environment variables

```python
import os
from pathlib import Path

repo_root = Path.cwd()  # should be /content/intent-watch after the git clone + %cd

# Critical: disables heavy real-time streaming endpoints for demo reliability
os.environ["INTENTWATCH_DEMO_MODE"] = "1"

# OPTIONAL (recommended if you know the exact checkpoint): set an ABSOLUTE model path.
# If you skip this, the backend will auto-detect the newest best.pt under runs_weapon/ or runs/detect/.
#
# Example (adjust run name to yours):
# model_path = (repo_root / "runs" / "detect" / "runs_weapon" / "combined_yolov8s_gpu" / "weights" / "best.pt").resolve()
# os.environ["INTENTWATCH_DEMO_MODEL_PATH"] = str(model_path)

# Force GPU if available
os.environ["INTENTWATCH_DEMO_DEVICE"] = "0"

# Allow your Vercel frontend origin (set this after you deploy Vercel)
# os.environ["INTENTWATCH_CORS_ORIGINS"] = "https://YOUR-VERCEL-DOMAIN.vercel.app"

# Optional: protect IoT endpoint
# os.environ["INTENTWATCH_IOT_SHARED_SECRET"] = "YOUR_SECRET"
```

### E. Start the FastAPI backend in the notebook (non-blocking)

```python
import threading
import uvicorn


def run_api():
    # Run from backend/ so module paths match how the repo starts locally
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, log_level="info")

# Important: change into backend first
%cd backend

threading.Thread(target=run_api, daemon=True).start()
```

### F. Start ngrok and get the public URL

```python
from pyngrok import ngrok

# Paste your token once
ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN")

public_url = ngrok.connect(8000, bind_tls=True).public_url
print("ngrok URL:", public_url)
```

### G. Warm up the model (removes first-call lag)

```python
import requests

print(requests.post(f"{public_url}/demo/warmup").json())
```

At this point your backend is ready.

---

## 2) Frontend on Vercel

### A. Deploy

- Import the repo into Vercel.
- Set the **Root Directory** to `Frontend/`.

### B. Set the backend URL

In Vercel Project → Settings → Environment Variables:

- `VITE_API_URL` = `https://YOUR-NGROK-SUBDOMAIN.ngrok-free.app`

Redeploy.

### C. CORS (backend)

In Colab, set:

```python
import os
os.environ["INTENTWATCH_CORS_ORIGINS"] = "https://YOUR-VERCEL-DOMAIN.vercel.app"
```

If you change CORS, restart the backend thread (simplest: restart the Colab runtime).

---

## 3) Demo flow (the “judge-proof” script)

1) Open your Vercel site (Dashboard).
2) Use **Demo: Upload Image**.
   - The UI calls `POST /demo/detect-image`.
   - Backend saves an annotated snapshot and emits an alert.
3) Show **Recent Alerts** updating.
4) Show **Analytics** charts updating.
5) Trigger IoT event (door open) and show a `door` alert.

Why this is stable:
- No webcam loop.
- No multi-stream.
- Inference runs only when you upload an image / short clip.

Optional short-video demo:
- Call `POST /demo/detect-video` (not wired in UI by default).

---

## 4) IoT (ESP8266 → `POST /iot/door`)

The backend expects JSON:

```json
{ "state": "open", "device_id": "door-1" }
```

If `INTENTWATCH_IOT_SHARED_SECRET` is set, include header:

- `X-IOT-KEY: YOUR_SECRET`

### ESP8266 example (HTTPS ngrok)

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>

const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASS";

const char* server = "https://YOUR_NGROK_URL/iot/door";
const char* iotKey = "YOUR_SECRET"; // optional (only if backend secret enabled)

int sensorPin = D1;

void setup() {
  Serial.begin(115200);
  pinMode(sensorPin, INPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void loop() {
  if (digitalRead(sensorPin) == HIGH) {
    if (WiFi.status() == WL_CONNECTED) {
      std::unique_ptr<BearSSL::WiFiClientSecure> client(new BearSSL::WiFiClientSecure);
      client->setInsecure(); // demo-only; for production use cert pinning

      HTTPClient http;
      http.begin(*client, server);
      http.addHeader("Content-Type", "application/json");

      // Only send this header if you enabled INTENTWATCH_IOT_SHARED_SECRET
      // http.addHeader("X-IOT-KEY", iotKey);

      String payload = "{\"state\":\"open\",\"device_id\":\"door-1\"}";
      int code = http.POST(payload);
      Serial.println(code);
      http.end();
    }

    delay(5000); // cooldown
  }
}
```

---

## 5) Useful endpoints (demo mode)

- `POST /demo/warmup` — load model + run 1 inference
- `POST /demo/detect-image` — image upload inference (+ emits an alert)
- `POST /demo/detect-video` — short video inference (+ emits an alert)
- `POST /iot/door` — IoT alerts
- `GET /alerts/live`, `GET /alerts/analytics` — dashboard updates
- `GET /docs` — Swagger UI
