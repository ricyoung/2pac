import os
import time
import concurrent.futures
import hashlib
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

import colorama
import humanize
from tqdm import tqdm
import tqdm.auto as tqdm_auto

from find_bad_images.config import VERSION, SUPPORTED_FORMATS, DEFAULT_PROGRESS_DIR
from find_bad_images.validation import is_valid_image, attempt_repair
from find_bad_images.security import validate_file_security, safe_join_path


def process_file(args):
    """Process a single image file."""
    file_path, repair_mode, repair_dir, thorough_check, sensitivity, ignore_eof, check_visual, visual_strictness, enable_security_checks = args

    if enable_security_checks:
        try:
            is_safe, warnings = validate_file_security(file_path, check_size=True, check_dimensions=True)

            for warning in warnings:
                logging.warning(f"Security warning for {file_path}: {warning}")

            if not is_safe:
                size = os.path.getsize(file_path)
                return file_path, False, size, "security_failed", "Failed security validation", None

        except ValueError as e:
            logging.error(f"Security check failed for {file_path}: {e}")
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            return file_path, False, size, "security_failed", str(e), None
        except Exception as e:
            logging.debug(f"Security validation error for {file_path}: {e}")

    is_valid = is_valid_image(file_path, thorough=thorough_check, sensitivity=sensitivity,
                             ignore_eof=ignore_eof, check_visual=check_visual, visual_strictness=visual_strictness)

    if not is_valid and repair_mode:
        repair_success, repair_msg, width, height = attempt_repair(file_path, repair_dir)

        if repair_success:
            return file_path, True, 0, "repaired", repair_msg, (width, height)
        else:
            size = os.path.getsize(file_path)
            return file_path, False, size, "repair_failed", repair_msg, None
    else:
        size = os.path.getsize(file_path) if not is_valid else 0
        return file_path, is_valid, size, "not_repaired", None, None


def get_session_id(directory, formats, recursive):
    """Generate a unique session ID based on scan parameters."""
    dir_path = str(directory).encode('utf-8')
    formats_str = ",".join(sorted(formats)).encode('utf-8')
    recursive_str = str(recursive).encode('utf-8')

    hash_obj = hashlib.sha256()
    hash_obj.update(dir_path)
    hash_obj.update(formats_str)
    hash_obj.update(recursive_str)

    return hash_obj.hexdigest()[:16]


def _deduplicate(seq):
    """Return a list with duplicates removed while preserving order."""
    seen = set()
    deduped = []
    for item in seq:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def save_progress(session_id, directory, formats, recursive, processed_files,
                 bad_files, repaired_files, progress_dir=DEFAULT_PROGRESS_DIR):
    """Save the current progress to a file."""
    if not os.path.exists(progress_dir):
        os.makedirs(progress_dir, exist_ok=True)

    progress_state = {
        'version': VERSION,
        'timestamp': datetime.now().isoformat(),
        'directory': str(directory),
        'formats': formats,
        'recursive': recursive,
        'processed_files': _deduplicate(processed_files),
        'bad_files': _deduplicate(bad_files),
        'repaired_files': _deduplicate(repaired_files)
    }

    progress_file = os.path.join(progress_dir, f"session_{session_id}.progress.json")
    with open(progress_file, 'w') as f:
        json.dump(progress_state, f, indent=2)

    logging.debug(f"Progress saved to {progress_file}")
    return progress_file


def load_progress(session_id, progress_dir=DEFAULT_PROGRESS_DIR):
    """Load progress from a saved session."""
    progress_file_json = os.path.join(progress_dir, f"session_{session_id}.progress.json")
    progress_file_legacy = os.path.join(progress_dir, f"session_{session_id}.progress")

    if os.path.exists(progress_file_json):
        progress_file = progress_file_json
        use_json = True
    elif os.path.exists(progress_file_legacy):
        progress_file = progress_file_legacy
        use_json = False
        logging.warning("Loading legacy pickle format. This format is deprecated for security reasons.")
    else:
        return None

    try:
        if use_json:
            with open(progress_file, 'r') as f:
                progress_state = json.load(f)
        else:
            import pickle
            with open(progress_file, 'rb') as f:
                progress_state = pickle.load(f)
            logging.warning("SECURITY WARNING: Loaded progress file using unsafe pickle format. "
                          "Please delete old .progress files and use new .progress.json format.")

        for key in ('processed_files', 'bad_files', 'repaired_files'):
            if key in progress_state:
                progress_state[key] = _deduplicate(progress_state[key])

        if progress_state.get('version', '0.0.0') != VERSION:
            logging.warning("Progress file was created with a different version. Some incompatibilities may exist.")

        logging.info(f"Loaded progress from {progress_file}")
        return progress_state
    except Exception as e:
        logging.error(f"Failed to load progress: {str(e)}")
        return None


