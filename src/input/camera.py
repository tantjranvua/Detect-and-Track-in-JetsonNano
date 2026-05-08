import cv2
import sys
from typing import Any, Dict


def _build_jetson_csi_pipeline(width: int, height: int, fps: int, flip_method: int) -> str:
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        f"width=(int){width}, height=(int){height}, format=(string)NV12, "
        f"framerate=(fraction){fps}/1 ! "
        f"nvvidconv flip-method={int(flip_method)} ! "
        "video/x-raw, width=(int){w}, height=(int){h}, format=(string)BGRx ! "
        "videoconvert ! video/x-raw, format=(string)BGR ! appsink"
    ).format(w=int(width), h=int(height))


def resolve_camera_runtime(runtime_cfg: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "camera_index": int(runtime_cfg.get("camera_index", 0)),
        "camera_backend": str(runtime_cfg.get("camera_backend", "auto")),
        "camera_use_csi": bool(runtime_cfg.get("camera_use_csi", False)),
        "camera_flip_method": int(runtime_cfg.get("camera_flip_method", 0)),
        "camera_gstreamer_pipeline": str(runtime_cfg.get("camera_gstreamer_pipeline", "")),
        "width": int(runtime_cfg.get("width", 1280)),
        "height": int(runtime_cfg.get("height", 720)),
        "input_fps": int(runtime_cfg.get("input_fps", 10)),
    }

    active_name = str(runtime_cfg.get("active_camera_profile", "")).strip()
    profiles = runtime_cfg.get("camera_profiles", {})
    if not active_name or not isinstance(profiles, dict):
        return base

    profile_cfg = profiles.get(active_name)
    if not isinstance(profile_cfg, dict):
        print(f"[WARN] Khong tim thay camera profile: {active_name}. Dung cau hinh runtime mac dinh")
        return base

    merged = dict(base)
    merged.update(profile_cfg)
    merged["camera_index"] = int(merged.get("camera_index", base["camera_index"]))
    merged["camera_backend"] = str(merged.get("camera_backend", base["camera_backend"]))
    merged["camera_use_csi"] = bool(merged.get("camera_use_csi", base["camera_use_csi"]))
    merged["camera_flip_method"] = int(merged.get("camera_flip_method", base["camera_flip_method"]))
    merged["camera_gstreamer_pipeline"] = str(merged.get("camera_gstreamer_pipeline", base["camera_gstreamer_pipeline"]))
    merged["width"] = int(merged.get("width", base["width"]))
    merged["height"] = int(merged.get("height", base["height"]))
    merged["input_fps"] = int(merged.get("input_fps", base["input_fps"]))
    return merged


def open_camera(
    index: int,
    width: int,
    height: int,
    fps: int,
    backend: str = "auto",
    use_csi: bool = False,
    gstreamer_pipeline: str = "",
    flip_method: int = 0,
) -> cv2.VideoCapture:
    backend_norm = str(backend or "auto").strip().lower()

    if bool(use_csi):
        pipeline = str(gstreamer_pipeline or "").strip()
        if not pipeline:
            pipeline = _build_jetson_csi_pipeline(width=width, height=height, fps=fps, flip_method=flip_method)
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            return cap
        print("[WARN] Khong mo duoc camera CSI bang GStreamer, fallback sang camera_index")

    cap = None
    if backend_norm in ("gstreamer", "gst"):
        cap = cv2.VideoCapture(index, cv2.CAP_GSTREAMER)
    elif backend_norm == "v4l2":
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    elif backend_norm == "directshow":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    elif backend_norm == "auto":
        if sys.platform.startswith("linux"):
            cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(index)
        else:
            cap = cv2.VideoCapture(index)
    else:
        cap = cv2.VideoCapture(index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap
