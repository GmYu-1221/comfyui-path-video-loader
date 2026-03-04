import os
from typing import List, Union

import cv2
import numpy as np
import torch

# ---------- helpers ----------
def _ensure_path(x: Union[str, List[str]]) -> str:
    # VHS 的 Filenames 输出有时是 list[str]，有时是 str
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("Empty filenames list.")
        return str(x[-1])  # 默认取最后一个（通常是最新生成的那个）
    return str(x)

def _bgr_to_rgb_float01(frame_bgr: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0

def _to_comfy_image_batch(frames_rgb01: List[np.ndarray]) -> torch.Tensor:
    # ComfyUI IMAGE: shape [B, H, W, C], float32 0..1
    arr = np.stack(frames_rgb01, axis=0)  # [B,H,W,C]
    return torch.from_numpy(arr)

# ---------- node ----------
class LoadVideoFromPath:
    """
    Input:  video_path (STRING or LIST[STRING])
    Output: images (IMAGE batch), fps (FLOAT), frame_count (INT), used_path (STRING)
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 这里用 STRING，ComfyUI 会允许接其它节点的 STRING 输出
                "video_path": ("STRING", {"default": ""}),
                "max_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 1000}),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("images", "fps", "frame_count", "used_path")
    FUNCTION = "load"
    CATEGORY = "video"

    def load(self, video_path, max_frames, skip_first_frames, select_every_nth):
        path = _ensure_path(video_path).strip()

        if not path:
            raise ValueError("video_path is empty.")

        # 常见情况：VHS 输出是相对 output 目录的路径；你也可以改成绝对路径
        # 如果你想自动补全到 ComfyUI output 目录，可在这里加逻辑：
        # path = os.path.join(os.getcwd(), "output", path)  # 按需启用

        if not os.path.exists(path):
            raise FileNotFoundError(f"Video file not found: {path}")

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0:
            fps = 0.0

        # 跳过前面帧
        if skip_first_frames > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, skip_first_frames)

        frames = []
        idx = 0
        read_count = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            # 选择每 nth 帧
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