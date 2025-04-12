# 🔫 2PAC: The Picture Analyzer & Corruption killer

> 2**P**AC stands for: 
> - **P**icture
> - **A**nalyzer & 
> - **C**orruption killer

<div align="center">

![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Colorful](https://img.shields.io/badge/output-colorful-orange)

<img src="docs/2pac.jpg" alt="2PAC Coding" width="400">

**All Eyez On Your Images: A lightning-fast tool to find and whack corrupt image files from your photo collection.**

*"I ain't a killer but don't push me. Corrupt images got their days numbered."*

*Created by [Richard Young](https://github.com/ricyoung)*

[View official logo and usage guidelines](docs/logo.md)

</div>

## 🚀 What's New in v1.5.0

<table>
<tr>
<td width="80" align="center">👁️</td>
<td><b>Visual Corruption Detection</b><br>New command-line option <code>--check-visual</code> analyzes image content to detect visually corrupt files with large gray/black areas</td>
</tr>
<tr>
<td align="center">🔍</td>
<td><b>Adjustable Detection Strictness</b><br>New <code>--visual-strictness {low,medium,high}</code> option lets you control how aggressive the visual corruption detection should be</td>
</tr>
<tr>
<td align="center">🧠</td>
<td><b>Smart Detection Algorithm</b><br>Intelligently distinguishes between corruption and legitimate solid-colored areas like white backgrounds</td>
</tr>
<tr>
<td align="center">🔧</td>
<td><b>Combined Detection Modes</b><br>Can be used with <code>--ignore-eof</code> to find only visually corrupt files while ignoring technical EOF issues</td>
</tr>
</table>

[Skip to the detailed Visual Content Analysis section](#-visual-content-analysis)

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
  - 👁️ **NEW:** Visual corruption detection to find files with gray/black areas
  - 🎚️ Adjustable sensitivity levels to balance speed vs thoroughness:
    - **Low:** Basic header checks for quick scans (fastest)
    - **Medium:** Standard validation for most use cases (default)
    - **High:** Deep structure analysis to catch subtle corruption (most thorough)
  - 🔍 **NEW:** Visual strictness levels to control how aggressively to detect visible corruption:
    - **Low:** Only the most obvious visual corruption (minimal false positives)
    - **Medium:** Balanced visual detection (default)
    - **High:** Catches more subtle visual corruption (may have false positives)
  - 📐 Format-specific structure validation:
    - JPEG: Verifies marker sequence, EOI presence, segment structure
    - PNG: Validates chunks, CRC checksums, IHAT compression integrity
  - 🧩 Smart EOF handling with `--ignore-eof` option for files that are technically 
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
  - Preserve directory structure when moving files

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
git clone https://github.com/ricyoung/2pac.git
cd 2pac

# Install dependencies
pip install -r requirements.txt

# Make executable (Unix/macOS)
chmod +x find_bad_images.py
```

*"They got money for wars, but can't feed the poor." - But we got tools for your images.*

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
                          [--ignore-eof] [--check-visual]
                          [--visual-strictness {low,medium,high}]
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
  --check-visual    Analyze image content to detect visible corruption like gray/black areas
  --visual-strictness {low,medium,high}
                    Set strictness level for visual corruption detection (default: medium)

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
<img src="https://raw.githubusercontent.com/ricyoung/2pac/main/docs/workflow.png" alt="2PAC Workflow" width="700">

*"I see no changes, wake up in the morning and I ask myself, is my image collection worth cleanin'? I don't know."*
</div>

2PAC uses a sophisticated multi-step approach to handle corrupt image files:

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

### Visual corruption detection

```bash
# Find images with visible corruption (gray/black areas)
./find_bad_images.py /Volumes/Photos --check-visual --move-to ~/Desktop/visibly_corrupt

# Ignore technical issues and only find visual corruption
./find_bad_images.py /Volumes/Photos --check-visual --ignore-eof --move-to ~/Desktop/visibly_corrupt

# Use a more conservative detection (fewer false positives)
./find_bad_images.py /Volumes/Photos --check-visual --visual-strictness low

# Use a stricter detection (catches more corruption but may have false positives)
./find_bad_images.py /Volumes/Photos --check-visual --visual-strictness high
```

## 👁️ Visual Content Analysis

The latest version introduces a powerful new visual corruption detection system that can find files with actual visible corruption, even if they pass technical validation checks:

### 1. Types of Visual Corruption Detected

<table>
<tr>
<th>Type</th>
<th>Sample</th>
<th>Description</th>
</tr>
<tr>
<td>Gray Block</td>
<td align="center"><img src="docs/samples/gray_block_corruption.jpg" width="200"></td>
<td>Large areas of uniform gray color that replace image content</td>
</tr>
<tr>
<td>Black Block</td>
<td align="center"><img src="docs/samples/black_block_corruption.jpg" width="200"></td>
<td>Sections of solid black that indicate missing or corrupted data</td>
</tr>
<tr>
<td>Partial Image</td>
<td align="center"><img src="docs/samples/partial_corruption.jpg" width="200"></td>
<td>Bottom or top sections of the image replaced with solid colors</td>
</tr>
<tr>
<td>Normal Image</td>
<td align="center"><img src="docs/samples/perfect_image.jpg" width="200"></td>
<td>For comparison: a normal, uncorrupted image</td>
</tr>
</table>

### 2. Visual Strictness Levels

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
<li>Only detects very obvious corruption</li>
<li>Requires 30%+ of image to be uniform gray/black</li>
<li>Minimal false positives</li>
</ul>
</td>
<td>
<ul>
<li>When you only want to find severely corrupted images</li>
<li>For photos with lots of legitimate white/black areas</li>
<li>Most conservative detection</li>
</ul>
</td>
</tr>
<tr>
<td align="center">Medium</td>
<td>
<ul>
<li>Balanced visual corruption detection</li>
<li>Requires 20%+ of image to be uniform gray/black</li>
<li>Good balance between detection and false positives</li>
</ul>
</td>
<td>
<ul>
<li>Default for most use cases</li>
<li>Regular photo library maintenance</li>
<li>When you want to catch most visual corruption</li>
</ul>
</td>
</tr>
<tr>
<td align="center">High</td>
<td>
<ul>
<li>Most sensitive detection</li>
<li>Requires only 15%+ of image to be uniform gray/black</li>
<li>Also checks for unusual color distribution</li>
<li>May have some false positives</li>
</ul>
</td>
<td>
<ul>
<li>When finding all corruption is critical</li>
<li>For photos that must be perfect</li>
<li>When reviewing results is not a problem</li>
</ul>
</td>
</tr>
</table>

### 3. Smart Detection Features

The visual corruption detection algorithm includes several smart features:

- **Color Context Awareness**: Distinguishes between corruption and legitimate white/black areas based on color context
- **Sampling Technique**: Uses intelligent sampling to efficiently analyze even large images
- **Grayscale Detection**: Specifically targets mid-tone grays that are common in corruption but rare in natural photos
- **White Area Handling**: Special handling for white areas, which are often legitimate in photos (sky, backgrounds, etc.)

### 4. How Visual Detection Works

1. **Image Sampling**: Takes a representative sample of pixels across the image
2. **Color Analysis**: Identifies uniform color regions and calculates their percentage
3. **Color Context**: Analyzes if the colors are likely corruption (mid-gray, black) or natural (white, gradient)
4. **Threshold Comparison**: Compares against strictness thresholds to determine if corruption is present

### 5. Visual vs Technical Corruption

<table>
<tr>
<th>Scenario</th>
<th>Technical Tests</th>
<th>Visual Analysis</th>
<th>Result</th>
</tr>
<tr>
<td>Correctly structured file with gray blocks</td>
<td align="center">✅ Passes</td>
<td align="center">❌ Fails</td>
<td>Detected by <code>--check-visual</code> only</td>
</tr>
<tr>
<td>Missing EOF but visually perfect</td>
<td align="center">❌ Fails</td>
<td align="center">✅ Passes</td>
<td>Caught by normal checks, bypassed with <code>--ignore-eof</code></td>
</tr>
<tr>
<td>Severely corrupt file</td>
<td align="center">❌ Fails</td>
<td align="center">❌ Fails</td>
<td>Detected by both methods</td>
</tr>
<tr>
<td>Perfect file</td>
<td align="center">✅ Passes</td>
<td align="center">✅ Passes</td>
<td>Passes all checks</td>
</tr>
</table>

### 6. Command-Line Examples

```bash
# Find visibly corrupt files with medium strictness (default)
find_bad_images.py /path/to/photos --check-visual --move-to /path/for/corrupted

# Very strict detection - catches all visual corruption but may have false positives
find_bad_images.py /path/to/photos --check-visual --visual-strictness high

# Conservative detection - only flagging obvious corruption
find_bad_images.py /path/to/photos --check-visual --visual-strictness low

# Find only visually corrupt files but ignore technical EOF issues
find_bad_images.py /path/to/photos --check-visual --ignore-eof
```

### 7. Combining With Other Features

Visual corruption detection works seamlessly with other features:

- Use with `--ignore-eof` to find only visibly corrupt files while ignoring technical issues
- Use with `--repair` to attempt to fix files that have both visual and technical corruption
- Use with `--move-to` to collect all visually corrupt files in a separate directory for review

## 🎚️ New Validation System

The v1.4.0 version introduced a powerful validation system with improved control and detection capabilities:

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

### 2. EOF Marker Handling

The `--ignore-eof` option addresses a common issue with images that are technically corrupt but still usable:

- **What it does**: Ignores missing End-Of-File/Image markers during validation
- **When to use it**: For files that open properly in most viewers but fail strict validation
- **Technical detail**: Many images with truncated data or missing EOI markers can still be displayed correctly by applications that are tolerant of these issues
- **Example scenario**: Images downloaded from the web, processed by certain applications, or transferred with incomplete writes

### 3. Enhanced Format-Specific Validation

The tool includes deep structure validation for common formats:

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
<tr>
<td>Large gray/black areas</td>
<td align="center">❌</td>
<td align="center">❌</td>
<td align="center">❌</td>
</tr>
</table>

✅ = Detected | ❌ = Not detected | ⚠️ = Sometimes detected

> **Note**: To detect large gray/black areas, use the `--check-visual` option.

## 🤝 Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.

---

## 🕊️ In Memory of Jeff Young

<div align="center">
<img src="docs/jeff.jpg" alt="Jeff Young" width="400">
</div>

This project is dedicated to the memory of Jeff Young, who loved Tupac's music and embodied his spirit of bringing people together. Like my brother, Jeff would always reach out to help others, making connections and building community wherever he went. His compassion for people and willingness to always lend a hand to those in need are qualities that inspired this tool's purpose - helping others preserve their precious memories.

May your photos always be as bright and clear as the memories they capture, and may we all strive to connect and help others as Jeff did.

---

<div align="center">
<img src="https://raw.githubusercontent.com/ricyoung/2pac/main/preview.gif" alt="2PAC in action" width="700">

*"You know these corrupt JPEGs will never survive. We're on a mission and our reputation's live."*

Made with ❤️ by Richard Young
</div>