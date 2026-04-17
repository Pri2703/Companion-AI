#!/usr/bin/env python3
"""
Improved MiDaS multi-point calibration tool
- auto-tries backends if webcam fails
- robust MiDaS input handling
- interactive: press 'c' to capture, enter real meters
- press 'f' to fit (>=3 samples), saves midas_calib.json and calib_plot.png
- press 'q' to quit
"""
import argparse, json, time, sys, traceback
from pathlib import Path
import numpy as np
import cv2
import torch

MODEL_NAME = "MiDaS_small"   # try "DPT_Hybrid" for higher accuracy (slower)
OUT_JSON = "midas_calib.json"
PLOT_FILE = "calib_plot.png"

def try_open_capture(src, backend_preference=None):
    """Return cv2.VideoCapture or None. backend_preference can be 'msmf','dshow'."""
    if str(src).isdigit():
        idx = int(src)
        # Try chosen backend first, then fallbacks
        backends = []
        if backend_preference:
            backends.append(backend_preference)
        # Common Windows options
        backends += ["msmf", "dshow", "cv2"]
        for b in backends:
            try:
                if b == "msmf":
                    cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
                elif b == "dshow":
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(idx)
            except Exception:
                cap = None
            if cap is not None and cap.isOpened():
                print(f"Opened camera {idx} with backend={b}")
                return cap
        print(f"Unable to open camera {idx} with tried backends: {backends}")
        return None
    else:
        cap = cv2.VideoCapture(src)
        if cap.isOpened():
            print(f"Opened video file: {src}")
            return cap
        print(f"Unable to open video file: {src}")
        return None

def load_midas(device="cpu"):
    print("Loading MiDaS model:", MODEL_NAME)
    midas = torch.hub.load("intel-isl/MiDaS", MODEL_NAME)
    midas.to(device).eval()
    transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    if MODEL_NAME == "MiDaS_small":
        transform = transforms.small_transform
    elif MODEL_NAME.startswith("DPT"):
        transform = transforms.dpt_transform
    else:
        transform = transforms.default_transform
    return midas, transform

def prepare_input(transform, frame, device):
    # Robust transform: accept numpy or PIL
    from PIL import Image
    import torch
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try:
        t = transform(img_rgb)
    except Exception:
        t = transform(Image.fromarray(img_rgb))
    # get tensor and normalize dims
    if hasattr(t, "dim"):
        tensor = t
    else:
        tensor = torch.as_tensor(t)
    # squeeze extra singleton outer dims if present
    while tensor.dim() > 4 and 1 in tensor.shape:
        tensor = tensor.squeeze(0)
    if tensor.dim() == 3:
        tensor = tensor.unsqueeze(0)
    return tensor.to(device)

def mids_to_depth(midas, inbatch, target_size):
    import torch.nn.functional as F
    with torch.no_grad():
        pred = midas(inbatch)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        if pred.dim() == 4 and pred.shape[1] == 1:
            pred = pred.squeeze(1)
        if pred.dim() == 3:
            pred = pred.squeeze(0)
        h, w = target_size
        up = F.interpolate(pred.unsqueeze(0).unsqueeze(0), size=(h, w), mode="bicubic", align_corners=False)
        depth = up.squeeze().cpu().numpy()
        return depth

def fit_and_save(samples, out_json=OUT_JSON):
    preds = np.array([s[0] for s in samples])
    reals = np.array([s[1] for s in samples])
    # affine
    A = np.vstack([preds, np.ones_like(preds)]).T
    a, b = np.linalg.lstsq(A, reals, rcond=None)[0]
    pred_fit = a*preds + b
    rmse = float(np.sqrt(np.mean((reals - pred_fit)**2)))
    # quadratic
    coefs = np.polyfit(preds, reals, 2)
    pred_q = np.polyval(coefs, preds)
    rmse_q = float(np.sqrt(np.mean((reals - pred_q)**2)))
    out = {
        "model": MODEL_NAME,
        "affine": {"a": float(a), "b": float(b), "rmse": rmse},
        "quad": {"coefs": [float(x) for x in coefs], "rmse": rmse_q},
        "samples": [{"pred": float(p), "m": float(r)} for p,r in samples]
    }
    Path(out_json).write_text(json.dumps(out, indent=2))
    print("Saved calibration to", out_json, "affine RMSE:", rmse, "quad RMSE:", rmse_q)
    # plot
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6,5))
        plt.scatter(preds, reals, label="samples")
        xs = np.linspace(preds.min()*0.9, preds.max()*1.1, 200)
        plt.plot(xs, a*xs + b, label="affine")
        plt.plot(xs, np.polyval(coefs, xs), label="quad")
        plt.xlabel("MiDaS pred")
        plt.ylabel("Meters (real)")
        plt.legend()
        plt.grid(True)
        plt.title(f"affine RMSE={rmse:.3f} quad RMSE={rmse_q:.3f}")
        plt.tight_layout()
        plt.savefig(PLOT_FILE, dpi=200)
        print("Wrote plot to", PLOT_FILE)
    except Exception as e:
        print("Could not produce plot:", e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="webcam index or video path")
    parser.add_argument("--backend", default=None, help="preferred webcam backend: msmf or dshow (optional)")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    args = parser.parse_args()

    cap = try_open_capture(args.source, backend_preference=args.backend)
    if cap is None:
        print("ERROR: could not open source. Try different index or --backend dshow/msmf or use video file.")
        return

    device = args.device
    try:
        midas, transform = load_midas(device=device)
    except Exception as e:
        print("Failed loading MiDaS:", e)
        traceback.print_exc()
        return

    samples = []
    print("Ready. Controls: 'c' capture sample, 'f' fit mapping (>=3 samples), 'q' quit.")
    max_side = 1024

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Stream ended")
            break
        H, W = frame.shape[:2]
        if max(H, W) > max_side:
            scale = max_side / float(max(H, W))
            small = cv2.resize(frame, (int(W*scale), int(H*scale)))
        else:
            small = frame.copy()

        sh, sw = small.shape[:2]
        cx1, cy1 = int(0.4*sw), int(0.4*sh)
        cx2, cy2 = int(0.6*sw), int(0.6*sh)
        vis = small.copy()
        cv2.rectangle(vis, (cx1,cy1), (cx2,cy2), (0,255,0), 2)
        cv2.putText(vis, f"Samples: {len(samples)}  (c=cap, f=fit, q=quit)", (8,20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        cv2.imshow("MiDaS Calibrate", vis)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        if key == ord('c'):
            try:
                inb = prepare_input(transform, small, device)
                depth = mids_to_depth(midas, inb, (small.shape[0], small.shape[1]))
                region = depth[cy1:cy2, cx1:cx2]
                med = float(np.median(region))
                print(f"Captured pred_median = {med:.6f}")
                # ask user for real distance
                real = input("Enter real distance in meters (e.g. 2.0): ").strip()
                try:
                    real_m = float(real)
                    samples.append((med, real_m))
                    print("Saved sample:", samples[-1])
                except:
                    print("Invalid number. sample discarded.")
            except Exception as e:
                print("Error capturing depth:", e)
                traceback.print_exc()
        if key == ord('f'):
            if len(samples) < 3:
                print("Need >=3 samples to fit. have:", len(samples))
            else:
                fit_and_save(samples)
                print("Fit complete. continue collecting or press q to quit.")
    cap.release()
    cv2.destroyAllWindows()
    print("Exiting. Collected samples:", len(samples))

if __name__ == "__main__":
    main()
