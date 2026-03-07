import cv2
import time
import math
import sqlite3
import threading
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from playsound import playsound

# =========================
# VIDEO SOURCE SELECTION
# =========================
print("Select input source:")
print("1 - Live Camera")
print("2 - CCTV Video File")

choice = input("Enter choice (1 or 2): ").strip()

if choice == "1":
    VIDEO_SOURCE = 0
elif choice == "2":
    VIDEO_SOURCE = input("Enter path to CCTV video file: ").strip()
else:
    print("Invalid choice. Defaulting to live camera.")
    VIDEO_SOURCE = 0

RUNNING_SPEED = 150.0       # pixels / second (webcam friendly)
LOITER_TIME = 5.0           # seconds (demo friendly)
ALERT_COOLDOWN = 3.0        # seconds

BAG_CLASSES = {"backpack", "handbag", "suitcase"}
WEAPON_CLASSES = {"knife", "gun"}

ALERT_SOUND = "alert.wav"   # optional

# =========================
# DATABASE (ALERT LOGS)
# =========================
conn = sqlite3.connect("alerts.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    time TEXT,
    person_id INTEGER,
    intent TEXT
)
""")
conn.commit()

# =========================
# MODELS
# =========================
detector = YOLO("yolov8n.pt")
tracker = DeepSort(max_age=30)

# =========================
# TRACK MEMORY
# =========================
track_history = {}

# =========================
# ALERT FUNCTION
# =========================
def raise_alert(person_id, intent):
    print(f"[ALERT] Person {person_id} → {intent}")

    try:
        threading.Thread(
            target=playsound,
            args=(ALERT_SOUND,),
            daemon=True
        ).start()
    except:
        pass

    cursor.execute(
        "INSERT INTO alerts VALUES (?,?,?)",
        (time.strftime("%H:%M:%S"), person_id, intent)
    )
    conn.commit()

# =========================
# INTENT ENGINE
# =========================
def infer_intent(has_bag, has_weapon, loitering, speed):
    if has_weapon and speed > RUNNING_SPEED:
        return "POSSIBLE ATTACK"
    elif has_bag and loitering:
        return "SUSPICIOUS OBJECT"
    elif loitering:
        return "LOITERING"
    elif speed > RUNNING_SPEED:
        return "RUNNING"
    return "NORMAL"

# =========================
# VIDEO
# =========================
cap = cv2.VideoCapture(VIDEO_SOURCE)

print("[INFO] IntentWatch started")

# =========================
# MAIN LOOP
# =========================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape

    # -------------------------
    # YOLO DETECTION
    # -------------------------
    results = detector(frame, verbose=False)[0]
    detections = []
    detected_objects = set()

    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label = detector.names[cls]

        if conf < 0.4:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        detected_objects.add(label)

        if label == "person":
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, label))

        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(frame, label, (x1, y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

    # -------------------------
    # OBJECT FLAGS
    # -------------------------
    has_bag = any(obj in BAG_CLASSES for obj in detected_objects)
    has_weapon = any(obj in WEAPON_CLASSES for obj in detected_objects)

    # -------------------------
    # TRACKING
    # -------------------------
    tracks = tracker.update_tracks(detections, frame=frame)

    for track in tracks:
        if not track.is_confirmed():
            continue

        tid = track.track_id
        l, t, r, b = map(int, track.to_ltrb())
        cx, cy = (l + r)//2, (t + b)//2
        now = time.time()

        if tid not in track_history:
            track_history[tid] = {
                "pos": (cx, cy),
                "time": now,
                "still_time": 0,
                "last_alert": 0
            }

        prev = track_history[tid]
        dist = math.dist((cx, cy), prev["pos"])
        dt = now - prev["time"] + 1e-6
        speed = dist / dt

        if speed < 10:
            prev["still_time"] += dt
        else:
            prev["still_time"] = 0

        loitering = prev["still_time"] > LOITER_TIME

        prev["pos"] = (cx, cy)
        prev["time"] = now

        # -------------------------
        # INTENT
        # -------------------------
        intent = infer_intent(has_bag, has_weapon, loitering, speed)

        if intent != "NORMAL" and now - prev["last_alert"] > ALERT_COOLDOWN:
            raise_alert(tid, intent)
            prev["last_alert"] = now

        # -------------------------
        # DRAW PERSON BOX
        # -------------------------
        color = (0,0,255) if intent != "NORMAL" else (255,0,0)
        cv2.rectangle(frame, (l,t), (r,b), color, 2)
        cv2.putText(frame,
                    f"ID:{tid} {intent}",
                    (l, t-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2)

        # -------------------------
        # ALERT BANNER (TASK 2)
        # -------------------------
        if intent != "NORMAL":
            cv2.rectangle(frame, (0,0), (w,60), (0,0,255), -1)
            cv2.putText(frame,
                        f"ALERT: {intent} (Person {tid})",
                        (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255,255,255),
                        3)

    # -------------------------
    # DISPLAY
    # -------------------------
    cv2.imshow("IntentWatch - Intelligent Surveillance", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# =========================
# CLEANUP
# =========================
cap.release()
cv2.destroyAllWindows()
conn.close()
print("[INFO] IntentWatch stopped")
