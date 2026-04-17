import cv2
import time
import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

try:
    from database.mongo import client, logs_collection, status_collection, users_collection, relation_collection, location_collection
    
    # Try a quick ping to ensure the database is actually reachable
    client.admin.command('ping')
    MONGO_AVAILABLE = True
    
    try:
        import pymongo
        location_collection.create_index([("timestamp", pymongo.ASCENDING)], expireAfterSeconds=3600)
    except Exception as index_err:
        print(f"[WARNING] Mongo Index creation failed: {index_err}")
        
except Exception as e:
    print(f"[ERROR] Mongo DB initialization failed: {e}")
    MONGO_AVAILABLE = False
    logs_collection = None
    status_collection = None
    users_collection = None
    relation_collection = None
    location_collection = None

ACTIVE_USER_ID = None

from core.detection_engine import DetectionEngine
from core.alert_engine import AlertEngine

app = FastAPI(title="YOLO Footpath API")

# 1. ENABLE CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals to hold the latest pipeline output
latest_frame = None
latest_raw_frame = None
latest_data = {"objects": [], "alerts": []}
camera_running = False
detection_running = False
target_video_source = 0

# Initialize the engines
print("[INFO] Initializing detection engine... This may take a moment to load weights.")
try:
    detector = DetectionEngine()
    alerter = AlertEngine()
except Exception as e:
    print(f"[ERROR] Engine initialization failed: {e}")
    detector = None
    alerter = None

# 2. ADD HEALTH CHECK ENDPOINT
@app.get("/health")
def health():
    return {"status": "ok"}

def process_pipeline(frame):
    """
    Thin orchestrator for the backend wrapped in basic error isolation.
    """
    if not detector or not alerter:
         return [], {"objects": [], "alerts": []}
         
    try:
        detection = detector.process_frame(frame)
        objects = detection.get("objects", [])
        
        raw_count = len(objects)
        
        # LIMIT OUTPUT PAYLOAD SIZE: sort objects by distance (closest first)
        def get_dist(o):
            return o["distance"] if o["distance"] is not None else float('inf')
            
        objects.sort(key=get_dist)
        objects = objects[:5]  # Allow up to 5 objects
        
        if raw_count > 0:
            print(f"[PIPELINE] Raw objects: {raw_count}, after limit: {len(objects)}, "
                  f"labels: {[o['label'] for o in objects]}, "
                  f"confs: {[round(o['confidence'], 3) for o in objects]}")
        
        # Generate stable alerts and retrieve direction
        alerts_data = alerter.generate_alerts(objects, frame.shape[1])
        
        # Build strict payload
        final_objs = []
        for obj in alerts_data["objects"]:
            final_objs.append({
                "label": obj.get("label", "unknown"),
                "distance": obj.get("distance"),
                "direction": obj.get("direction", "ahead")
            })
            
        api_payload = {
            "objects": final_objs,
            "alerts": alerts_data.get("alerts", [])
        }
        
        return alerts_data["objects"], api_payload
        
    except Exception as e:
        print(f"[ERROR] Pipeline exception: {e}")
        import traceback
        traceback.print_exc()
        return [], {"objects": [], "alerts": []}

