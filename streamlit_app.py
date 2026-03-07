import streamlit as st
import cv2
import time
import math
import sqlite3
import os
import pandas as pd
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# =========================
# CONFIG
# =========================
RUNNING_SPEED = 150.0
LOITER_TIME = 5.0
BAG_CLASSES = {"backpack", "handbag", "suitcase"}
WEAPON_CLASSES = {"knife", "gun"}

os.makedirs("data/videos", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("logs/alerts.db", check_same_thread=False)
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
track_history = {}

# =========================
# INTENT LOGIC
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

def log_alert(tid, intent):
    cursor.execute(
        "INSERT INTO alerts VALUES (?,?,?)",
        (time.strftime("%H:%M:%S"), tid, intent)
    )
    conn.commit()

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(layout="wide", page_title="IntentWatch", page_icon="🔍")

# Initialize session state for refresh
if "refresh_dashboard" not in st.session_state:
    st.session_state.refresh_dashboard = False

# Add auto-refresh mechanism
refresh_container = st.empty()

# Navigation
tab1, tab2 = st.tabs(["📊 Dashboard", "🎥 Live Analysis"])

# =========================
# DASHBOARD TAB
# =========================
with tab1:
    st.title("🔍 IntentWatch – Intelligent Surveillance System")
    
    # Project Description
    st.markdown("""
    ### About IntentWatch
    
    **IntentWatch** is an AI-powered intelligent surveillance system that goes beyond traditional CCTV monitoring.
    Instead of only recording footage, it understands human behavior and infers suspicious intent in real time, 
    then raises alerts before incidents escalate.
    
    #### Key Features:
    - 🎯 **Real-time Intent Detection**: Identifies suspicious behaviors like loitering, running, and potential attacks
    - 🎒 **Object Recognition**: Detects weapons, bags, and suspicious objects
    - 👤 **Person Tracking**: Tracks individuals across frames using DeepSORT algorithm
    - 📊 **Analytics Dashboard**: Provides insights into detected threats and patterns
    - 🚨 **Instant Alerts**: Immediate notifications when suspicious activity is detected
    """)
    
    st.divider()
    
    # Analytics Section
    st.header("📈 Analytics Overview")
    
    # Add refresh button
    col_refresh_btn, col_empty = st.columns([1, 5])
    with col_refresh_btn:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.refresh_dashboard = True
            st.rerun()
    
    # Fetch analytics from database (always fresh read)
    cursor.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = cursor.fetchone()[0]
    
    cursor.execute("SELECT intent, COUNT(*) as count FROM alerts GROUP BY intent")
    alerts_by_type = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(DISTINCT person_id) FROM alerts")
    unique_persons = cursor.fetchone()[0]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Alerts", total_alerts, delta=None)
    
    with col2:
        st.metric("Unique Persons Tracked", unique_persons, delta=None)
    
    with col3:
        # Count critical alerts (POSSIBLE ATTACK, SUSPICIOUS OBJECT)
        cursor.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE intent IN ('POSSIBLE ATTACK', 'SUSPICIOUS OBJECT')
        """)
        critical_alerts = cursor.fetchone()[0]
        st.metric("Critical Alerts", critical_alerts, delta=None, delta_color="inverse")
    
    with col4:
        # Count running alerts
        cursor.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE intent = 'RUNNING'
        """)
        running_alerts = cursor.fetchone()[0]
        st.metric("Running Alerts", running_alerts, delta=None)
    
    st.divider()
    
    # Alerts by Type
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Alerts by Intent Type")
        if alerts_by_type:
            df_intents = pd.DataFrame(alerts_by_type, columns=["Intent", "Count"])
            st.bar_chart(df_intents.set_index("Intent"))
        else:
            st.info("No alerts recorded yet. Start a surveillance session to see analytics.")
    
    with col_right:
        st.subheader("Alert Distribution")
        if alerts_by_type:
            intent_dict = {intent: count for intent, count in alerts_by_type}
            st.write(intent_dict)
        else:
            st.info("No data available")
    
    # Recent Alerts Table
    st.subheader("Recent Alerts")
    cursor.execute("""
        SELECT time, person_id, intent 
        FROM alerts 
        ORDER BY rowid DESC 
        LIMIT 10
    """)
    recent_alerts = cursor.fetchall()
    
    if recent_alerts:
        df_recent = pd.DataFrame(recent_alerts, columns=["Time", "Person ID", "Intent"])
        st.dataframe(df_recent, use_container_width=True)
    else:
        st.info("No alerts recorded yet.")
    
    # Clear Database Button
    st.divider()
    col_clear1, col_clear2, col_clear3 = st.columns([1, 1, 2])
    with col_clear1:
        if st.button("🗑️ Clear All Alerts"):
            cursor.execute("DELETE FROM alerts")
            conn.commit()
            st.success("All alerts cleared!")
            st.rerun()

