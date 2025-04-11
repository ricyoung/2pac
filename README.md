# Bad JPG Finder

A Python utility to find and manage corrupt JPEG images in large collections.

## Features

- Find corrupt JPG/JPEG files with thorough validation
- Parallel processing for high performance with large image collections
- Progress bar to track completion
- Space savings calculation
- Multiple handling options:
  - Dry run mode (default)
  - Delete mode
  - Move mode to relocate corrupt files
- Option to save a list of corrupt files

## Requirements

- Python 3.6+
- Dependencies (install via `pip install -r requirements.txt`):
  - Pillow (PIL Fork)
  - tqdm
  - humanize

## Installation

```bash
git clone https://github.com/yourusername/bad-jpg-finder.git
cd bad-jpg-finder
pip install -r requirements.txt
```

## Usage

### Basic Usage (Dry Run)

```bash
python find_bad_jpgs.py /path/to/images
```

This will scan the directory, identify corrupt JPG files, but won't delete anything.

### Delete Mode

```bash
python find_bad_jpgs.py /path/to/images --delete
```

⚠️ **Warning**: This will permanently delete corrupt JPG files!

### Move Mode

```bash
python find_bad_jpgs.py /path/to/images --move-to /path/to/corrupted_files
```

Moves corrupt files to the specified directory instead of deleting them.

### Other Options

```bash
python find_bad_jpgs.py --help
```

```
usage: find_bad_jpgs.py [-h] [--delete] [--move-to MOVE_TO] [--workers WORKERS]
                         [--non-recursive] [--output OUTPUT] [--verbose]
                         directory

Find and delete corrupt JPG files

positional arguments:
  directory         Directory to search for JPG files

optional arguments:
  -h, --help        show this help message and exit
  --delete          Delete corrupt JPG files (without this flag, runs in dry-run mode)
  --move-to MOVE_TO Move corrupt files to this directory instead of deleting them
  --workers WORKERS Number of worker processes (default: CPU count)
  --non-recursive   Only search in the specified directory, not subdirectories
  --output OUTPUT   Save list of corrupt files to this file
  --verbose, -v     Enable verbose logging
```

## How It Works

The script uses PIL (Python Imaging Library) to:

1. Scan directories recursively for JPG/JPEG files
2. Validate each image file by:
   - Checking the image header
   - Attempting to load the image data
3. Process files in parallel for speed
4. Report all corrupt files, their size, and total space savings

## Examples

### Check a large photo library and save list of corrupt files

```bash
python find_bad_jpgs.py /Volumes/Photos --output corrupt_photos.txt --verbose
```

### Move corrupt files from archive to a review folder

```bash
python find_bad_jpgs.py /mnt/archive/photos --move-to /home/user/corrupt_photos --workers 8
```

### Scan only the current directory (non-recursive)

```bash
python find_bad_jpgs.py . --non-recursive
```

## License

MIT