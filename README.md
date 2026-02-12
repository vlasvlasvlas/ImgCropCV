
> 🇬🇧 **English** | [🇪🇸 Español](README.es.md)

# ImgCropCV

**Smart image cropping** using YOLO-World object detection for government platforms that require photos in multiple formats.


## Motivation

Government project management platforms require uploading images in multiple formats (high, medium, low resolution). Doing this manually is tedious, and automating it without criteria can produce crops that include irrelevant areas (sky, ground, empty spaces).

This project automates cropping with **intelligent criteria**: using YOLO-World, the script detects relevant objects in the photo (buildings, construction sites, people, machinery, cranes, signs) and centers the crop on those areas of interest.


## What does it do?

Takes photos of public investment projects and generates **3 intelligently cropped versions**, centered on the relevant content of each photo:

| Format | Size        | Suffix     |
|--------|-------------|------------|
| XL     | 1440 × 1080 | `_XL.jpg`  |
| MD     | 632 × 474   | `_MD.jpg`  |
| SM     | 260 × 195   | `_SM.jpg`  |

Accepts **any image format** (JPG, PNG, WEBP, BMP, TIFF, GIF, etc.) — if Pillow can open it, it gets processed.


## Step-by-step workflow

```
 STEP 1 ─── Prepare photos
 │
 │   Copy all original photos to the /input folder
 │   (any format: JPG, PNG, WEBP, etc.)
 │
 ▼
 STEP 2 ─── Run the script
 │
 │   python3 run.py
 │
 ▼
 STEP 3 ─── Interactive menu
 │
 │   The script displays a listing of all photos:
 │
 │     #  File                  Size    Status
 │     1  photo_01.jpg          1.2 MB  ○ pending
 │     2  photo_02.png          843 KB  ✓ processed
 │     3  photo_03.webp         2.1 MB  ○ pending
 │
 │   Options:
 │     [P] Process only pending files
 │     [T] Process ALL (reprocess included)
 │     [L] List files in output folder
 │     [Q] Quit
 │
 │   → Choose P or T to begin
 │
 ▼
 STEP 4 ─── Processing (automatic, per photo)
 │
 │   4a. YOLO-World scans the photo looking for:
 │       "building", "construction", "person", "crane", etc.
 │       (configurable in config.json)
 │
 │   4b. If objects found → calculates a FOCAL POINT
 │       (weighted center of detected objects)
 │
 │       If NO objects found → uses SALIENCY MAP
 │       (detects the most visually prominent regions)
 │
 │   4c. Crops the photo centered on the focal point
 │       and generates 3 files:
 │
 │       photo_01_XL.jpg  (1440×1080)
 │       photo_01_MD.jpg  (632×474)
 │       photo_01_SM.jpg  (260×195)
 │
 ▼
 STEP 5 ─── Result
 │
 │   Cropped files are in the /output folder,
 │   ready to upload to the platform.
 │
 │   If the script is run again, already-processed photos
 │   are marked as "✓ processed" and automatically skipped
 │   (unless [T] or --force is used).
 │
 ▼
 DONE!
```


## Requirements

- **Python 3.9+** — https://www.python.org/downloads/
  - On Windows, select "Add to PATH" during installation
- **pip** — Python package installer (comes with Python)
- Approximately **500 MB** of disk space for dependencies (YOLO-World, PyTorch, OpenCV)


## Installation

### 1. Clone or download the repository

```bash
git clone https://github.com/vlasvlasvlas/ImgCropCV.git
cd ImgCropCV
```

### 2. Create a virtual environment

```bash
# Create
python3 -m venv venv

# Activate (Linux / Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `ultralytics` — YOLO-World (zero-shot object detection)
- `opencv-python` + `opencv-contrib-python` — image processing and saliency detection
- `Pillow` — crop, resize, and optimized saving

> **Note:** The first run will automatically download the YOLO-World model (~25 MB). This only happens once.


## Usage

### Interactive mode (default)

```bash
python3 run.py
```

Running without parameters opens an **interactive menu** that lists all images with their status and lets you choose what to process.

### Automatic mode (no menu, for scripts or batch processing)

```bash
# Process pending images automatically
python3 run.py --auto

# Reprocess everything
python3 run.py --auto --force

# Preview what would be processed
python3 run.py --dry-run

# Specify folders
python3 run.py --auto --input photos --output processed

# Parallel processing with 4 workers
python3 run.py --auto --workers 4

