# IntentWatch - Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Setup (First Time Only)

Run the setup script to install all dependencies:

```powershell
.\setup.ps1
```

This will:
- ✅ Check Python and Node.js installations
- ✅ Create Python virtual environment
- ✅ Install Python dependencies (FastAPI, YOLOv8, OpenCV, etc.)
- ✅ Install frontend dependencies (React, Vite, etc.)

### Step 2: Start the Application

Run the main startup script:

```powershell
.\start-intentwatch.ps1
```

This will open two terminal windows:
- 🟢 **Backend Server** running on http://localhost:8000
- 🟢 **Frontend Dev Server** running on http://localhost:5173

### Step 3: Use the Application

1. **Open in Browser**
   - Go to http://localhost:5173

2. **Start Video Detection**
   - Click on "Live Feed" in the navigation
   - Select video source (Webcam or Upload Video)
   - Click "Start" button
   - Watch the AI detect objects and behaviors in real-time!

3. **View Alerts**
   - Real-time alerts appear in the sidebar
   - Click "Alerts Log" to see complete history
   - Use filters to search specific alert types

4. **Check Analytics**
   - Go to "Dashboard" for overview
   - "Analytics" page shows detailed statistics

---

## 📌 Common Commands

### Start Everything
```powershell
.\start-intentwatch.ps1
```

### Start Backend Only
```powershell
.\start-backend.ps1
```

### Start Frontend Only
```powershell
.\start-frontend.ps1
```

### Reinstall Dependencies
```powershell
# Python
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd "Frontend"
npm install
```

---

## 🔧 Manual Setup (Alternative)

If the automated setup doesn't work, follow these steps:

### Backend Setup

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start backend
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```powershell
# Navigate to frontend
cd "Frontend"

# Install dependencies
npm install

# Start dev server
npm run dev
```

---

## 🎯 What Can You Do?

### Detection Features
- ✅ **Person Detection** - Identify people in the frame
- ✅ **Loitering Detection** - Alert when someone stays in one place too long
- ✅ **Running Detection** - Detect fast movement
- ✅ **Unattended Bag Detection** - Alert for abandoned objects
- ✅ **Real-time Alerts** - Instant notifications for detected events

### Video Sources
- 📹 **Webcam** - Use your computer's camera
- 📁 **Video Files** - Upload MP4, AVI, MOV, etc.
- 🌐 **RTSP Streams** (Coming Soon)

---

## 📊 Application Pages

### 1. Dashboard
- Overview of system status
- Real-time statistics
- Activity timeline
- Alert distribution charts

### 2. Live Feed
- Real-time video stream with AI overlay
- Object detection bounding boxes
- Live alert notifications
- System status indicators

### 3. Alerts Log
- Complete alert history
- Search and filter capabilities
- Alert type breakdown
- Export functionality (Coming Soon)

### 4. Analytics
- Detection trends over time
- Alert type distribution
- Performance metrics
- Heatmaps (Coming Soon)

### 5. Zone Config
- Define restricted areas
- Set detection parameters
- Configure alert thresholds
- (UI Coming Soon)

---

## 🐛 Troubleshooting

### Backend Won't Start

**Problem:** "Module not found" error
```powershell
# Solution:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Problem:** "Port 8000 already in use"
```powershell
# Solution: Kill the process using port 8000
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
```

### Frontend Won't Start

**Problem:** "Dependencies not installed"
```powershell
# Solution:
cd "Frontend"
npm install
```

**Problem:** "Port 5173 already in use"
```powershell
# Solution: Kill the process or edit vite.config.ts to change port
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force
```

### Video Stream Issues

**Problem:** "No video showing"
- ✅ Check if backend is running
- ✅ Click "Start" button to begin stream
- ✅ Ensure webcam is connected (for webcam mode)
- ✅ Check browser console for errors (F12)

**Problem:** "Slow performance"
- ✅ Close other applications
- ✅ Use smaller video resolution
- ✅ Try a shorter video file for testing

### Can't Connect Frontend to Backend

**Problem:** "Failed to fetch" errors
- ✅ Ensure backend is running on port 8000
- ✅ Check `Frontend/.env` file
- ✅ Clear browser cache
- ✅ Check CORS settings in `backend/api/main.py`

---

## 🎨 Customization

### Adjust Detection Thresholds

Edit `backend/api/routes/video.py`:

```python
LOITER_THRESHOLD = 5          # seconds for loitering
BAG_THRESHOLD = 5             # seconds for unattended bag
RUNNING_SPEED_THRESHOLD = 120  # pixels/second for running
```

### Change UI Theme

Edit Tailwind classes in React components:
- Components are in `Frontend/src/app/components/`
- Pages are in `Frontend/src/app/pages/`

### Add Custom Alerts

1. Add detection logic in `backend/api/routes/video.py`
2. Use `add_alert(type, message)` to trigger
3. Alerts automatically appear in frontend

---

## 📝 Testing the System

### Quick Test with Webcam

1. Start the application
2. Go to Live Feed
3. Select "Webcam" source
4. Click "Start"
5. Move in front of camera to test person detection

### Test with Video File

1. Download a test video or use your own
2. Go to Live Feed
3. Click "Upload" button
4. Select your video file
5. Watch AI process the video

### Test Alert System

- **Loitering**: Stand still in front of camera for 5+ seconds
- **Running**: Move quickly across the frame
- **Unattended Bag**: Place an object and move away from it

---

## 🔗 Useful Links

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc

---

## 📦 What's Included

```
IntentWatch/
├── 📜 setup.ps1                 # One-click setup
├── 🚀 start-intentwatch.ps1     # Start everything
├── 📖 QUICKSTART.md             # This file
├── 📋 README.md                 # Full documentation
│
├── 🔙 backend/                  # FastAPI backend
│   ├── api/main.py              # API entry point
│   └── api/routes/              # API endpoints
│
└── 🎨 Frontend/  # React frontend
    ├── src/app/pages/           # UI pages
    ├── src/services/api.ts      # Backend integration
    └── vite.config.ts           # Dev server config
```

---

## 🎉 You're All Set!

Your IntentWatch AI Surveillance System is ready to use!

**Need help?** Check the full README.md for detailed documentation.

**Found a bug?** Check the troubleshooting section above.

**Want to customize?** Explore the codebase and make it your own!

---

**Happy Surveilling! 🎥🤖** 