def camera_loop(source=0):
    global latest_frame, latest_raw_frame, latest_data, camera_running, target_video_source
    
    current_source = target_video_source
    cap = cv2.VideoCapture(current_source)
    if isinstance(current_source, str) and "http" in current_source:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # 3. ADD CAMERA FAIL-SAFE HANDLING
    if not cap.isOpened():
        print(f"[ERROR] Camera {current_source} not accessible")
        
    camera_running = True
    print("[INFO] Camera loop started.")
    
    frame_count = 0
    while camera_running:
        if current_source != target_video_source:
            print(f"[INFO] Switching camera to {target_video_source}")
            cap.release()
            current_source = target_video_source
            cap = cv2.VideoCapture(current_source)
            if isinstance(current_source, str) and "http" in current_source:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                print(f"[ERROR] New camera source {current_source} invalid. Will keep retrying.")
                time.sleep(1)
                continue

        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Frame not received")
            time.sleep(0.5)
            continue
            
        frame_count += 1
            
        if not detection_running:
            # Just stream the raw un-annotated video if paused
            _, buffer = cv2.imencode('.jpg', frame)
            latest_frame = buffer.tobytes()
            latest_raw_frame = buffer.tobytes()
            
            if MONGO_AVAILABLE and ACTIVE_USER_ID:
                try:
                    if frame_count % 30 == 0:
                        status_collection.update_one(
                            {"user_id": ACTIVE_USER_ID},
                            {
                                "$set": {
                                    "last_seen": datetime.utcnow(),
                                    "state": "PAUSED"
                                }
                            },
                            upsert=True
                        )
                except Exception as db_err:
                    pass # silent error catch preventing crash
            
            time.sleep(0.01)
            continue
            
        # 6. ADD FPS OPTIMIZATION: skip frames
        if frame_count % 2 != 0:
            continue
            
        # Resize to maintain FPS
        frame = cv2.resize(frame, (640, 480))
            
        # Run pipeline
        raw_objects, data = process_pipeline(frame)
        
        # 7. ADD STRUCTURED LOGGING
        print(f"[INFO] Objects: {len(data['objects'])} | Alerts: {data['alerts']}")
        
        objects = data.get("objects", [])
        alerts = data.get("alerts", [])

        if MONGO_AVAILABLE and ACTIVE_USER_ID:
            try:
                # 3. ADD RISK LEVEL COMPUTATION
                risk_level = "LOW"
                if any(obj.get("distance") is not None and float(obj["distance"]) < 2 for obj in objects):
                    risk_level = "HIGH"
                elif len(objects) > 1:
                    risk_level = "MODERATE"

                # 5. UPDATE USER STATUS (HEARTBEAT)
                if frame_count % 30 == 0:
                    status_collection.update_one(
                        {"user_id": ACTIVE_USER_ID},
                        {
                            "$set": {
                                "last_seen": datetime.utcnow(),
                                "state": "ACTIVE",
                                "environment": "default"
                            }
                        },
                        upsert=True
                    )

                # 4. SAVE DETECTION LOGS (THROTTLED)
                # Roughly every 5 processed frames
                if frame_count % 10 == 0 and risk_level in ["MODERATE", "HIGH"]:
                    logs_collection.insert_one({
                        "user_id": ACTIVE_USER_ID,
                        "timestamp": datetime.utcnow(),
                        "objects": objects,
                        "alerts": alerts,
                        "risk": risk_level
                    })
            except Exception as e:
                print(f"[DB ERROR] {e}")
                
        # Annotate frame for video stream
        annotated_frame = frame.copy()
        _, bg_buffer = cv2.imencode('.jpg', frame)
        latest_raw_frame = bg_buffer.tobytes()
        
        for obj in raw_objects:
            if "bbox" not in obj:
                continue
            x1, y1, x2, y2 = obj["bbox"]
            label = obj.get("label", "unknown")
            meters = obj.get("distance")
            conf = obj.get("confidence", 0)
            
            color = (0, 200, 0)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            txt = f"{label} {conf:.2f}"
            if meters is not None:
                txt += f" {meters:.2f}m"
            cv2.putText(annotated_frame, txt, (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
        # Update globals safely
        latest_data = data
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        latest_frame = buffer.tobytes()
        
        # Small sleep to prevent CPU hogging
        time.sleep(0.01)
        
    cap.release()
    print("[INFO] Camera loop stopped.")

@app.on_event("startup")
def startup_event():
    # Start the background camera processing loop
    thread = threading.Thread(target=camera_loop, args=(0,), daemon=True)
    thread.start()

@app.on_event("shutdown")
def shutdown_event():
    global camera_running
    camera_running = False

def gen_frames():
    """Generator for MJPEG streaming."""
    global latest_frame
    while True:
        if latest_frame is None:
            time.sleep(0.1)
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        
        time.sleep(0.03)

@app.get("/video")
def video_feed():
    """Endpoint exposing MJPEG stream."""
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

def gen_raw_frames():
    """Generator for un-annotated MJPEG streaming."""
    global latest_raw_frame
    while True:
        if latest_raw_frame is None:
            time.sleep(0.1)
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + latest_raw_frame + b'\r\n')
        
        time.sleep(0.03)

@app.get("/video_raw")
def video_raw_feed():
    """Endpoint exposing raw MJPEG stream suitable for caretaker."""
    return StreamingResponse(gen_raw_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# 8. ENSURE API RESPONSE CONSISTENCY
@app.get("/data")
def get_data(user_id: str = None):
    """Endpoint exposing JSON output of pipeline."""
    global ACTIVE_USER_ID
    if user_id:
        ACTIVE_USER_ID = user_id
        
    if not detection_running:
        return {
            "objects": [],
            "alerts": []
        }
    return latest_data

@app.post("/start")
def start_detection(data: dict):
    global detection_running, ACTIVE_USER_ID
    ACTIVE_USER_ID = data.get("user_id")
    detection_running = True
    return {"status": "started"}

@app.post("/set_source")
def set_source(data: dict):
    global target_video_source
    new_source = data.get("source", 0)
    
    # Process string 0 back to integer index
    if isinstance(new_source, str) and new_source.isdigit():
        new_source = int(new_source)
        
    target_video_source = new_source
    return {"status": "success", "source": str(target_video_source)}

@app.post("/pause")
def pause_detection():
    global detection_running
    detection_running = False
    return {"status": "paused"}

@app.get("/status")
def status():
    return {"running": detection_running}

@app.post("/signup")
def signup(data: dict):
    if not MONGO_AVAILABLE:
        return {"error": "DB offline"}
        
    existing = users_collection.find_one({"email": data["email"]})
    if existing:
        return {"error": "User already exists"}

    user = {
        "user_id": data["email"],
        "email": data["email"],
        "password": data["password"],
        "role": data["role"]
    }

    users_collection.insert_one(user)
    
    if data["role"] == "caretaker" and data.get("linked_user"):
        relation_collection.insert_one({
            "caretaker_id": data["email"],
            "linked_users": [data["linked_user"]]
        })

    return {"message": "Signup successful"}

@app.post("/login")
def login(data: dict):
    if not MONGO_AVAILABLE:
        return {"error": "DB offline"}
    user = users_collection.find_one({"email": data.get("email")})
    if not user:
        return {"error": "User not found"}
    if user["password"] != data.get("password"):
        return {"error": "Invalid credentials"}
    return {
        "user_id": user["user_id"],
        "role": user["role"],
        "token": user["user_id"]
    }

@app.get("/caretaker/{caretaker_id}/status")
def caretaker_status(caretaker_id: str):
    if not MONGO_AVAILABLE:
        return {"error": "DB offline"}
    relation = relation_collection.find_one({"caretaker_id": caretaker_id})
    if not relation or not relation.get("linked_users"):
        return {"error": "No linked users"}
    user_id = relation["linked_users"][0]
    
    status_doc = status_collection.find_one({"user_id": user_id})
    if not status_doc:
        return {
            "state": "OFFLINE",
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "environment": "Waiting for patient app..."
        }
    status_doc["_id"] = str(status_doc["_id"])
    if "last_seen" in status_doc and hasattr(status_doc["last_seen"], "isoformat"):
        status_doc["last_seen"] = status_doc["last_seen"].isoformat() + "Z"
        
    return status_doc

@app.post("/location/update")
def update_location(data: dict):
    if not MONGO_AVAILABLE:
        return {"status": "error", "error": "DB offline"}
    try:
        location_collection.insert_one({
            "user_id": data.get("user_id"),
            "lat": data.get("lat"),
            "lng": data.get("lng"),
            "timestamp": datetime.utcnow()
        })
        return {"status": "ok"}
    except Exception as e:
        print("[LOCATION ERROR]", e)
        return {"status": "error"}

@app.get("/caretaker/location/{caretaker_id}")
def get_location(caretaker_id: str):
    if not MONGO_AVAILABLE:
        return {"error": "DB offline"}
        
    relation = relation_collection.find_one({"caretaker_id": caretaker_id})
    if not relation or not relation.get("linked_users"):
        return {"error": "No linked users"}
        
    user_id = relation["linked_users"][0]
    
    import pymongo
    loc = location_collection.find_one(
        {"user_id": user_id},
        sort=[("timestamp", pymongo.DESCENDING)]
    )
    
    if not loc:
        return {"error": "No location found"}
        
    ts = loc["timestamp"]
    if hasattr(ts, "isoformat"):
        ts = ts.isoformat() + "Z"

    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "timestamp": ts
    }

@app.get("/caretaker/{caretaker_id}/logs")
def caretaker_logs(caretaker_id: str):
    if not MONGO_AVAILABLE:
        return {"error": "DB offline"}
    relation = relation_collection.find_one({"caretaker_id": caretaker_id})
    if not relation or not relation.get("linked_users"):
        return {"error": "No linked users"}
    user_id = relation["linked_users"][0]
    
    logs_cursor = logs_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(20)
    logs = []
    for log in logs_cursor:
        log["_id"] = str(log["_id"])
        if "timestamp" in log and hasattr(log["timestamp"], "isoformat"):
            log["timestamp"] = log["timestamp"].isoformat() + "Z"
        logs.append(log)
    return logs

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
