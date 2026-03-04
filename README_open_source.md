# comfyui-path-video-loader

A small ComfyUI custom node that loads a video from a **connectable path input** (STRING), so you can wire it to outputs such as **comfyui-videohelpersuite** `Video Combine → Filenames`.

This is especially useful when your video loader node only provides a file-picker UI (no input socket), but you want to **pipe the freshly-saved output video** into the next stage of a workflow (e.g., `continue_motion` / segment stitching).

---

## Features

- ✅ Accepts **video path as input** (`STRING`)
- ✅ Works with **VHS `Video Combine` → `Filenames`** output
- ✅ Decodes video into a ComfyUI `IMAGE` batch (`[B,H,W,C]`, float32, 0..1)
- ✅ Basic controls: `skip_first_frames`, `select_every_nth`, `max_frames`
- ✅ Returns `fps`, `frame_count`, and `used_path` for debugging

---

## Node

### Load Video From Path (Connectable)

**Category:** `video`

#### Inputs

- `video_path` (`STRING`): path to a video file  
  - If a list-like value is passed (some nodes output a list of filenames), the node will use the **last** entry.
- `max_frames` (`INT`): maximum number of frames to output  
  - `0` = no limit
- `skip_first_frames` (`INT`): number of frames to skip from the start
- `select_every_nth` (`INT`): keep every Nth frame (e.g., `2` keeps 1/2 frames)

#### Outputs

- `images` (`IMAGE`): image batch of decoded frames
- `fps` (`FLOAT`): detected fps (0 if unknown)
- `frame_count` (`INT`): number of decoded frames
- `used_path` (`STRING`): resolved path the node actually opened

---

## Installation

### Option A — Git clone (recommended)

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/GmYu-1221/comfyui-path-video-loader.git
```

Restart ComfyUI.

### Dependencies

This node uses OpenCV to decode video.

```bash
pip install opencv-python
```

> If you're using ComfyUI in a venv/conda environment, make sure you run the pip install inside that environment.

---

## Quick Start

### Use with VHS Video Combine → Filenames

1. Add **VHS `Video Combine`** (from `comfyui-videohelpersuite`) and enable `save_output`.
2. Add **Load Video From Path (Connectable)**.
3. Connect:
   - `Video Combine` **Filenames** → `Load Video From Path` **video_path**
4. Use `images` output anywhere you need an `IMAGE` batch (e.g., `WanAnimateToVideo.continue_motion`).

Example settings for taking the **last N frames**:

- First segment length: `121`
- Tail frames `N`: `16`
- For the loader:
  - `skip_first_frames = 121 - 16 = 105`
  - `max_frames = 16`

---

## Notes / Troubleshooting

### 1) Relative vs absolute paths

Some nodes output paths relative to ComfyUI `output/`.  
If you see `File not found`, try:

- Pass an **absolute path**, or
- Adjust your upstream node to output full paths.

(If needed, a future update can add automatic `output/` prefix resolution.)

### 2) H.265 / 10-bit decode issues

OpenCV decode support depends on how it was built.  
If you run into decode failures with H.265/10-bit videos, consider outputting H.264 first, or open an issue and we can add an ffmpeg-based decoder option.

---

## Development

Pull requests are welcome. Please include:

- OS / Python version
- ComfyUI version
- Sample path format (absolute/relative)
- Minimal repro steps

---

## License

MIT (recommended). Add a `LICENSE` file if you plan to share/distribute.
