import time

class AlertEngine:
    def __init__(self):
        self.PRIORITY = ["person", "pothole", "stairs", "traffic_cone", "stop_sign", "chair", "bench"]
        self.alert_history = {}  # Tracks consecutive frames a label is seen

    def get_direction(self, x_center, frame_width):
        left_th = frame_width / 3.0
        right_th = 2.0 * frame_width / 3.0
        
        if x_center < left_th:
            return "left"
        elif x_center > right_th:
            return "right"
        else:
            return "ahead"

    def filter_priority(self, objects):
        # Create events tuple (priority_index, object_data)
        events = []
        for obj in objects:
            label = obj["label"]
            pr_idx = self.PRIORITY.index(label) if label in self.PRIORITY else len(self.PRIORITY)
            events.append((pr_idx, obj))
            
        # Sort by highest priority (lowest index)
        events.sort(key=lambda x: x[0])
        return [e[1] for e in events]

    def generate_alerts(self, objects, frame_width):
        alerts = []
        current_frame_labels = set()
        
        # Hydrate direction into the objects for API consistency
        for obj in objects:
            if "bbox" in obj:
                cx = (obj["bbox"][0] + obj["bbox"][2]) / 2.0
                obj["direction"] = self.get_direction(cx, frame_width)
            else:
                obj["direction"] = "unknown"
                
        filtered_objects = self.filter_priority(objects)
        
        for obj in filtered_objects:
            label = obj["label"]
            current_frame_labels.add(label)
            
            # --- Alert Stability Filter (Critical) ---
            self.alert_history[label] = self.alert_history.get(label, 0) + 1
            if self.alert_history[label] < 1:
                continue # Suppress flicker, wait for consecutive frames
            
            meters = obj.get("distance")
            conf = obj.get("confidence", 0)
            dir_text = obj.get("direction", "ahead")

            msg = None
            dir_phrase = f"on {dir_text}" if dir_text in ["left", "right"] else "ahead"
            
            if meters is not None and meters < 0.6:
                msg = f"{label} very close {dir_phrase}, step back!"
            elif meters is not None and meters < 1.0:
                msg = f"{label} {dir_phrase}, very close."
            elif meters is not None:
                msg = f"{label} {dir_phrase} at {meters} meters"
            else:
                if conf >= 0.10:
                    msg = f"{label} {dir_phrase}"
            
            if msg:
                alerts.append(msg)
                
        # Reset stability history for items that disappeared
        for k in list(self.alert_history.keys()):
            if k not in current_frame_labels:
                self.alert_history[k] = 0
                
        return {"alerts": alerts, "objects": objects}
