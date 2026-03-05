import os
import cv2
import numpy as np
import torch
import ast

# ---------- helpers ----------
def _pick_first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        # 有些 socket 会传空字符串/空列表
        if isinstance(v, str) and v.strip() == "":
            continue
        if isinstance(v, (list, tuple)) and len(v) == 0:
            continue
        return v
    return None

def _choose_best_path(paths):
    # 优先：普通 mp4（非 audio）
    mp4s = [p for p in paths if isinstance(p, str) and p.lower().endswith(".mp4") and "-audio" not in p.lower()]
    if mp4s:
        return mp4s[-1]

    # 次选：任意视频
    vids = [p for p in paths if isinstance(p, str) and os.path.splitext(p.lower())[1] in (".mp4", ".mov", ".mkv", ".webm", ".avi")]
    if vids:
        return vids[-1]

    # 兜底：最后一个
    return str(paths[-1]) if paths else ""

def _ensure_path(x) -> str:
    # 1) x 是字符串：可能是正常路径，也可能是 "['a','b']" 这种列表字符串
    if isinstance(x, str):
        s = x.strip()
        # 尝试把“列表字符串”解析成真正 list
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)) and len(parsed) > 0:
                    return _choose_best_path(list(parsed))
            except Exception:
                pass
        return s

    # 2) list/tuple：选最合适的那个
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("Empty filenames list.")
        return _choose_best_path(list(x))

    # 3) dict：尝试常见字段
    if isinstance(x, dict):
        for k in ("filenames", "filename", "path", "paths"):
            if k in x:
                v = x[k]
                if isinstance(v, (list, tuple)) and len(v) > 0:
                    return _choose_best_path(list(v))
                return str(v)

    return str(x)


def _resolve_output_path(path: str) -> str:
    """
    If upstream returns a path relative to ComfyUI output/,
    try to resolve it automatically.
    """
    path = path.strip()
    if os.path.exists(path):
        return path

    # 常见：VHS 只给 "wan2.2/animate/xxx.mp4" 这种相对 output 的路径
    # 这里按 ComfyUI 典型结构：<ComfyUI>/output/<relative>
    # __file__ = <ComfyUI>/custom_nodes/<this_repo>/__init__.py
    comfy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidate = os.path.join(comfy_root, "output", path)
    if os.path.exists(candidate):
        return candidate

    return path  # let caller raise FileNotFoundError with original info

def _bgr_to_rgb_float01(frame_bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0

def _to_comfy_image_batch(frames_rgb01):
    arr = np.stack(frames_rgb01, axis=0)  # [B,H,W,C]
    return torch.from_numpy(arr)


# ---------- node ----------
class LoadVideoFromPath:
    """
    Load video frames from a connectable path-like input.

    You can connect:
      - VHS Video Combine -> Filenames (often VHS_FILENAMES / FILENAMES)
      - or manually provide a STRING path
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 手动输入兜底：你不接线也能用
                "video_path_text": ("STRING", {"default": ""}),
                "max_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 1000}),
            },
            "optional": {
                # 尽量覆盖 VHS/其它视频节点常见的 filenames socket 类型
                "filenames_vhs": ("VHS_FILENAMES",),
                "filenames": ("FILENAMES",),
                # 再给一个 ANY 兜底（部分环境 * 可用，部分不可用）
                "filenames_any": ("*",),
            },
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("images", "fps", "frame_count", "used_path")
    FUNCTION = "load"
    CATEGORY = "video"

    def load(self, video_path_text, max_frames, skip_first_frames, select_every_nth,
             filenames_vhs=None, filenames=None, filenames_any=None):

        src = _pick_first_nonempty(filenames_vhs, filenames, filenames_any, video_path_text)
        if src is None:
            raise ValueError("No input provided: connect Filenames socket or fill video_path_text.")

        path = _ensure_path(src)
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


# ---------- registration ----------
NODE_CLASS_MAPPINGS = {
    "LoadVideoFromPath": LoadVideoFromPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadVideoFromPath": "Load Video From Path (Connectable)"
}

