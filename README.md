# 🖼️ Bad JPG Finder

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**A lightning-fast tool to find and clean up corrupt JPEG images from your photo collection.**

</div>

## ✨ Features

- **High Performance**: Parallel processing to handle thousands of images efficiently
- **Thorough Validation**: Checks both image headers and data to identify corruption
- **Multiple Operation Modes**:
  - 🔍 **Dry Run** - Preview corrupt files with no changes (default)
  - 🗑️ **Delete** - Permanently remove corrupt files
  - 📦 **Move** - Relocate corrupt files to a separate directory
- **Detailed Reporting**:
  - Space savings calculation
  - Processing speed metrics
  - Organized logging
- **Flexible Configuration**:
  - Control recursion depth
  - Adjust worker count
  - Save reports for later review

## 📋 Requirements

- Python 3.6+
- Required packages:
  - [Pillow](https://pillow.readthedocs.io/) - Python Imaging Library
  - [tqdm](https://github.com/tqdm/tqdm) - Progress bar
  - [humanize](https://github.com/jmoiron/humanize) - Human-readable metrics

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bad-jpg-finder.git
cd bad-jpg-finder

# Install dependencies
pip install -r requirements.txt

# Make executable (Unix/macOS)
chmod +x find_bad_jpgs.py
```

## 🧰 Usage

### Basic (Safe) Mode

```bash
./find_bad_jpgs.py /path/to/images
```

This performs a dry run, showing which files would be deleted without making changes.

### Delete Mode

```bash
./find_bad_jpgs.py /path/to/images --delete
```

⚠️ **Warning**: This permanently deletes corrupt JPG files!

### Move Mode

```bash
./find_bad_jpgs.py /path/to/images --move-to /path/to/corrupt_folder
```

Safely relocates corrupt files to a separate directory for review.

### All Options

```
usage: find_bad_jpgs.py [-h] [--delete] [--move-to MOVE_TO] [--workers WORKERS]
                         [--non-recursive] [--output OUTPUT] [--verbose]
                         directory

positional arguments:
  directory         Directory to search for JPG files

optional arguments:
  -h, --help        Show this help message and exit
  --delete          Delete corrupt JPG files (without this flag, runs in dry-run mode)
  --move-to MOVE_TO Move corrupt files to this directory instead of deleting them
  --workers WORKERS Number of worker processes (default: CPU count)
  --non-recursive   Only search in the specified directory, not subdirectories
  --output OUTPUT   Save list of corrupt files to this file
  --verbose, -v     Enable verbose logging
```

## 🔍 How It Works

Bad JPG Finder uses a two-step validation process to catch different types of image corruption:

1. **Header Verification**: Checks if the file has a valid JPEG header structure
2. **Data Validation**: Attempts to load the image data to detect deeper corruption issues

This approach is more thorough than simple header checks, catching partially downloaded files, truncated images, and data corruption.

## 📊 Performance

- **Processing Speed**: ~1000 images per minute on a modern quad-core CPU
- **Memory Usage**: Minimal (~50MB base + ~2MB per worker)
- **CPU Usage**: Scales efficiently with available cores

## 📋 Examples

### Check a large photo library and save report

```bash
./find_bad_jpgs.py /Volumes/Photos --output corrupt_photos.txt --verbose
```

### Process a NAS archive with limited CPU impact

```bash
./find_bad_jpgs.py /mnt/nas/archive --workers 2
```

### Quick check of recent imports

```bash
./find_bad_jpgs.py ~/Pictures/imports --non-recursive
```

### Clean up and reclaim space immediately

```bash
./find_bad_jpgs.py /Volumes/ExternalDrive --delete --verbose
```

## 🤝 Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.

---

<div align="center">
Made with ❤️ by your friendly neighborhood coder
</div>