def list_saved_sessions(progress_dir=DEFAULT_PROGRESS_DIR):
    """List all saved sessions with their details."""
    if not os.path.exists(progress_dir):
        return []

    sessions = []
    for filename in os.listdir(progress_dir):
        if filename.endswith('.progress.json') or filename.endswith('.progress'):
            try:
                filepath = os.path.join(progress_dir, filename)
                use_json = filename.endswith('.progress.json')

                if use_json:
                    with open(filepath, 'r') as f:
                        progress_state = json.load(f)
                else:
                    import pickle
                    with open(filepath, 'rb') as f:
                        progress_state = pickle.load(f)

                if filename.endswith('.progress.json'):
                    session_id = filename.replace('session_', '').replace('.progress.json', '')
                else:
                    session_id = filename.replace('session_', '').replace('.progress', '')

                session_info = {
                    'id': session_id,
                    'timestamp': progress_state.get('timestamp', 'Unknown'),
                    'directory': progress_state.get('directory', 'Unknown'),
                    'formats': progress_state.get('formats', []),
                    'processed_count': len(progress_state.get('processed_files', [])),
                    'bad_count': len(progress_state.get('bad_files', [])),
                    'repaired_count': len(progress_state.get('repaired_files', [])),
                    'filepath': filepath,
                    'format': 'JSON' if use_json else 'Pickle (Legacy)'
                }
                sessions.append(session_info)
            except Exception as e:
                logging.debug(f"Failed to load session from {filename}: {str(e)}")

    sessions.sort(key=lambda x: x['timestamp'], reverse=True)
    return sessions


def get_extensions_for_formats(formats):
    """Get all file extensions for the specified formats."""
    extensions = []
    for fmt in formats:
        if fmt in SUPPORTED_FORMATS:
            extensions.extend(SUPPORTED_FORMATS[fmt])
    return tuple(extensions)


def find_image_files(directory, formats, recursive=True):
    """Find all image files of specified formats in a directory."""
    image_files = []
    extensions = get_extensions_for_formats(formats)

    if not extensions:
        logging.warning("No valid image formats specified!")
        return []

    format_names = ", ".join(formats)
    if recursive:
        logging.info(f"Recursively scanning for {format_names} files...")
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extensions):
                    image_files.append(os.path.join(root, file))
    else:
        logging.info(f"Scanning for {format_names} files in {directory} (non-recursive)...")
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and file.lower().endswith(extensions):
                image_files.append(os.path.join(directory, file))

    logging.info(f"Found {len(image_files)} image files")
    return image_files


