import cv2
import math
import numpy as np
import torch
from pathlib import Path
from ultralytics import YOLO

# From the original script's helper:
import json
from collections import deque

class CalibMapper:
    def __init__(self, path="../utils/midas_calib.json", prefer="quad", smooth_n=3):
        self.path = Path(path)
        self.exist = self.path.exists()
        self.prefer = prefer
        self.smooth_n = smooth_n
        self.buffers = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            self.affine = None; self.quad = None; self.samples = []; self.pred_min = None; self.pred_max = None
            return
        d = json.loads(self.path.read_text())
        self.affine = d.get("affine")
        q = d.get("quad")
        self.quad = q.get("coefs") if q else None
        self.samples = d.get("samples", [])
        preds = [s["pred"] for s in self.samples] if self.samples else []
        if preds:
            self.pred_min = float(min(preds)); self.pred_max = float(max(preds))
        else:
            self.pred_min = self.pred_max = None

    def available(self):
        return (self.quad is not None) or (self.affine is not None)

    def apply(self, med_pred, key="global"):
        if med_pred is None:
            return None, {"reason": "no_pred"}
        if not self.available():
            return None, {"reason": "no_calib"}
        method = self.prefer
        meters = None
        if method == "quad" and self.quad:
            c2, c1, c0 = [float(x) for x in self.quad]
            meters = float(c2*(med_pred**2) + c1*med_pred + c0)
        elif method == "affine" and self.affine:
            a = float(self.affine["a"]); b = float(self.affine["b"])
            meters = a * float(med_pred) + b
        else:
            if self.quad:
                c2, c1, c0 = [float(x) for x in self.quad]
                meters = float(c2*(med_pred**2) + c1*med_pred + c0)
            elif self.affine:
                a = float(self.affine["a"]); b = float(self.affine["b"])
                meters = a * float(med_pred) + b
        if not np.isfinite(meters):
            return None, {"reason": "nonfinite"}
        meters = float(np.clip(meters, 0.02, 200.0))
        if self.smooth_n > 1:
            buf = self.buffers.get(key)
            if buf is None:
                buf = deque(maxlen=self.smooth_n)
                self.buffers[key] = buf
            buf.append(meters)
            meters = float(sum(buf)/len(buf))
        return meters, {"method": method, "raw": float(med_pred), "mapped": meters}

def load_midas(device="cpu", model_name="MiDaS_small"):
    # Load MiDaS
    midas_model = torch.hub.load("intel-isl/MiDaS", model_name)
    midas_model.to(device).eval()
    transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    midas_transform = transforms.small_transform if model_name == "MiDaS_small" else transforms.default_transform
    return midas_model, midas_transform

def prepare_midas_input(midas_transform, frame, device):
    from PIL import Image
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try:
        inp = midas_transform(img_rgb)
    except Exception:
        inp = midas_transform(Image.fromarray(img_rgb))
    if hasattr(inp, "dim"):
        t = inp
    else:
        if isinstance(inp, (list, tuple)):
            t = next((v for v in inp if hasattr(v, "dim")), None)
            if t is None: t = torch.as_tensor(inp)
        else:
            t = torch.as_tensor(inp)
    while t.dim() > 4 and 1 in t.shape:
        t = t.squeeze(0)
    if t.dim() == 3:
        t = t.unsqueeze(0)
    return t.to(device)

def mids_to_depth_map(midas_model, input_batch, target_size):
    import torch.nn.functional as F
    with torch.no_grad():
        pred = midas_model(input_batch)
        if isinstance(pred, (list, tuple)): pred = pred[0]
        if pred.dim() == 4 and pred.shape[1] == 1: pred = pred.squeeze(1)
        if pred.dim() == 3: pred = pred.squeeze(0)
        h, w = target_size
        up = F.interpolate(pred.unsqueeze(0).unsqueeze(0), size=(h, w), mode="bicubic", align_corners=False)
        return up.squeeze().cpu().numpy()

