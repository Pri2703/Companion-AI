# 🚶‍♂️ YOLO Footpath Assistive Navigation

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-cyan)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-teal)

This project provides an AI-powered assistive navigation tool designed for enhanced spatial awareness on footpaths. By leveraging **YOLO** for object detection and **MiDaS** for depth estimation, the system dynamically calculates distances and spatial orientations, delivering real-time sensory feedback via a dedicated web application.

---

## 🌟 Key Features
- **Real-Time Video Analytics:** Uses YOLO to detect objects and pedestrians seamlessly.
- **Depth Estimation:** MiDaS computes dynamic relative distances for objects.
- **Spatial Awareness:** Calculates geometries to map specific object coordinates ("left", "right", "ahead").
- **Smart Alert Engine:** Implements a stability filter tracking object inferences over multiple frames to prevent false positives and auditory flickering.
- **Browser Native TTS:** Delivers Text-to-Speech spatial events securely to the user through their web browser.
- **Frontend Dashboard:** A React (Vite) interface that allows starting/pausing the detection pipelines dynamically without dropping the live MJPEG camera feed.

---

## 🏗 System Architecture

### Backend (`/backend`)
A completely isolated API-driven backend.
- **FastAPI Core (`app.py`)**: Runs the web server via Uvicorn. Initiates threaded camera background loops.
- **Detection Engine (`detection_engine.py`)**: Coordinates execution of local YOLO weights and PyTorch Hub MiDaS.
- **Alert Engine (`alert_engine.py`)**: Maps geometries and tracks stability to orchestrate confident text events.

### Frontend (`/frontend`)
A Vite + React driven single-page application.
- **`App.jsx`**: Acts as the main orchestrator communicating with local backend APIs.
- **`Controls.jsx`**: Triggers interactive camera execution state cycles.
- **`VideoFeed.jsx`**: Parses `multipart/x-mixed-replace` streams.
- **`AlertsPanel.jsx`**: Polls bounding arrays and synthesizes browser speech events.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.x
- Node.js & npm

### 2. Backend Setup
Navigate to the root directory, create/activate your virtual environment, and install dependencies:
```bash
python -m venv myenv

# Activate on Windows:
.\myenv\Scripts\activate
# Activate on Mac/Linux:
source myenv/bin/activate

pip install -r requirements.txt
```

To run the backend server:
```bash
uvicorn backend.app:app --reload
```
The FastAPI instance will boot at `http://localhost:8000`.

### 3. Frontend Setup
Open a new terminal, navigate to the frontend directory, install dependencies, and start the development server:
```bash
cd frontend
npm install
npm run dev
```

The React dashboard should now be locally accessible.

---

## 📡 API Endpoints (FastAPI)
| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Rapid API vitality ping. |
| `/video` | `GET` | Streams the MJPEG encoded video natively. |
| `/data` | `GET` | Returns sanitized JSON payloads of identified objects and spatial text alerts. |
| `/start` | `POST` | Interactively kicks off the background tracking pipeline. |
| `/pause` | `POST` | Pauses execution natively bypassing YOLO/MiDaS compute constraints but retaining HTTP streams. |

---

## 🔮 Roadmap / Future
- Enhance React UI/UX using specific specialized design languages (e.g. TailwindCSS or Chakra UI).
- Resolve deprecation warnings logged by FastAPI upon startup (`on_event("startup")` vs `lifespan`).
- Expose configuration endpoints to actively modify detection confidence, model selections, or MiDaS calibration curves natively from the frontend dashboard.
