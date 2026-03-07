from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os
import shutil
import time
import threading
import cv2
from ultralytics import YOLO
from api.routes.alerts import add_alert

router = APIRouter()

# Disable FFmpeg threading to avoid codec errors
os.environ.setdefault("FFREPORT", "file=/dev/null")
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "threads;1")

# Limit OpenCV internal threading to reduce race conditions
cv2.setNumThreads(1)

# ---------------- PATHS / CONFIG ----------------
BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
WORKSPACE_DIR = BACKEND_DIR.parent

VIDEO_DIR = BACKEND_DIR / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

MODEL_CANDIDATES = [BACKEND_DIR / "yolov8n.pt", WORKSPACE_DIR / "yolov8n.pt"]

LOITER_THRESHOLD = 5        # seconds (reduced for faster detection)
BAG_THRESHOLD = 5           # seconds (reduced for faster detection)  
PERSON_BAG_DISTANCE = 150   # pixels
RUNNING_SPEED_THRESHOLD = 120  # pixels per second (high threshold for actual running)
RUNNING_ACCELERATION_THRESHOLD = 60  # px/s² (large speed increase needed)

# Global thread lock for thread-safe operations
stream_lock = threading.Lock()

# ---------------- GLOBAL STATE ----------------
current_video_source = {"mode": None, "path": None}
cap = None

person_start_time = None
bag_start_time = None
person_positions = {}  # Track person positions for speed calculation
person_speed_history = {}  # Track speed history for acceleration detection
frame_count = 0
last_frame_time = time.time()

model = None


class StartCameraRequest(BaseModel):
    device_id: int = 0


class StartVideoRequest(BaseModel):
    source: str

def open_capture(source):
    if isinstance(source, int) and os.name == "nt":
        return cv2.VideoCapture(source, cv2.CAP_DSHOW)
    # For file paths / rtsp URLs, CAP_FFMPEG can be flaky on some Windows builds.
    # Try FFmpeg first, then fall back to OpenCV's default backend.
    cap_try = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    if cap_try.isOpened():
        return cap_try

    try:
        cap_try.release()
    except Exception:
        pass

    return cv2.VideoCapture(source)


def reset_stream_state():
    global cap, person_start_time, bag_start_time, person_positions, person_speed_history, frame_count, last_frame_time
    if cap:
        cap.release()
        cap = None
    person_start_time = None
    bag_start_time = None
    person_positions = {}
    person_speed_history = {}
    frame_count = 0
    last_frame_time = time.time()

def get_model():
    """Lazy load YOLO model"""
    global model
    try:
        if model is None:
            model_path = next((p for p in MODEL_CANDIDATES if p.exists()), None)
            if model_path is None:
                raise FileNotFoundError(
                    "YOLO model file not found. Expected one of: "
                    + ", ".join(str(p) for p in MODEL_CANDIDATES)
                )

            print(f"Loading YOLO model from: {model_path}")
            model = YOLO(str(model_path))
            print("YOLO model loaded successfully")
        return model
    except Exception as e:
        print(f"ERROR loading YOLO model: {str(e)}")
        raise

# ---------------- API ENDPOINTS ----------------