# =========================
# LIVE ANALYSIS TAB
# =========================
with tab2:
    st.title("🎥 Live Surveillance Analysis")
    
    # Initialize session state for analysis control
    if "analysis_running" not in st.session_state:
        st.session_state.analysis_running = False
    
    st.sidebar.header("Input Selection")
    mode = st.sidebar.radio(
        "Choose Input Source",
        ("Live Camera", "CCTV Video Upload")
    )
    
    col_start, col_stop = st.sidebar.columns(2)
    with col_start:
        start = st.button("▶ Start", use_container_width=True)
    with col_stop:
        stop = st.button("⏹ Stop", use_container_width=True)
    
    if stop:
        st.session_state.analysis_running = False
        st.sidebar.warning("Analysis stopped")
    
    video_placeholder = st.empty()
    alert_placeholder = st.empty()

# =========================
# VIDEO SOURCE
# =========================
video_source = None

if mode == "CCTV Video Upload":
    uploaded_file = st.sidebar.file_uploader(
        "Upload CCTV Video",
        type=["mp4", "avi", "mov"]
    )

    if uploaded_file:
        video_path = f"data/videos/{uploaded_file.name}"
        with open(video_path, "wb") as f:
            f.write(uploaded_file.read())
        video_source = video_path

elif mode == "Live Camera":
    video_source = 0

# =========================
# RUN ANALYSIS
# =========================
if start and video_source is not None:
    st.session_state.analysis_running = True

if st.session_state.analysis_running and video_source is not None:
    cap = cv2.VideoCapture(video_source)
    st.success("Analysis started")
    
    frame_count = 0

    while cap.isOpened() and st.session_state.analysis_running:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        # Process every 2nd frame for smoother performance
        if frame_count % 2 != 0:
            continue

        h, w, _ = frame.shape
        results = detector(frame, verbose=False)[0]

        detections = []
        detected_objects = set()

        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = detector.names[cls]

            if conf < 0.5:  # Increased threshold for better accuracy
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detected_objects.add(label)

            if label == "person":
                detections.append(([x1, y1, x2-x1, y2-y1], conf, label))
            
            # Draw boxes only for non-person objects (bags, weapons) for context
            if label in BAG_CLASSES or label in WEAPON_CLASSES:
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,165,255), 2)
                cv2.putText(frame, label, (x1,y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,165,255), 2)

        has_bag = any(obj in BAG_CLASSES for obj in detected_objects)
        has_weapon = any(obj in WEAPON_CLASSES for obj in detected_objects)

        tracks = tracker.update_tracks(detections, frame=frame)

        alerts = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            tid = track.track_id
            l, t, r, b = map(int, track.to_ltrb())
            cx, cy = (l+r)//2, (t+b)//2
            now = time.time()

            if tid not in track_history:
                track_history[tid] = {
                    "pos": (cx, cy),
                    "time": now,
                    "still": 0
                }

            prev = track_history[tid]
            dist = math.dist((cx, cy), prev["pos"])
            dt = now - prev["time"] + 1e-6
            speed = dist / dt

            if speed < 10:
                prev["still"] += dt
            else:
                prev["still"] = 0

            loitering = prev["still"] > LOITER_TIME
            prev["pos"] = (cx, cy)
            prev["time"] = now

            intent = infer_intent(has_bag, has_weapon, loitering, speed)

            # Color coding: Red for threats, Yellow for suspicious, Blue for normal
            if intent in ["POSSIBLE ATTACK", "SUSPICIOUS OBJECT"]:
                color = (0,0,255)  # Red for critical
            elif intent in ["LOITERING", "RUNNING"]:
                color = (0,255,255)  # Yellow for warning
            else:
                color = (0,255,0)  # Green for normal
            
            cv2.rectangle(frame, (l,t), (r,b), color, 3)
            
            # Add background for better text visibility
            label_text = f"ID:{tid} - {intent}"
            (text_width, text_height), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (l, t-30), (l+text_width+5, t), color, -1)
            cv2.putText(frame, label_text,
                        (l+2, t-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

            if intent != "NORMAL":
                alerts.append(f"Person {tid}: {intent}")
                log_alert(tid, intent)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(frame, width=None, use_container_width=True)

        if alerts:
            alert_placeholder.error("🚨 ALERTS DETECTED")
            for a in alerts:
                st.write(a)

    cap.release()
    cv2.destroyAllWindows()
    st.session_state.analysis_running = False
    
    if ret == False:
        st.warning("Analysis completed")
    else:
        st.info("Analysis stopped by user")
    
    # Auto-refresh dashboard after analysis
    time.sleep(1)
    st.session_state.refresh_dashboard = True
