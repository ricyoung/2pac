# 🖼️ Bad Image Finder

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
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

### All Options

```
usage: find_bad_images.py [-h] [--delete] [--move-to MOVE_TO] [--workers WORKERS]
                          [--non-recursive] [--output OUTPUT] [--verbose]
                          [--no-color] [--formats {JPEG,PNG,GIF,TIFF,BMP,WEBP,ICO,HEIC} [...]]
                          [--jpeg] [--png] [--tiff] [--gif] [--bmp]
                          directory

positional arguments:
  directory         Directory to search for image files

optional arguments:
  -h, --help        Show this help message and exit
  --delete          Delete corrupt image files (without this flag, runs in dry-run mode)
  --move-to MOVE_TO Move corrupt files to this directory instead of deleting them
  --workers WORKERS Number of worker processes (default: CPU count)
  --non-recursive   Only search in the specified directory, not subdirectories
  --output OUTPUT   Save list of corrupt files to this file
  --verbose, -v     Enable verbose logging
  --no-color        Disable colored output (useful for logs or non-interactive terminals)

Image format options:
  --formats {JPEG,PNG,GIF,TIFF,BMP,WEBP,ICO,HEIC} [...]
                        Image formats to check (default: all formats)
  --jpeg               Check JPEG files only
  --png                Check PNG files only
  --tiff               Check TIFF files only
  --gif                Check GIF files only
  --bmp                Check BMP files only
```

## 🔍 How It Works

Bad Image Finder uses a two-step validation process to catch different types of image corruption:

1. **Header Verification**: Checks if the file has a valid image header structure
2. **Data Validation**: Attempts to load the image data to detect deeper corruption issues

This approach is more thorough than simple header checks, catching partially downloaded files, truncated images, and data corruption.

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