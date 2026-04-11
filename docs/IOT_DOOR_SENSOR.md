# IoT Door Sensor (ESP8266 + Reed Switch) → IntentWatch

This guide connects a simple door sensor (reed switch) to the IntentWatch backend so it can generate alerts + (optionally) phone notifications.

## What you built
- ESP8266 (NodeMCU / Wemos D1 mini) reads a door reed switch.
- On door open/close/tamper, it sends an HTTP `POST` to the backend at `/iot/door`.
- The backend converts that event into an IntentWatch alert (`type=door`).

## 1) Backend: enable LAN access
Your ESP8266 must reach the backend over WiFi.

- Start backend with host `0.0.0.0` (not `127.0.0.1`).

PowerShell (example):

```powershell
$env:INTENTWATCH_BACKEND_HOST = "0.0.0.0"
$env:INTENTWATCH_BACKEND_PORT = "8000"
.\start-backend.ps1
```

- Find your PC LAN IP (example `192.168.1.50`) and use that in the ESP8266 firmware.

### CORS note (when opening the UI from another device)
If you open the frontend from your phone (e.g. `http://192.168.1.50:5173`), the backend must allow that origin.

Quick dev-only option:

```powershell
$env:INTENTWATCH_CORS_ORIGIN_REGEX = ".*"
```

## 2) Backend: active-hours schedule (optional)
If you only want alerts at night:

```powershell
$env:INTENTWATCH_IOT_ACTIVE_START = "22:00"
$env:INTENTWATCH_IOT_ACTIVE_END   = "06:00"
```

If you don’t set these, IoT alerting is always active.

## 3) Backend: simple security (recommended)
Set a shared secret so only your ESP8266 can post events:

```powershell
$env:INTENTWATCH_IOT_SHARED_SECRET = "change-me-to-a-random-string"
```

The ESP8266 will send it in `X-IoT-Key`.

## 4) Phone notifications (works without the buzzer)
IntentWatch already supports Telegram notifications.

Set:

```powershell
$env:INTENTWATCH_PHONE_ALERTS_ENABLED = "true"
$env:INTENTWATCH_PHONE_ALERT_TYPES   = "door,weapon,unattended bag"

$env:INTENTWATCH_TELEGRAM_ENABLED    = "true"
$env:INTENTWATCH_TELEGRAM_BOT_TOKEN  = "<your-bot-token>"
$env:INTENTWATCH_TELEGRAM_CHAT_ID    = "<your-chat-id>"
```

Now your phone will usually play a notification sound via Telegram — no hardware buzzer needed.

### Website-notification note
The frontend also supports browser notifications, but many mobile browsers only allow notifications on **HTTPS** origins (secure context). For local WiFi testing on `http://<LAN-IP>:5173`, notifications may be blocked by the browser.

For reliable phone notifications from the website, you typically need:
- HTTPS (deploy to a domain, or use a tunnel like ngrok/cloudflared), and later
- Web Push (PWA) if you want notifications while the site is closed.

## 5) Wiring (no buzzer)
### Reed switch → ESP8266 (recommended)
- One wire of reed switch → `D2` (GPIO4)
- Other wire → `GND`

In firmware we use `INPUT_PULLUP`, so:
- door **closed**: pin reads `LOW` (circuit closed)
- door **open**: pin reads `HIGH`

Tip: if your sensor behaves opposite, just invert the logic.

### “Alarm” feedback without a buzzer
- Use the onboard LED (`LED_BUILTIN`) to blink when the door opens.

## 6) ESP8266 firmware (Arduino IDE)
### Arduino IDE setup
- Install **ESP8266 board support** (Boards Manager)
- Select board: **NodeMCU 1.0 (ESP-12E Module)**

### Example firmware
Replace:
- `WIFI_SSID`, `WIFI_PASS`
- `BACKEND_HOST` (your PC LAN IP)
- `IOT_KEY` (same as `INTENTWATCH_IOT_SHARED_SECRET`)

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// --- USER CONFIG ---
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

const char* BACKEND_HOST = "192.168.1.50";  // your PC LAN IP
const int   BACKEND_PORT = 8000;

const char* DEVICE_ID = "door-1";
const char* IOT_KEY   = "change-me-to-a-random-string"; // must match backend env

// --- PINS ---
const int REED_PIN = D2; // GPIO4

// NodeMCU built-in LED is usually active LOW
#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

static bool lastDoorOpen = false;
static unsigned long lastPostMs = 0;

bool isDoorOpen() {
  // With INPUT_PULLUP and reed wired to GND: open => HIGH
  int v = digitalRead(REED_PIN);
  return (v == HIGH);
}

void blinkLed(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_BUILTIN, LOW);
    delay(120);
    digitalWrite(LED_BUILTIN, HIGH);
    delay(120);
  }
}

bool postDoorState(const char* state) {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClient client;
  HTTPClient http;

  String url = String("http://") + BACKEND_HOST + ":" + BACKEND_PORT + "/iot/door";

  if (!http.begin(client, url)) return false;

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-IoT-Key", IOT_KEY);

  String body = String("{\"device_id\":\"") + DEVICE_ID + "\",\"state\":\"" + state + "\",\"rssi\":" + String(WiFi.RSSI()) + "}";

  int code = http.POST(body);
  http.end();

  return (code >= 200 && code < 300);
}

void setup() {
  pinMode(REED_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    blinkLed(1);
  }

  blinkLed(3);
  lastDoorOpen = isDoorOpen();
}

void loop() {
  bool openNow = isDoorOpen();

  // Debounce: only act when state changes and at least 500ms since last post
  unsigned long now = millis();
  if (openNow != lastDoorOpen && (now - lastPostMs) > 500) {
    lastPostMs = now;
    lastDoorOpen = openNow;

    if (openNow) {
      blinkLed(5);
      postDoorState("open");
    } else {
      blinkLed(2);
      postDoorState("closed");
    }
  }

  delay(50);
}
```

## 7) Test quickly
1) Start backend.
2) Open in browser:
- `http://<PC_LAN_IP>:8000/iot/ping`
3) Trigger sensor and watch backend logs + `/alerts/live`.

---

### Files involved
- Backend route: `backend/api/routes/iot.py`
- Alerts storage + phone notify: `backend/api/routes/alerts.py`, `backend/api/phone_notify.py`
