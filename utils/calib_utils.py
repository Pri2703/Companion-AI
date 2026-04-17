# calib_utils.py
import json
from pathlib import Path
import numpy as np
from collections import deque

class MidasCalibrator:
    def __init__(self, path="midas_calib.json", prefer="affine", smooth_n=3):
        self.path = Path(path)
        self.exist = self.path.exists()
        self.prefer = prefer
        self.smooth_n = max(0, int(smooth_n))
        self._buffers = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            self.affine = None; self.quad = None; self.samples = []
            self.pred_min = self.pred_max = None
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
        return self.path.exists() and (self.affine or self.quad)

    def apply(self, med_pred, method=None, key=None):
        if med_pred is None:
            return None, {"reason":"no_pred"}
        if not self.available():
            return None, {"reason":"no_calib"}
        method = (method or self.prefer).lower()
        meters = None
        if method == "affine" and self.affine:
            a = float(self.affine["a"]); b = float(self.affine["b"])
            meters = a * float(med_pred) + b
        elif method == "quad" and self.quad:
            c2, c1, c0 = [float(x) for x in self.quad]
            meters = c2*med_pred*med_pred + c1*med_pred + c0
        else:
            if self.affine:
                a = float(self.affine["a"]); b = float(self.affine["b"])
                meters = a * float(med_pred) + b
            elif self.quad:
                c2, c1, c0 = [float(x) for x in self.quad]
                meters = c2*med_pred*med_pred + c1*med_pred + c0
        in_range = True
        if self.pred_min is not None and self.pred_max is not None:
            in_range = (self.pred_min <= med_pred <= self.pred_max)
        if meters is not None:
            if not np.isfinite(meters):
                return None, {"reason":"nonfinite"}
            meters = float(np.clip(meters, 0.02, 200.0))
        if self.smooth_n > 1 and key is not None and meters is not None:
            buf = self._buffers.get(key)
            if buf is None:
                buf = deque(maxlen=self.smooth_n)
                self._buffers[key] = buf
            buf.append(meters)
            meters = float(sum(buf)/len(buf))
        info = {"method": method, "in_range": in_range, "raw": float(med_pred), "mapped": meters}
        return meters, info
