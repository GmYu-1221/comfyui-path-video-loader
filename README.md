# comfyui-path-video-loader

**中文（Chinese）**一个小型的 ComfyUI 自定义节点：支持从**可连接的路径输入**（STRING）加载视频，这样你就可以把它接到诸如 **comfyui-videohelpersuite** 的 `Video Combine → Filenames` 这类输出上。

当你使用的视频加载节点**只有文件选择器 UI（没有输入插口）**时，这个节点尤其有用——它可以把**刚保存出来的视频**直接“管道化”地送入工作流的下一阶段（例如 `continue_motion` / 分段拼接）。

**English**A small ComfyUI custom node that loads a video from a **connectable path input** (STRING), so you can wire it to outputs such as **comfyui-videohelpersuite** `Video Combine → Filenames`.

This is especially useful when your video loader node only provides a file-picker UI (no input socket), but you want to **pipe the freshly-saved output video** into the next stage of a workflow (e.g., `continue_motion` / segment stitching).

* * *

## 功能特性 / Features

**中文（Chinese）**

* ✅ 接受**视频路径作为输入**（`STRING`）
* ✅ 可直接对接 **VHS `Video Combine` → `Filenames`** 输出
* ✅ 解码为 ComfyUI `IMAGE` 批（`[B,H,W,C]`，float32，范围 0..1）
* ✅ 提供基础控制参数：`skip_first_frames`、`select_every_nth`、`max_frames`
* ✅ 输出 `fps`、`frame_count`、`used_path`，便于调试

**English**

* ✅ Accepts **video path as input** (`STRING`)
* ✅ Works with **VHS `Video Combine` → `Filenames`** output
* ✅ Decodes video into a ComfyUI `IMAGE` batch (`[B,H,W,C]`, float32, 0..1)
* ✅ Basic controls: `skip_first_frames`, `select_every_nth`, `max_frames`
* ✅ Returns `fps`, `frame_count`, and `used_path` for debugging

* * *

## 节点说明 / Node

### Load Video From Path (Connectable)

**分类 / Category:** `video`

#### 输入 / Inputs

**中文（Chinese）**

* `video_path`（`STRING`）：视频文件路径
  * 如果传入的是“类列表”的值（某些节点会输出文件名列表），本节点默认使用**最后一个**条目。
* `max_frames`（`INT`）：最多输出的帧数
  * `0` = 不限制
* `skip_first_frames`（`INT`）：从开头跳过的帧数
* `select_every_nth`（`INT`）：每隔 N 帧取 1 帧（例如 `2` 表示保留 1/2 的帧）

**English**

* `video_path` (`STRING`): path to a video file
  * If a list-like value is passed (some nodes output a list of filenames), the node will use the **last** entry.
* `max_frames` (`INT`): maximum number of frames to output
  * `0` = no limit
* `skip_first_frames` (`INT`): number of frames to skip from the start
* `select_every_nth` (`INT`): keep every Nth frame (e.g., `2` keeps 1/2 frames)

#### 输出 / Outputs

**中文（Chinese）**

* `images`（`IMAGE`）：解码后的帧序列（IMAGE batch）
* `fps`（`FLOAT`）：检测到的帧率（未知则为 0）
* `frame_count`（`INT`）：解码得到的帧数
* `used_path`（`STRING`）：实际打开的路径（用于排错）

**English**

* `images` (`IMAGE`): image batch of decoded frames
* `fps` (`FLOAT`): detected fps (0 if unknown)
* `frame_count` (`INT`): number of decoded frames
* `used_path` (`STRING`): resolved path the node actually opened

* * *

## 安装 / Installation

### 方案 A — Git clone（推荐）/ Option A — Git clone (recommended)

    cd /path/to/ComfyUI/custom_nodes
    git clone https://github.com/GmYu-1221/comfyui-path-video-loader.git

重启 ComfyUI。Restart ComfyUI.

### 依赖 / Dependencies

**中文（Chinese）**本节点使用 OpenCV 来解码视频。

**English**This node uses OpenCV to decode video.

    pip install opencv-python

> **中文提示**：如果你在 venv/conda 环境中运行 ComfyUI，请确保在对应环境里执行 pip 安装。**English**: If you're using ComfyUI in a venv/conda environment, make sure you run the pip install inside that environment.

* * *

## 快速开始 / Quick Start

### 搭配 VHS Video Combine → Filenames 使用 / Use with VHS Video Combine → Filenames

**中文（Chinese）**

1. 添加 **VHS `Video Combine`**（来自 `comfyui-videohelpersuite`），并启用 `save_output`。
2. 添加 **Load Video From Path (Connectable)**。
3. 连接：
  * `Video Combine` 的 **Filenames** → `Load Video From Path` 的 **video_path**
4. 在任何需要 `IMAGE` 批的地方使用 `images` 输出（例如 `WanAnimateToVideo.continue_motion`）。

**English**

1. Add **VHS `Video Combine`** (from `comfyui-videohelpersuite`) and enable `save_output`.
2. Add **Load Video From Path (Connectable)**.
3. Connect:
  * `Video Combine` **Filenames** → `Load Video From Path` **video_path**
4. Use `images` output anywhere you need an `IMAGE` batch (e.g., `WanAnimateToVideo.continue_motion`).

#### 取“最后 N 帧”的示例参数 / Example settings for taking the last N frames

* 第一段长度 / First segment length：`121`
* 尾帧数量 / Tail frames `N`：`16`
* 加载器参数 / For the loader：
  * `skip_first_frames = 121 - 16 = 105`
  * `max_frames = 16`

* * *

## 说明与排错 / Notes / Troubleshooting

### 1) 相对路径 vs 绝对路径 / Relative vs absolute paths

**中文（Chinese）**某些节点输出的路径是相对于 ComfyUI `output/` 目录的。若出现 `File not found`，可尝试：

* 传入**绝对路径**，或
* 调整上游节点，让它输出完整路径

（后续如有需要，可以加入自动补全 `output/` 前缀的逻辑。）

**English**Some nodes output paths relative to ComfyUI `output/`.If you see `File not found`, try:

* Pass an **absolute path**, or
* Adjust your upstream node to output full paths.

(If needed, a future update can add automatic `output/` prefix resolution.)

### 2) H.265 / 10-bit 解码问题 / H.265 / 10-bit decode issues

**中文（Chinese）**OpenCV 的解码能力取决于其编译方式与系统环境。若 H.265/10-bit 解码失败，可先输出 H.264，或提 Issue，我们可以增加基于 ffmpeg 的解码选项。

**English**OpenCV decode support depends on how it was built.If you run into decode failures with H.265/10-bit videos, consider outputting H.264 first, or open an issue and we can add an ffmpeg-based decoder option.

* * *

## 开发 / Development

**中文（Chinese）**欢迎 PR。请尽量提供：

* 操作系统 / Python 版本
* ComfyUI 版本
* 路径格式示例（绝对/相对）
* 最小复现步骤

**English**Pull requests are welcome. Please include:

* OS / Python version
* ComfyUI version
* Sample path format (absolute/relative)
* Minimal repro steps

* * *

## 许可证 / License

**中文（Chinese）**推荐使用 MIT。如果你计划共享/分发，请添加 `LICENSE` 文件。

**English**MIT (recommended). Add a `LICENSE` file if you plan to share/distribute.