def process_images(directory, formats, dry_run=True, repair=False,
                  max_workers=None, recursive=True, move_to=None, repair_dir=None,
                  save_progress_interval=5, resume_session=None, progress_dir=DEFAULT_PROGRESS_DIR,
                  thorough_check=False, sensitivity='medium', ignore_eof=False, check_visual=False,
                  visual_strictness='medium', enable_security_checks=False):
    """Find corrupt image files and optionally repair, delete, or move them."""
    start_time = time.time()

    session_id = get_session_id(directory, formats, recursive)
    processed_files = []
    bad_files = []
    repaired_files = []
    total_size_saved = 0
    last_progress_save = time.time()

    if resume_session:
        try:
            progress = load_progress(resume_session, progress_dir)
            if progress and progress['directory'] == str(directory) and progress['formats'] == formats:
                processed_files = list(dict.fromkeys(progress['processed_files']))
                bad_files = progress['bad_files']
                repaired_files = progress['repaired_files']
                logging.info(f"Resuming session: {len(processed_files)} files already processed")
            else:
                if progress:
                    logging.warning("Session parameters don't match current parameters. Starting fresh scan.")
                else:
                    logging.warning(f"Couldn't find session {resume_session}. Starting fresh scan.")
        except Exception as e:
            logging.error(f"Error loading session: {str(e)}. Starting fresh scan.")

    image_files = find_image_files(directory, formats, recursive)
    if not image_files:
        logging.warning("No image files found!")
        return [], [], 0

    if processed_files:
        remaining_files = [f for f in image_files if f not in processed_files]
        skipped_count = len(image_files) - len(remaining_files)
        image_files = remaining_files
        logging.info(f"Skipping {skipped_count} already processed files")

    if not image_files:
        logging.info("All files have already been processed in the previous session!")
        return bad_files, repaired_files, total_size_saved

    if move_to and not os.path.exists(move_to):
        os.makedirs(move_to)
        logging.info(f"Created directory for corrupt files: {move_to}")

    if repair and repair_dir and not os.path.exists(repair_dir):
        os.makedirs(repair_dir)
        logging.info(f"Created directory for backup files: {repair_dir}")

    input_args = [(file_path, repair, repair_dir, thorough_check, sensitivity, ignore_eof, check_visual, visual_strictness, enable_security_checks) for file_path in image_files]

    logging.info("Processing files in parallel...")

    class ProgressSavingBar(tqdm_auto.tqdm):
        def update(self, n=1):
            nonlocal last_progress_save, processed_files
            result = super().update(n)

            current_time = time.time()
            if save_progress_interval > 0 and current_time - last_progress_save >= save_progress_interval * 60:
                save_progress(
                    session_id,
                    directory,
                    formats,
                    recursive,
                    processed_files,
                    bad_files,
                    repaired_files,
                    progress_dir,
                )

                last_progress_save = current_time
                logging.debug(f"Progress saved at {self.n} / {len(image_files)} files")

            return result

    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = []
            futures = {executor.submit(process_file, arg): arg[0] for arg in input_args}

            with ProgressSavingBar(
                total=len(image_files),
                desc=f"{colorama.Fore.BLUE}Checking image files{colorama.Style.RESET_ALL}",
                unit="file",
                bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="blue"
            ) as pbar:
                for future in concurrent.futures.as_completed(futures):
                    file_path = futures[future]
                    try:
                        result = future.result()
                        results.append(result)

                        processed_files.append(file_path)

                        pbar.update(1)

                        file_path, is_valid, size, repair_status, repair_msg, dimensions = result
                        if repair_status == "repaired":
                            repaired_files.append(file_path)
                        elif not is_valid:
                            bad_files.append(file_path)

                    except Exception as e:
                        logging.error(f"Error processing {file_path}: {str(e)}")
                        pbar.update(1)
    except KeyboardInterrupt:
        logging.warning("Process interrupted by user. Saving progress...")
        save_progress(session_id, directory, formats, recursive,
                     processed_files, bad_files, repaired_files, progress_dir)
        logging.info(f"Progress saved. You can resume with --resume {session_id}")
        raise

    total_size_saved = 0
    for file_path, is_valid, size, repair_status, repair_msg, dimensions in results:
        if repair_status == "repaired":
            width, height = dimensions
            msg = f"Repaired: {file_path} ({width}x{height}) - {repair_msg}"
            logging.info(msg)
        elif not is_valid:
            total_size_saved += size

            size_str = humanize.naturalsize(size)
            if repair_status == "repair_failed":
                fail_msg = f"Repair failed: {file_path} ({size_str}) - {repair_msg}"
                logging.warning(fail_msg)

            if dry_run:
                msg = f"Would delete: {file_path} ({size_str})"
                logging.info(msg)
            elif move_to:
                try:
                    rel_path = os.path.relpath(file_path, str(directory))
                    if rel_path.startswith('..'):
                        rel_path = os.path.basename(file_path)

                    try:
                        dest_path = safe_join_path(move_to, rel_path)
                    except ValueError as ve:
                        logging.error(f"Security error moving {file_path}: {ve}")
                        continue

                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    shutil.move(file_path, dest_path)

                    arrow = f"{colorama.Fore.CYAN}\u2192{colorama.Style.RESET_ALL}"
                    msg = f"Moved: {file_path} {arrow} {dest_path} ({size_str})"
                    logging.info(msg)
                except Exception as e:
                    logging.error(f"Failed to move {file_path}: {e}")
            else:
                try:
                    os.remove(file_path)
                    msg = f"Deleted: {file_path} ({size_str})"
                    logging.info(msg)
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")

    save_progress(session_id, directory, formats, recursive,
                 processed_files, bad_files, repaired_files, progress_dir)

    elapsed = time.time() - start_time
    logging.info(f"Processed {len(processed_files)} files in {elapsed:.2f} seconds")
    logging.info(f"Session ID: {session_id} (use --resume {session_id} to resume if needed)")

    return bad_files, repaired_files, total_size_saved
