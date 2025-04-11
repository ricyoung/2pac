# 🖼️ Bad Image Finder

<div align="center">

![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Colorful](https://img.shields.io/badge/output-colorful-orange)

**A lightning-fast tool to find and clean up corrupt image files from your photo collection.**

*Created by [Richard Young](https://github.com/ricyoung)*

</div>

## 🚀 What's New in v1.4.0

<table>
<tr>
<td width="80" align="center">🎚️</td>
<td><b>Adjustable Validation Sensitivity</b><br>New command-line option <code>--sensitivity {low,medium,high}</code> lets you control the strictness of image validation to match your needs</td>
</tr>
<tr>
<td align="center">🧩</td>
<td><b>Smart EOF Handling</b><br>New <code>--ignore-eof</code> option allows keeping files that are technically corrupt (missing proper end markers) but still viewable in most applications</td>
</tr>
<tr>
<td align="center">📐</td>
<td><b>Enhanced Format Structure Validation</b><br>Deep JPEG and PNG structure analysis finds corruption that basic validation misses</td>
</tr>
<tr>
<td align="center">⚡</td>
<td><b>Performance Optimizations</b><br>Smarter validation path selection based on sensitivity level improves scanning speed</td>
</tr>
</table>

[Skip to the detailed New Validation System section](#-new-validation-system)

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
- **Advanced Validation Technology**: 
  - 🧐 Checks both image headers and data to identify corruption
  - 🎚️ **NEW:** Adjustable sensitivity levels to balance speed vs thoroughness:
    - **Low:** Basic header checks for quick scans (fastest)
    - **Medium:** Standard validation for most use cases (default)
    - **High:** Deep structure analysis to catch subtle corruption (most thorough)
  - 📐 **NEW:** Format-specific structure validation:
    - JPEG: Verifies marker sequence, EOI presence, segment structure
    - PNG: Validates chunks, CRC checksums, IHAT compression integrity
  - 🧩 **NEW:** Smart EOF handling with `--ignore-eof` option for files that are technically 
    corrupt (missing proper end markers) but still viewable in most applications
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

Safely relocates corrupt files to a separate directory for review instead of deleting them. Use this as an alternative to `--delete` when you want to examine corrupt files before permanently removing them.

The directory structure from the original location is preserved in the destination folder, making it easier to understand where files came from and preventing filename collisions.

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

# Repair and move files that couldn't be repaired
./find_bad_images.py /path/to/images --repair --backup-dir /path/to/backups --move-to /path/to/still_corrupt
```

**Important Notes:**
- `--backup-dir` is used with `--repair` to save original versions of files **before** attempting repairs
- `--move-to` is used to relocate corrupt files that were found (or couldn't be repaired) to another location
- These options serve different purposes: one preserves originals before repair, the other handles corrupt files

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
                          [--resume SESSION_ID] [--sensitivity {low,medium,high}]
                          [--ignore-eof]
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

Validation options:
  --sensitivity {low,medium,high}
                    Set validation sensitivity level: low (basic checks), 
                    medium (standard checks), high (most strict) (default: medium)
  --ignore-eof      Ignore missing end-of-file markers (useful for truncated but viewable files)

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
<tr>
<td align="center">🎚️</td>
<td><b>Sensitivity Levels</b><br>
<ul>
<li><b>Low</b>: Basic checks only (headers and minimal data verification)</li>
<li><b>Medium</b>: Standard validation (balanced between speed and thoroughness)</li>
<li><b>High</b>: Most strict validation (deep format-specific structure checks)</li>
</ul>
</td>
</tr>
<tr>
<td align="center">🧩</td>
<td><b>Format-Specific Validation</b><br>
<ul>
<li><b>JPEG</b>: Verifies markers, EOI (End Of Image) presence, proper structure</li>
<li><b>PNG</b>: Validates chunks, CRC checksums, IDAT structure</li>
<li><b>Other formats</b>: Format-appropriate validation techniques</li>
</ul>
</td>
</tr>
</table>

This multi-layered approach catches a wide range of common image corruption problems:
- Truncated downloads
- Partially written files
- Damaged headers
- Internal data corruption
- Invalid encoding
- Missing end markers
- Incorrect format structure
- Checksum failures

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

### Customize validation strictness

```bash
# Use high sensitivity to catch even minor corruption issues
./find_bad_images.py /Volumes/Photos --sensitivity high

# Use low sensitivity for a quick basic check
./find_bad_images.py /Volumes/Photos --sensitivity low

# Keep truncated but viewable files
./find_bad_images.py /Volumes/Photos --ignore-eof

# Combine options for specific use cases
./find_bad_images.py /Volumes/Photos --sensitivity high --ignore-eof --verbose
```

### Cross-device operations

```bash
# Move corrupt files from an external drive to a local folder while preserving structure
./find_bad_images.py /Volumes/ExternalDrive --move-to ~/Desktop/corrupted
# Result: Files like '/Volumes/ExternalDrive/folder1/subfolder/image.jpg' will be moved to '~/Desktop/corrupted/folder1/subfolder/image.jpg'
```

## 🎚️ New Validation System

The latest version introduces a powerful new validation system with improved control and detection capabilities:

### 1. Sensitivity Levels

<table>
<tr>
<th align="center">Level</th>
<th>Description</th>
<th>Use Case</th>
</tr>
<tr>
<td align="center">Low</td>
<td>
<ul>
<li>Basic header verification only</li>
<li>Minimal data loading checks</li>
<li>Fast but less thorough</li>
</ul>
</td>
<td>
<ul>
<li>Quick initial scan of large collections</li>
<li>When looking for only severely corrupted files</li>
<li>Maximum performance needed</li>
</ul>
</td>
</tr>
<tr>
<td align="center">Medium</td>
<td>
<ul>
<li>Standard header and data validation</li>
<li>Balanced between speed and detection</li>
<li>Catches most common corruption issues</li>
</ul>
</td>
<td>
<ul>
<li>Default for most use cases</li>
<li>Regular maintenance scans</li>
<li>Good balance of speed and thoroughness</li>
</ul>
</td>
</tr>
<tr>
<td align="center">High</td>
<td>
<ul>
<li>Deep structure analysis</li>
<li>Format-specific validation</li>
<li>Checks internal consistency</li>
<li>Most thorough but slower</li>
</ul>
</td>
<td>
<ul>
<li>Archive integrity verification</li>
<li>When preparing critical collections</li>
<li>Finding subtle corruption issues</li>
</ul>
</td>
</tr>
</table>

### 2. New EOF Marker Handling

The new `--ignore-eof` option addresses a common issue with images that are technically corrupt but still usable:

- **What it does**: Ignores missing End-Of-File/Image markers during validation
- **When to use it**: For files that open properly in most viewers but fail strict validation
- **Technical detail**: Many images with truncated data or missing EOI markers can still be displayed correctly by applications that are tolerant of these issues
- **Example scenario**: Images downloaded from the web, processed by certain applications, or transferred with incomplete writes

### 3. Enhanced Format-Specific Validation

The new version includes deep structure validation for common formats:

**JPEG Validation:**
- Validates marker sequence (SOI, APP, COM, SOF, etc.)
- Checks for proper EOI marker presence
- Validates segment structure and lengths
- Detects truncated files and data corruption

**PNG Validation:**
- Verifies PNG signature and header chunk
- Validates critical chunks (IHDR, IDAT, IEND)
- Checks CRC values for all chunks
- Validates chunk sequence and structure
- Detects IDAT compression issues

### 4. Corruption Detection Comparison

<table>
<tr>
<th>Corruption Type</th>
<th align="center">Low Sensitivity</th>
<th align="center">Medium Sensitivity</th>
<th align="center">High Sensitivity</th>
</tr>
<tr>
<td>Severely truncated file</td>
<td align="center">✅</td>
<td align="center">✅</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Invalid image header</td>
<td align="center">✅</td>
<td align="center">✅</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Missing critical data chunks</td>
<td align="center">❌</td>
<td align="center">✅</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Missing EOI/EOF markers</td>
<td align="center">❌</td>
<td align="center">✅</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Invalid chunk sequences (PNG)</td>
<td align="center">❌</td>
<td align="center">❌</td>
<td align="center">✅</td>
</tr>
<tr>
<td>CRC validation errors</td>
<td align="center">❌</td>
<td align="center">❌</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Invalid structure but viewable</td>
<td align="center">❌</td>
<td align="center">❌</td>
<td align="center">✅</td>
</tr>
<tr>
<td>Partially corrupt data</td>
<td align="center">⚠️</td>
<td align="center">✅</td>
<td align="center">✅</td>
</tr>
</table>

✅ = Detected | ❌ = Not detected | ⚠️ = Sometimes detected

### 5. Decision Flowchart: Which Settings to Use?

<table>
<tr>
<td colspan="3" align="center"><b>What's your primary concern?</b></td>
</tr>
<tr>
<td align="center" width="33%"><b>Speed</b><br><i>I need to process quickly</i></td>
<td align="center" width="33%"><b>Balance</b><br><i>I want good detection without sacrificing too much speed</i></td>
<td align="center" width="33%"><b>Thoroughness</b><br><i>I need to find every possible corruption</i></td>
</tr>
<tr>
<td align="center">⬇️</td>
<td align="center">⬇️</td>
<td align="center">⬇️</td>
</tr>
<tr>
<td align="center"><code>--sensitivity low</code></td>
<td align="center"><code>--sensitivity medium</code> (default)</td>
<td align="center"><code>--sensitivity high</code></td>
</tr>
<tr>
<td colspan="3" align="center"><b>Do your images need to strictly follow format specifications?</b></td>
</tr>
<tr>
<td align="center" width="33%"><b>No</b><br><i>I just want viewable images</i></td>
<td align="center" width="33%"><b>Somewhat</b><br><i>I want mostly valid files but some exceptions are ok</i></td>
<td align="center" width="33%"><b>Yes</b><br><i>I need 100% format compliant files</i></td>
</tr>
<tr>
<td align="center">⬇️</td>
<td align="center">⬇️</td>
<td align="center">⬇️</td>
</tr>
<tr>
<td align="center">Add <code>--ignore-eof</code></td>
<td align="center">Consider <code>--ignore-eof</code><br>with <code>--sensitivity high</code></td>
<td align="center">Use without <code>--ignore-eof</code></td>
</tr>
</table>

### 6. Real-World Examples

<table>
<tr>
<th>Scenario</th>
<th>Recommended Settings</th>
<th>Why</th>
</tr>
<tr>
<td>Quick check of large photo library</td>
<td><code>--sensitivity low</code></td>
<td>Fast initial scan to find obviously corrupt files</td>
</tr>
<tr>
<td>Standard maintenance of personal photos</td>
<td><code>--sensitivity medium</code> (default)</td>
<td>Good balance of detection and performance</td>
</tr>
<tr>
<td>Processing web-downloaded images</td>
<td><code>--sensitivity medium --ignore-eof</code></td>
<td>Many web images have missing EOI markers but are still viewable</td>
</tr>
<tr>
<td>Preparing images for professional printing</td>
<td><code>--sensitivity high</code></td>
<td>Ensures highest quality images with no subtle corruption</td>
</tr>
<tr>
<td>Archiving important image collections</td>
<td><code>--sensitivity high</code></td>
<td>Maximum detection ensures long-term preservation</td>
</tr>
<tr>
<td>Recovery after hardware failure</td>
<td><code>--sensitivity high --ignore-eof --repair</code></td>
<td>Find all issues but attempt to keep viewable images</td>
</tr>
</table>

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