class DetectionEngine:
    # Derive the project root once from the file location:
    # detection_engine.py -> core/ -> backend/ -> project_root/
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

    def __init__(self, yolo_model_path="models/best.pt", calib_path="utils/midas_calib.json", scale_path="utils/midas_scale.txt"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[INFO] DetectionEngine using device: {self.device}")
        print(f"[INFO] Project root resolved to: {self._PROJECT_ROOT}")
        self.yolo = None
        self.midas_model = None
        self.midas_transform = None
        self._load_models(yolo_model_path)
        
        # Determine paths using the project root so they work from any CWD
        actual_calib = self._resolve_path(calib_path)
        self.mapper = CalibMapper(path=str(actual_calib), prefer="quad", smooth_n=3)
        self.scale = None
        
        actual_scale = self._resolve_path(scale_path)
        if actual_scale.exists():
            try:
                self.scale = float(actual_scale.read_text().strip())
            except:
                pass

    def _resolve_path(self, rel_path):
        """Resolve a path relative to the project root, with fallbacks."""
        candidates = [
            self._PROJECT_ROOT / rel_path,       # project_root/utils/...
            Path(rel_path),                       # CWD-relative
            Path("../" + rel_path),               # one level up from CWD
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]  # return the project-root version even if missing

    def _load_models(self, yolo_path):
        # Determine path dynamically — prefer custom model, use absolute project root
        candidates = [
            self._PROJECT_ROOT / yolo_path,       # project_root/models/best.pt  (BEST)
            Path(yolo_path),                       # CWD-relative
            Path("../" + yolo_path),               # from backend/ -> ../models/best.pt
        ]
        actual_yolo = None
        for c in candidates:
            if c.exists():
                actual_yolo = c
                break

        # Fallback to generic yolov8n only if custom model is truly missing
        if actual_yolo is None:
            fallbacks = [
                self._PROJECT_ROOT / "yolov8n.pt",
                Path("yolov8n.pt"),
                Path("../yolov8n.pt"),
            ]
            for fb in fallbacks:
                if fb.exists():
                    actual_yolo = fb
                    print(f"[WARNING] Custom model '{yolo_path}' not found! Falling back to generic: {fb.resolve()}")
                    break

        if actual_yolo is None:
            actual_yolo = Path(yolo_path)  # let YOLO handle the error
        
        print(f"[INFO] Loading YOLO model from: {actual_yolo.resolve()}")
        self.yolo = YOLO(str(actual_yolo))
        print(f"[INFO] YOLO model classes ({len(self.yolo.names)}): {self.yolo.names}")
        print(f"[INFO] 'person' in model classes: {'person' in self.yolo.names.values()}")
        
        # Load MiDaS depth model — optional, detection works without it
        try:
            midas_model, midas_transform = load_midas(device=self.device, model_name="MiDaS_small")
            self.midas_model = midas_model
            self.midas_transform = midas_transform
            print("[INFO] MiDaS depth model loaded successfully")
        except Exception as e:
            print(f"[WARNING] MiDaS depth model failed to load: {e}")
            print("[WARNING] Depth estimation disabled — YOLO detection will still work")
            self.midas_model = None
            self.midas_transform = None

    def compute_depth(self, frame):
        if self.midas_model is None or self.midas_transform is None:
            return None  # Depth estimation unavailable
        try:
            inb = prepare_midas_input(self.midas_transform, frame, self.device)
            depth_map = mids_to_depth_map(self.midas_model, inb, (frame.shape[0], frame.shape[1]))
            return depth_map
        except Exception as e:
            print(f"Depth computation error: {e}")
            return None

    def run_inference(self, frame, conf=0.10):
        results = self.yolo(frame, conf=conf, verbose=False)
        return results[0]

    def process_frame(self, frame):
        depth_map = self.compute_depth(frame)
        res = self.run_inference(frame)
        
        num_detections = len(res.boxes) if res.boxes is not None else 0
        
        objects = []
        if num_detections > 0:
            for box in res.boxes:
                xy = [float(v) for v in box.xyxy[0].tolist()]
                x1, y1, x2, y2 = [int(round(v)) for v in xy]
                cls = int(box.cls[0].item())
                confv = float(box.conf[0].item())
                label = self.yolo.names.get(cls, str(cls))
                
                meters = None
                if depth_map is not None:
                    h_d, w_d = depth_map.shape
                    x1c, x2c = max(0, min(w_d - 1, x1)), max(0, min(w_d - 1, x2))
                    y1c, y2c = max(0, min(h_d - 1, y1)), max(0, min(h_d - 1, y2))
                    
                    if x2c > x1c and y2c > y1c:
                        region = depth_map[y1c:y2c + 1, x1c:x2c + 1]
                        if region.size > 0:
                            med = float(np.median(region))
                            if self.mapper.exist:
                                meters, _ = self.mapper.apply(med, key=label)
                            elif self.scale is not None:
                                meters = med * self.scale
                
                # Default a safe value when none is available
                if meters is not None and math.isnan(meters):
                    meters = None
                    
                objects.append({
                    "label": label,
                    "confidence": confv,
                    "bbox": [x1, y1, x2, y2],
                    "distance": round(meters, 2) if meters is not None else None
                })
                
        return {"objects": objects}