@router.post("/upload")
def upload_video(file: UploadFile = File(...)):
    """Upload and validate video file"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Validate file extension
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {', '.join(allowed_extensions)}",
            )
        
        file_path = VIDEO_DIR / file.filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate that file was written
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="File upload failed or file is empty")
        
        # Validate video can be opened
        test_cap = cv2.VideoCapture(str(file_path))
        if not test_cap.isOpened():
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Invalid video file or unsupported codec")
        test_cap.release()
        
        reset_stream_state()
        abs_path = str(file_path.resolve())
        current_video_source.update({"mode": "file", "path": abs_path})
        
        print(f"✓ Video uploaded successfully: {abs_path}")
        return {"message": "Video uploaded successfully", "path": abs_path, "filename": file.filename}
    
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Upload error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {error_msg}")

@router.post("/start-camera")
def start_camera(body: StartCameraRequest | None = None):
    """Start live camera feed"""
    try:
        device_id = 0 if body is None else int(body.device_id)
        # Test camera access first
        test_cap = open_capture(device_id)
        if not test_cap.isOpened():
            test_cap.release()
            raise HTTPException(status_code=500, detail="Camera not available or already in use")
        test_cap.release()
        
        reset_stream_state()
        current_video_source.update({"mode": "camera", "path": device_id})
        print("✓ Camera selected successfully")
        return {"message": "Live camera selected", "device_id": device_id}
    except Exception as e:
        print(f"✗ Camera error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Camera error: {str(e)}")


@router.post("/start")
def start_video(body: StartVideoRequest):
    """Start stream from a source.

    This endpoint exists to match the frontend API client.
    Accepted sources:
    - 'webcam'/'camera' -> device 0
    - numeric string -> that camera device id
    - any other string -> treated as a path/URL (validated by trying to open)
    """
    if body is None or not body.source:
        raise HTTPException(status_code=400, detail="Missing source")

    source_raw = str(body.source).strip()
    try:
        if source_raw.lower() in {"webcam", "camera"}:
            source: int | str = 0
        else:
            # If numeric, treat as camera device id.
            try:
                source = int(source_raw)
            except Exception:
                source = source_raw

        # Validate the source can be opened.
        test_cap = open_capture(source)
        if not test_cap.isOpened():
            try:
                test_cap.release()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="Video source not available")
        test_cap.release()

        reset_stream_state()
        current_video_source.update(
            {"mode": "camera" if isinstance(source, int) else "file", "path": source}
        )
        return {"message": "Video source selected", "source": source_raw}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start error: {str(e)}")

@router.post("/stop")
def stop_video():
    """Stop video stream"""
    global cap
    try:
        reset_stream_state()
        print("✓ Video stream stopped")
        return {"message": "Video stream stopped"}
    except Exception as e:
        print(f"✗ Stop error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def video_status():
    return current_video_source

# ---------------- STREAM + INTENT ----------------

def frame_generator(source):
    global cap, person_start_time, bag_start_time, person_positions, person_speed_history, frame_count, last_frame_time

    frames_processed = 0
    fps_limit = 30
    
    try:
        # Disable threading to avoid FFmpeg codec issues
        if isinstance(source, int):
            cap = open_capture(source)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Single buffer for camera
        else:
            cap = open_capture(source)
            # Disable multithreading for file reading
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        
        if not cap.isOpened():
            print(f"✗ Failed to open: {source}")
            return

        print(f"✓ Video source opened: {source}")
        detection_model = get_model()

        while True:
            try:
                ret, frame = cap.read()
                if not ret or frame is None:
                    if isinstance(source, str):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            break
                    else:
                        break

                # Resize frame if too large
                h, w = frame.shape[:2]
                if h > 720:
                    scale = 720 / h
                    w = int(w * scale)
                    frame = cv2.resize(frame, (w, 720), interpolation=cv2.INTER_LINEAR)

                frames_processed += 1

                # Run YOLO detection
                with stream_lock:
                    results = detection_model(frame, conf=0.4, verbose=False)

                persons = []
                bags = []

                # Process detections
                for r in results:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        label = detection_model.names[cls]
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2

                        if label == "person":
                            persons.append((x1, y1, x2, y2, cx, cy))
                        elif label in ["backpack", "handbag", "suitcase", "bag"]:
                            bags.append((x1, y1, x2, y2))

                        # Draw non-person objects immediately. Person labels are drawn
                        # after we assign a stable per-frame tracking id.
                        if label in ["backpack", "handbag", "suitcase"]:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(
                                frame,
                                label,
                                (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 0),
                                2,
                            )

                # ---- RUNNING DETECTION (Improved) ----
                now = time.time()
                running_persons = set()

                # Snapshot previous positions so pid assignment is stable within this frame.
                prev_positions = dict(person_positions)
                used_pids = set()
                person_ids_by_index: dict[int, int] = {}
                
                for i, (x1, y1, x2, y2, cx, cy) in enumerate(persons):
                    # Use X-position proximity for tracking (better than sequential ID)
                    pid = None
                    min_dist = float('inf')
                    
                    for tracked_pid in list(prev_positions.keys()):
                        if tracked_pid in used_pids:
                            continue
                        prev_x, prev_y, prev_t = prev_positions[tracked_pid]
                        x_dist = abs(cx - prev_x)
                        if x_dist < 80:  # Within 80 pixels horizontally
                            if x_dist < min_dist:
                                min_dist = x_dist
                                pid = tracked_pid
                    
                    # Assign new ID if no close match found
                    if pid is None:
                        pid = max(prev_positions.keys()) + 1 if prev_positions else 0
                        while pid in used_pids:
                            pid += 1

                    used_pids.add(pid)
                    person_ids_by_index[i] = pid
                    
                    # Calculate speed if we have previous position
                    if pid in prev_positions:
                        prev_x, prev_y, prev_t = prev_positions[pid]
                        dist = ((cx - prev_x)**2 + (cy - prev_y)**2)**0.5
                        dt = max(now - prev_t, 0.016)  # Min 16ms (60 FPS)
                        speed = dist / dt
                        
                        if pid not in person_speed_history:
                            person_speed_history[pid] = []
                        
                        person_speed_history[pid].append(speed)
                        if len(person_speed_history[pid]) > 5:
                            person_speed_history[pid].pop(0)
                        
                        # Require sustained high speed (not just a spike)
                        if len(person_speed_history[pid]) >= 3:
                            recent_speeds = person_speed_history[pid][-3:]
                            avg_speed = sum(recent_speeds) / len(recent_speeds)
                            
                            # Only trigger if consistently fast (not walking ~30-50 px/s)
                            if avg_speed > RUNNING_SPEED_THRESHOLD:
                                running_persons.add(pid)

                    # Update the global tracking state for this pid.
                    person_positions[pid] = (cx, cy, now)

                # Draw person boxes and include person id in the overlay label.
                for i, (x1, y1, x2, y2, cx, cy) in enumerate(persons):
                    pid = person_ids_by_index.get(i)
                    label = f"person {pid}" if pid is not None else "person"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
                
                # Alert on running detection
                for pid in running_persons:
                    add_alert("Running", "Person running detected")
                    # Find person and draw text
                    for i, (x1, y1, x2, y2, cx, cy) in enumerate(persons):
                        tracked_pid = None
                        for tp in person_positions.keys():
                            prev_x, prev_y, _ = person_positions[tp]
                            if abs(cx - prev_x) < 80:
                                tracked_pid = tp
                                break
                        if tracked_pid == pid:
                            cv2.putText(frame, "RUNNING!", (x1, y1 - 30),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                            break
                
                # Clean up old tracking data
                person_positions = {k: v for k, v in person_positions.items() if now - v[2] < 1.5}
                person_speed_history = {k: v for k, v in person_speed_history.items() if k in person_positions}

                # ---- LOITERING DETECTION ----
                if persons:
                    if person_start_time is None:
                        person_start_time = now
                    elif now - person_start_time > LOITER_THRESHOLD:
                        add_alert("Loitering", "Person loitering detected")
                        person_start_time = now
                else:
                    person_start_time = None

                # ---- UNATTENDED BAG DETECTION ----
                unattended_bag = False
                for bx1, by1, bx2, by2 in bags:
                    bcx = (bx1 + bx2) // 2
                    bcy = (by1 + by2) // 2
                    near_person = any(
                        ((bcx - px[4])**2 + (bcy - px[5])**2)**0.5 < PERSON_BAG_DISTANCE
                        for px in persons
                    )
                    
                    if not near_person:
                        unattended_bag = True
                        cv2.putText(frame, "UNATTENDED!", (bx1, by1 - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        break

                if unattended_bag:
                    if bag_start_time is None:
                        bag_start_time = now
                    elif now - bag_start_time > BAG_THRESHOLD:
                        add_alert("Unattended Bag", "Suspicious item detected")
                        bag_start_time = now
                else:
                    bag_start_time = None

                # Encode and yield
                ret, buf = cv2.imencode(".jpg", frame)
                if not ret:
                    continue

                if isinstance(source, str):
                    time.sleep(1 / fps_limit)

                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

            except Exception as e:
                print(f"✗ Frame error: {str(e)}")
                continue

        print(f"✓ Stream ended. Processed {frames_processed} frames")
        cap.release()
        cap = None

    except Exception as e:
        print(f"✗ Critical error: {str(e)}")
        if cap:
            cap.release()
        cap = None
@router.get("/stream")
def stream_video():
    if current_video_source["mode"] is None:
        raise HTTPException(status_code=400, detail="No video source selected")
    
    source = current_video_source["path"]
    
    # Validate source exists before streaming
    if isinstance(source, str):
        if not os.path.exists(source):
            print(f"ERROR: File does not exist: {source}")
            raise HTTPException(status_code=404, detail=f"Video file not found: {source}")
    
    try:
        return StreamingResponse(
            frame_generator(source),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        print(f"ERROR in stream_video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")