# Custom config file
python3 run.py --config my_config.json
```

### Command-line options

| Option | Short | Description |
|--------|-------|-------------|
| `--auto` | | Process without interactive menu |
| `--config` | `-c` | Path to config file (default: `config.json`) |
| `--input` | `-i` | Input folder (overrides config) |
| `--output` | `-o` | Output folder (overrides config) |
| `--extension` | `-e` | Filter by extension (e.g. `.jpg`) |
| `--force` | `-f` | Reprocess already-processed images |
| `--dry-run` | `-n` | Only show what would be processed |
| `--workers` | `-w` | Workers for parallel processing (default: `1`) |
| `--quality` | `-q` | JPEG output quality, 1-100 (default: `90`) |


## Configuration

Edit `config.json`:

```json
{
    "language": "en",
    "formatos": {
        "_XL": { "width": "1440", "height": "1080" },
        "_MD": { "width": "632",  "height": "474"  },
        "_SM": { "width": "260",  "height": "195"  }
    },
    "archivos": {
        "carpeta_in": "input",
        "carpeta_out": "output"
    },
    "detection": {
        "prompts": ["building", "construction", "person", "worker",
                    "crane", "machinery", "sign", "road", "house", "truck"],
        "model": "yolov8s-worldv2",
        "confidence_threshold": 0.15
    }
}
```

### `language`

Defines the interface language.
- `"en"`: English (default)
- `"es"`: Spanish

### `formatos` section

Defines output sizes. Each entry generates a file with the corresponding suffix. You can add, remove, or modify formats to match the target platform's requirements.

### `archivos` section

- `carpeta_in`: folder where original photos are placed
- `carpeta_out`: folder where cropped photos are saved

### `detection` section

- `prompts`: list of English words describing objects to look for in photos. YOLO-World understands these words and searches for those objects to center the crop. **Adjust based on photo context:**
  - Construction photos: `["building", "construction", "crane", "worker", "machinery"]`
  - Event photos: `["person", "crowd", "podium", "sign", "banner"]`
  - Rural photos: `["house", "road", "bridge", "field", "fence"]`
- `model`: YOLO-World model to use. `yolov8s-worldv2` is the lightest (~25 MB)
- `confidence_threshold`: minimum confidence to consider a detection (0.0 - 1.0). Lower values detect more objects with less certainty


## Supported image formats

The script accepts **any image format that Pillow can open**, including: JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, and more. No need to convert photos before processing.


## Logging

The script automatically creates a `logs/` folder and saves a daily log file (e.g., `log_2024-05-20.txt`).
These logs contain detailed information about operations, successful processing, errors, and timestamps, useful for auditing or debugging batch processes.


## Project structure

```
ImgCropCV/
├── logs/               # ← Daily execution logs
├── run.py              # Main script with interactive menu and CLI
├── smart_crop.py       # YOLO-World detection + saliency + crop module
├── config.json         # Format, folder, and detection configuration
├── requirements.txt    # Python dependencies
├── input/              # ← Place original photos here
├── output/             # ← Cropped photos go here
├── README.md           # Documentation (English)
└── README.es.md        # Documentation (Spanish)
```


## Tech stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Object detection | **YOLO-World** (Ultralytics) | Zero-shot text-prompted detection, understands "building", "person", etc. without training |
| Fallback | **OpenCV Saliency** | Detects salient regions when YOLO-World finds no objects |
| Crop + Resize | **Pillow** | Focal point-centered crop + LANCZOS resizing |
| Image validation | **Pillow** | Verifies a file is a valid image regardless of extension |
| Runtime | **Python 3.9+** | Command-line script |


## Execution example

```
08:55:13 │ INFO    │ [1/4] demo01.jpg
08:55:14 │ INFO    │   Detected 1 objects: crane(0.16)
08:55:14 │ INFO    │   Focal point: (0.52, 0.85) [yolo-world, conf=0.16]
08:55:14 │ INFO    │   → demo01_XL.jpg (1440×1080)
08:55:14 │ INFO    │   → demo01_MD.jpg (632×474)
08:55:14 │ INFO    │   → demo01_SM.jpg (260×195)
08:55:14 │ INFO    │ [2/4] demo02.jpg
08:55:14 │ INFO    │   Detected 3 objects: crane(0.37), crane(0.25), building(0.25)
08:55:15 │ INFO    │   Focal point: (0.48, 0.56) [yolo-world, conf=0.29]
08:55:15 │ INFO    │   → demo02_XL.jpg (1440×1080)
08:55:15 │ INFO    │   → demo02_MD.jpg (632×474)
08:55:15 │ INFO    │   → demo02_SM.jpg (260×195)
```


## Detection model: YOLO-World

Smart cropping uses **YOLO-World**, a real-time open-vocabulary object detection model, developed by **Tencent AI Lab** and published at **CVPR 2024**.

| Info | Details |
|------|---------|
| **Model used** | `yolov8s-worldv2` (Small variant, v2) |
| **Model weight** | ~25 MB (auto-downloaded on first run) |
| **Capability** | Detects objects from text descriptions, no training needed |
| **Architecture** | Based on YOLOv8 + CLIP text encoder |
| **Paper** | [YOLO-World: Real-Time Open-Vocabulary Object Detection](https://arxiv.org/abs/2401.17270) (arXiv, 2024) |
| **Authors** | Tianheng Cheng, Lin Song, Yixiao Ge, Wenyu Liu, Xinggang Wang, Ying Shan |
| **Source code** | [AILab-CVC/YOLO-World](https://github.com/AILab-CVC/YOLO-World) (GitHub) |
| **Integration** | [Ultralytics YOLO-World](https://docs.ultralytics.com/models/yolo-world/) (documentation) |


## Licenses

| Component | License | Note |
|-----------|---------|------|
| **YOLO-World** (model) | [GPL-3.0](https://github.com/AILab-CVC/YOLO-World/blob/master/LICENSE) | Allows commercial use; derivative works must keep the same license |
| **Ultralytics** (framework) | [AGPL-3.0](https://github.com/ultralytics/ultralytics/blob/main/LICENSE) | Requires open-sourcing the entire project, or a commercial license |
| **OpenCV** | [Apache 2.0](https://github.com/opencv/opencv/blob/master/LICENSE) | Free for commercial and non-commercial use |
| **Pillow** | [HPND](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | Permissive, similar to MIT |
