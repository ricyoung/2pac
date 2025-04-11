#!/usr/bin/env python3

import os
import argparse
import concurrent.futures
import sys
import time
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import humanize
import logging

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def is_valid_jpg(file_path):
    try:
        with Image.open(file_path) as img:
            # verify() checks the file header
            img.verify()
            
            # Additional step: try to load the image data
            # This catches more corruption issues
            with Image.open(file_path) as img2:
                img2.load()
        return True
    except Exception as e:
        logging.debug(f"Invalid image {file_path}: {str(e)}")
        return False

def process_file(file_path):
    is_valid = is_valid_jpg(file_path)
    size = os.path.getsize(file_path) if not is_valid else 0
    return file_path, is_valid, size

def find_jpg_files(directory, recursive=True):
    """Find all JPG files in a directory."""
    jpg_files = []
    extensions = ('.jpg', '.jpeg')
    
    if recursive:
        logging.info("Recursively scanning for JPG files...")
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extensions):
                    jpg_files.append(os.path.join(root, file))
    else:
        logging.info(f"Scanning for JPG files in {directory} (non-recursive)...")
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and file.lower().endswith(extensions):
                jpg_files.append(os.path.join(directory, file))
    
    logging.info(f"Found {len(jpg_files)} JPG files")
    return jpg_files

def find_bad_jpgs(directory, dry_run=True, max_workers=None, recursive=True, move_to=None):
    """Find corrupt JPG files and optionally delete or move them."""
    start_time = time.time()
    bad_files = []
    total_size_saved = 0
    
    # Find all jpg files
    jpg_files = find_jpg_files(directory, recursive)
    if not jpg_files:
        logging.warning("No JPG files found!")
        return [], 0
        
    # Create move_to directory if it doesn't exist
    if move_to and not os.path.exists(move_to):
        os.makedirs(move_to)
        logging.info(f"Created directory for corrupt files: {move_to}")
    
    # Process files in parallel
    logging.info("Processing files in parallel...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(
            executor.map(process_file, jpg_files),
            total=len(jpg_files),
            desc="Checking JPG files",
            unit="file"
        ))
    
    # Process results
    for file_path, is_valid, size in results:
        if not is_valid:
            bad_files.append(file_path)
            total_size_saved += size
            
            if dry_run:
                logging.info(f"Would delete: {file_path} ({humanize.naturalsize(size)})")
            elif move_to:
                dest_path = os.path.join(move_to, os.path.basename(file_path))
                try:
                    os.rename(file_path, dest_path)
                    logging.info(f"Moved: {file_path} → {dest_path} ({humanize.naturalsize(size)})")
                except Exception as e:
                    logging.error(f"Failed to move {file_path}: {e}")
            else:
                try:
                    os.remove(file_path)
                    logging.info(f"Deleted: {file_path} ({humanize.naturalsize(size)})")
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")
    
    elapsed = time.time() - start_time
    logging.info(f"Processed {len(jpg_files)} files in {elapsed:.2f} seconds")
    
    return bad_files, total_size_saved

def main():
    parser = argparse.ArgumentParser(description='Find and delete corrupt JPG files')
    parser.add_argument('directory', help='Directory to search for JPG files')
    parser.add_argument('--delete', action='store_true', help='Delete corrupt JPG files (without this flag, runs in dry-run mode)')
    parser.add_argument('--move-to', type=str, help='Move corrupt files to this directory instead of deleting them')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes (default: CPU count)')
    parser.add_argument('--non-recursive', action='store_true', help='Only search in the specified directory, not subdirectories')
    parser.add_argument('--output', type=str, help='Save list of corrupt files to this file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        logging.error(f"Error: {args.directory} is not a valid directory")
        sys.exit(1)
    
    # Check for incompatible options
    if args.delete and args.move_to:
        logging.error("Error: Cannot use both --delete and --move-to options")
        sys.exit(1)
    
    dry_run = not (args.delete or args.move_to)
    
    if dry_run:
        logging.info(f"DRY RUN MODE: No files will be deleted or moved")
    elif args.move_to:
        logging.info(f"MOVE MODE: Corrupt files will be moved to {args.move_to}")
    else:
        logging.info(f"DELETE MODE: Corrupt files will be permanently deleted")
    
    logging.info(f"Searching for corrupt JPG files in {directory}")
    
    try:
        bad_files, total_size_saved = find_bad_jpgs(
            directory, 
            dry_run=dry_run, 
            max_workers=args.workers,
            recursive=not args.non_recursive,
            move_to=args.move_to
        )
        
        logging.info(f"Found {len(bad_files)} corrupt JPG files")
        logging.info(f"Total space savings: {humanize.naturalsize(total_size_saved)}")
        
        # Save list of corrupt files if requested
        if args.output and bad_files:
            with open(args.output, 'w') as f:
                for file_path in bad_files:
                    f.write(f"{file_path}\n")
            logging.info(f"Saved list of corrupt files to {args.output}")
        
        if bad_files and dry_run:
            logging.info("Run with --delete to remove these files or --move-to to relocate them")
            
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()