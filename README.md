# 🖼️ Bad Image Finder

<div align="center">

![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Colorful](https://img.shields.io/badge/output-colorful-orange)

**A lightning-fast tool to find and clean up corrupt image files from your photo collection.**

*Created by [Richard Young](https://github.com/ricyoung)*

</div>

## ✨ Features

- **Supports Multiple Image Formats**:
  - 📸 **JPEG** (.jpg, .jpeg, .jfif, etc.)
  - 🎨 **PNG** (.png)
  - 📄 **TIFF** (.tiff, .tif)
  - 🎭 **GIF** (.gif)
  - 🖼️ **BMP** (.bmp)
  - 🌐 **WebP** (.webp)
  - 📱 **HEIC** (.heic)
- **High Performance**: Parallel processing to handle thousands of images efficiently
- **Thorough Validation**: Checks both image headers and data to identify corruption
- **Multiple Operation Modes**:
  - 🔍 **Dry Run** - Preview corrupt files with no changes (default)
  - 🗑️ **Delete** - Permanently remove corrupt files
  - 📦 **Move** - Relocate corrupt files to a separate directory
  - 🔧 **Repair** - Attempt to fix corrupted images
  - ⏸️ **Resume** - Continue interrupted scans from where they left off
- **Beautiful Interface**:
  - 🌈 **Colorful Output** - Color-coded progress bars and logs
  - 📊 **Visual Progress** - Real-time progress tracking with ETA
  - 📈 **Rich Reporting** - Space savings and processing metrics
- **Flexible Configuration**:
  - Control recursion depth
  - Adjust worker count
  - Filter by image format
  - Save reports for later review

## 📋 Requirements

- Python 3.6+
- Required packages:
  - [Pillow](https://pillow.readthedocs.io/) - Python Imaging Library
  - [tqdm](https://github.com/tqdm/tqdm) - Progress bar
  - [humanize](https://github.com/jmoiron/humanize) - Human-readable metrics
  - [colorama](https://github.com/tartley/colorama) - Cross-platform colored terminal output

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/ricyoung/bad-jpg-finder.git
cd bad-jpg-finder

# Install dependencies
pip install -r requirements.txt

# Make executable (Unix/macOS)
chmod +x find_bad_images.py
```

## 🧰 Usage

### Basic (Safe) Mode

```bash
./find_bad_images.py /path/to/images
```

This performs a dry run, showing which files would be deleted without making changes.

### Delete Mode

```bash
./find_bad_images.py /path/to/images --delete
```

⚠️ **Warning**: This permanently deletes corrupt image files!

### Move Mode

```bash
./find_bad_images.py /path/to/images --move-to /path/to/corrupt_folder
```

Safely relocates corrupt files to a separate directory for review.

### Filter By Format

```bash
# Check only JPEG files
./find_bad_images.py /path/to/images --jpeg

# Check only PNG files
./find_bad_images.py /path/to/images --png

# Check specific formats
./find_bad_images.py /path/to/images --formats JPEG PNG TIFF
```

### Repair Mode

```bash
# Attempt to repair corrupt images (creates backups first)
./find_bad_images.py /path/to/images --repair --backup-dir /path/to/backups

# Repair and save a report of fixed files
./find_bad_images.py /path/to/images --repair --repair-report repaired_files.txt
```

### Progress Saving and Resuming

```bash
# List all saved sessions
./find_bad_images.py --list-sessions

# Resume a previously interrupted session
./find_bad_images.py --resume abc123def456

# Customize progress saving interval (default: 5 minutes)
./find_bad_images.py /path/to/images --save-interval 10

# Disable progress saving
./find_bad_images.py /path/to/images --save-interval 0
```

### All Options

```
usage: find_bad_images.py [-h] [--list-sessions] [--delete] [--move-to MOVE_TO]
                          [--workers WORKERS] [--non-recursive] [--output OUTPUT]
                          [--verbose] [--no-color] [--version] [--repair]
                          [--backup-dir BACKUP_DIR] [--repair-report REPAIR_REPORT]
                          [--formats {JPEG,PNG,GIF,TIFF,BMP,WEBP,ICO,HEIC} [...]]
                          [--jpeg] [--png] [--tiff] [--gif] [--bmp]
                          [--save-interval SAVE_INTERVAL] [--progress-dir PROGRESS_DIR]
                          [--resume SESSION_ID]
                          [directory]

positional arguments:
  directory         Directory to search for image files

optional arguments:
  -h, --help        Show this help message and exit
  --list-sessions   List all saved sessions
  --delete          Delete corrupt image files (without this flag, runs in dry-run mode)
  --move-to MOVE_TO Move corrupt files to this directory instead of deleting them
  --workers WORKERS Number of worker processes (default: CPU count)
  --non-recursive   Only search in the specified directory, not subdirectories
  --output OUTPUT   Save list of corrupt files to this file
  --verbose, -v     Enable verbose logging
  --no-color        Disable colored output (useful for logs or non-interactive terminals)
  --version         Show program's version number and exit

Repair options:
  --repair          Attempt to repair corrupt image files
  --backup-dir BACKUP_DIR
                    Directory to store backups of files before repair
  --repair-report REPAIR_REPORT
                    Save list of repaired files to this file

Image format options:
  --formats {JPEG,PNG,GIF,TIFF,BMP,WEBP,ICO,HEIC} [...]
                    Image formats to check (default: all formats)
  --jpeg            Check JPEG files only
  --png             Check PNG files only
  --tiff            Check TIFF files only
  --gif             Check GIF files only
  --bmp             Check BMP files only

Progress options:
  --save-interval SAVE_INTERVAL
                    Save progress every N minutes (0 to disable progress saving, default: 5)
  --progress-dir PROGRESS_DIR
                    Directory to store progress files
  --resume SESSION_ID
                    Resume from a previously saved session
```

## 🔍 How It Works

<div align="center">
<img src="https://raw.githubusercontent.com/ricyoung/bad-jpg-finder/main/docs/workflow.png" alt="Bad Image Finder Workflow" width="700">
</div>

Bad Image Finder uses a sophisticated multi-step approach to handle corrupt image files:

### 🔎 Validation Process

<table>
<tr>
<td width="80" align="center">🧪</td>
<td><b>Header Verification</b><br>Examines file headers to ensure they match proper image format specifications</td>
</tr>
<tr>
<td align="center">🔬</td>
<td><b>Data Validation</b><br>Attempts full data loading to detect issues beyond headers</td>
</tr>
<tr>
<td align="center">📊</td>
<td><b>Error Classification</b><br>Categorizes corruption issues for optimal repair strategy selection</td>
</tr>
</table>

This multi-layered approach catches a wide range of common image corruption problems:
- Truncated downloads
- Partially written files
- Damaged headers
- Internal data corruption
- Invalid encoding

### 🔧 Repair Process

When repair mode is enabled, the tool intelligently attempts to rescue damaged files:

<table>
<tr>
<td width="80" align="center">🔍</td>
<td><b>Smart Diagnosis</b><br>Identifies the specific type and location of corruption</td>
</tr>
<tr>
<td align="center">💾</td>
<td><b>Safe Backup</b><br>Creates a backup of the original file before attempting repairs</td>
</tr>
<tr>
<td align="center">🛠️</td>
<td><b>Format-Specific Repair</b><br>Applies specialized techniques based on file format:
<ul>
<li><b>JPEG</b>: Handles truncation, enables partial loading, optimizes compression</li>
<li><b>PNG</b>: Attempts chunk repair, rebuilds critical sections</li>
<li><b>GIF</b>: Fixes frame data, repairs header structures</li>
</ul>
</td>
</tr>
<tr>
<td align="center">✅</td>
<td><b>Validation Check</b><br>Verifies the repaired file is now properly loadable</td>
</tr>
</table>

### ⏱️ Progress Saving System

For large collections, an intelligent progress tracking system prevents wasted work:

<table>
<tr>
<td width="80" align="center">🏷️</td>
<td><b>Unique Session IDs</b><br>Generates cryptographic hashes based on scan parameters for reliable session tracking</td>
</tr>
<tr>
<td align="center">⏰</td>
<td><b>Automatic Checkpoints</b><br>Saves progress at regular intervals with minimal performance impact</td>
</tr>
<tr>
<td align="center">🛑</td>
<td><b>Interrupt Protection</b><br>Detects Ctrl+C and other interruptions, gracefully saves state before exit</td>
</tr>
<tr>
<td align="center">⏯️</td>
<td><b>Smart Resumption</b><br>Continues processing exactly where it left off, skipping already processed files</td>
</tr>
<tr>
<td align="center">📋</td>
<td><b>Session Management</b><br>Easy-to-use commands for listing, inspecting, and resuming past sessions</td>
</tr>
</table>

<div align="center">
<b>Supported Repair Formats:</b> JPEG, PNG, GIF
</div>

## 📊 Performance

- **Processing Speed**: ~1000 images per minute on a modern quad-core CPU
- **Memory Usage**: Minimal (~50MB base + ~2MB per worker)
- **CPU Usage**: Scales efficiently with available cores

## 📋 Examples

### Check a large photo library and save report

```bash
./find_bad_images.py /Volumes/Photos --output corrupt_photos.txt --verbose
```

### Process a NAS archive with limited CPU impact

```bash
./find_bad_images.py /mnt/nas/archive --workers 2
```

### Quick check of recent imports

```bash
./find_bad_images.py ~/Pictures/imports --non-recursive
```

### Clean up and reclaim space immediately

```bash
./find_bad_images.py /Volumes/ExternalDrive --delete --verbose
```

### Disable colorful output for log files

```bash
./find_bad_images.py /Volumes/Photos --output corrupt_photos.txt --no-color > logfile.txt
```

### Check RAW images and JPEG files

```bash
./find_bad_images.py /Volumes/Photos --formats JPEG TIFF
```

### Repair corrupted images from a camera memory card

```bash
./find_bad_images.py /Volumes/MEMORY_CARD --repair --backup-dir ~/Desktop/image_backups --verbose
```

### Process a huge image collection with resumable progress

```bash
# Start processing a large image collection
./find_bad_images.py /Volumes/BigStorage --save-interval 10

# If interrupted, list available sessions
./find_bad_images.py --list-sessions

# Resume from where you left off
./find_bad_images.py --resume abc123def456
```

## 🤝 Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.

---

<div align="center">
<img src="https://raw.githubusercontent.com/ricyoung/bad-jpg-finder/main/preview.gif" alt="Bad Image Finder in action" width="700">

Made with ❤️ by Richard Young
</div>