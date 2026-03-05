import os
import ast
from typing import Any, List, Optional, Sequence

import cv2
import numpy as np
import torch


# -------------------------
# Helpers
# -------------------------
def _pick_first_nonempty(*vals):
    """
    Pick the first value that is not None and not empty.
    """
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, (list, tuple)) and len(v) == 0:
            continue
        return v
    return None


def _choose_best_path(paths: Sequence[Any]) -> str:
    """
    Given a list/tuple of candidate paths, choose the best video file path.

    Priority:
      1) .mp4 without '-audio' suffix
      2) other common video formats
      3) fallback: last entry stringified
    """
    # Normalize to str list
    s_paths = [p for p in paths if isinstance(p, str) and p.strip()]

    # 1) Prefer normal mp4 (not -audio)
    mp4s = [p for p in s_paths if p.lower().endswith(".mp4") and "-audio" not in p.lower()]
    if mp4s:
        return mp4s[-1]

    # 2) Other common video formats
    exts = (".mp4", ".mov", ".mkv", ".webm", ".avi")
    vids = [p for p in s_paths if p.lower().endswith(exts)]
    if vids:
        return vids[-1]

    # 3) Fallback: last item
    if s_paths:
        return s_paths[-1]
    return str(paths[-1]) if len(paths) > 0 else ""


def _ensure_path(x: Any) -> str:
    """
    Make sure we resolve input into a single file path string.

    Handles:
      - str path: "/a/b.mp4"
      - str that looks like a python list: "['a.png','b.mp4','c-audio.mp4']"
      - list/tuple: ["a.png","b.mp4","c-audio.mp4"]
      - dict: {"filenames":[...]} / {"filename":...} / {"path":...}
      - custom objects: will be stringified and then parsed if list-like
    """

    def _parse_list_string(s: str) -> Optional[str]:
        s = s.strip()
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)) and len(parsed) > 0:
                    return _choose_best_path(parsed)
            except Exception:
                return None
        return None

    # 1) string: maybe already a path, or a list-like string
    if isinstance(x, str):
        parsed = _parse_list_string(x)
        return parsed if parsed is not None else x.strip()

    # 2) list/tuple
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("Empty filenames list.")
        return _choose_best_path(x)

    # 3) dict
    if isinstance(x, dict):
        for k in ("filenames", "filename", "path", "paths"):
            if k in x:
                v = x[k]
                if isinstance(v, (list, tuple)) and len(v) > 0:
                    return _choose_best_path(v)
                # v might still be a list-like string
                if isinstance(v, str):
                    parsed = _parse_list_string(v)
                    return parsed if parsed is not None else v.strip()
                return str(v)

    # 4) custom objects: stringify -> parse if list-like -> else return string
    s = str(x).strip()
    parsed = _parse_list_string(s)
    return parsed if parsed is not None else s

def _resolve_output_path(path: str) -> str:
    """
    Resolve path when upstream returns a relative path to ComfyUI output/.

    - If path exists as-is, return it.
    - Else try: <ComfyUI root>/output/<path>
    """
    path = path.strip()
    if os.path.exists(path):
        return path

    # __file__ = <ComfyUI>/custom_nodes/<repo>/__init__.py
    comfy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidate = os.path.join(comfy_root, "output", path)
    if os.path.exists(candidate):
        return candidate

    return path


def _bgr_to_rgb_float01(frame_bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0


def _to_comfy_image_batch(frames_rgb01: List[np.ndarray]) -> torch.Tensor:
    # ComfyUI IMAGE format: [B, H, W, C], float32 0..1
    arr = np.stack(frames_rgb01, axis=0)
    return torch.from_numpy(arr)


# -------------------------
# Node
# -------------------------
class LoadVideoFromPath:
    """
    Load video frames from a connectable path-like input.

    Designed to work with:
      - VHS Video Combine -> Filenames output (often VHS_FILENAMES / FILENAMES)
      - or manual STRING path input (video_path_text)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Manual fallback if you don't connect any filenames socket
                "video_path_text": ("STRING", {"default": ""}),
                "max_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 1000}),
            },
            "optional": {
                # Try to cover VHS socket types.
                "filenames_vhs": ("VHS_FILENAMES",),
                "filenames": ("FILENAMES",),
                # wildcard fallback; may or may not connect in some setups
                "filenames_any": ("*",),
            },
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("images", "fps", "frame_count", "used_path")
    FUNCTION = "load"
    CATEGORY = "video"

    def load(
        self,
        video_path_text: str,
        max_frames: int,
        skip_first_frames: int,
        select_every_nth: int,
        filenames_vhs: Optional[Any] = None,
        filenames: Optional[Any] = None,
        filenames_any: Optional[Any] = None,
    ):
        # Pick the best upstream value, fallback to manual text path
        src = _pick_first_nonempty(filenames_vhs, filenames, filenames_any, video_path_text)
        if src is None:
            raise ValueError("No input provided: connect Filenames socket or fill video_path_text.")

        # Resolve to a single string path
        path = _ensure_path(src)

        # Extra safety: if something still isn't a string, coerce again
        if isinstance(path, (list, tuple, dict)):
            path = _ensure_path(path)

        path = _resolve_output_path(path)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Video file not found: {path}")

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0:
            fps = 0.0

        if skip_first_frames > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, skip_first_frames)

        frames = []
        idx = 0
        read_count = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if idx % select_every_nth == 0:
                frames.append(_bgr_to_rgb_float01(frame))
                read_count += 1
                if max_frames > 0 and read_count >= max_frames:
                    break

            idx += 1

        cap.release()

        if len(frames) == 0:
            raise RuntimeError("No frames decoded (check skip/select/max settings).")

        images = _to_comfy_image_batch(frames)
        return (images, float(fps), int(images.shape[0]), path)


# -------------------------
# Registration
# -------------------------
NODE_CLASS_MAPPINGS = {
    "LoadVideoFromPath": LoadVideoFromPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadVideoFromPath": "Load Video From Path (Connectable)"
}

