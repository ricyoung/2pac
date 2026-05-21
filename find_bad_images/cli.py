import sys
import os
import random
import argparse
import logging
from datetime import datetime
from pathlib import Path

import colorama
import humanize
from PIL import Image

from utils import setup_logging
from find_bad_images.config import VERSION, SUPPORTED_FORMATS, DEFAULT_FORMATS, REPAIRABLE_FORMATS, DEFAULT_PROGRESS_DIR, MAX_FILE_SIZE, MAX_IMAGE_PIXELS, QUOTES
from find_bad_images.validation import check_jpeg_structure, check_png_structure, try_full_decode_check, try_external_tools, check_visual_corruption, is_valid_image
from find_bad_images.processing import process_images, load_progress, list_saved_sessions

colorama.init()


def print_banner():
    """Print 2PAC-themed ASCII art banner"""
    banner = r"""
    ░▒▓███████▓▒░░▒▓███████▓▒░ ░▒▓██████▓▒░ ░▒▓██████▓▒░
           ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
           ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░
     ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░
     ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░
     ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
     ░▒▓████████▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░
     ╔═════════════════════════════════════════════════════════╗
     ║ The Picture Analyzer & Corruption killer                ║
     ║ In memory of Jeff Young - Bringing people together      ║
     ╚═════════════════════════════════════════════════════════╝
     """

    if 'colorama' in sys.modules:
        banner_lines = banner.strip().split('\n')
        colored_banner = []

        for i, line in enumerate(banner_lines):
            if i < 7:
                part1 = line[:11]
                part2 = line[11:24]
                part3 = line[24:38]
                part4 = line[38:]

                colored_line = f"{colorama.Fore.WHITE}{part1}" + \
                               f"{colorama.Fore.RED}{part2}" + \
                               f"{colorama.Fore.GREEN}{part3}" + \
                               f"{colorama.Fore.BLUE}{part4}{colorama.Style.RESET_ALL}"

                colored_banner.append(colored_line)
            elif i >= 7 and i <= 10:
                if i == 8:
                    parts = line.split("Picture Analyzer & Corruption")
                    if len(parts) == 2:
                        prefix = parts[0]
                        suffix = parts[1]
                        colored_title = f"{colorama.Fore.YELLOW}{prefix}" + \
                                       f"{colorama.Fore.RED}Picture " + \
                                       f"{colorama.Fore.GREEN}Analyzer " + \
                                       f"{colorama.Fore.WHITE}& " + \
                                       f"{colorama.Fore.BLUE}Corruption" + \
                                       f"{colorama.Fore.YELLOW}{suffix}{colorama.Style.RESET_ALL}"
                        colored_banner.append(colored_title)
                    else:
                        colored_banner.append(f"{colorama.Fore.YELLOW}{line}{colorama.Style.RESET_ALL}")
                elif i == 9:
                    colored_banner.append(f"{colorama.Fore.CYAN}{line}{colorama.Style.RESET_ALL}")
                else:
                    colored_banner.append(f"{colorama.Fore.YELLOW}{line}{colorama.Style.RESET_ALL}")
            else:
                colored_banner.append(f"{colorama.Fore.WHITE}{line}{colorama.Style.RESET_ALL}")

        print('\n'.join(colored_banner))
    else:
        print(banner)
    print()


def main():
    print_banner()

    if len(sys.argv) == 2 and sys.argv[1].lower() == 'q':
        print(f"{colorama.Fore.YELLOW}Exiting 2PAC. Stay safe!{colorama.Style.RESET_ALL}")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description='2PAC: The Picture Analyzer & Corruption killer',
        epilog='Created by Richard Young - "All Eyez On Your Images" - https://github.com/ricyoung/2pac'
    )

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('directory', nargs='?', help='Directory to search for image files')
    action_group.add_argument('--list-sessions', action='store_true', help='List all saved sessions')
    action_group.add_argument('--check-file', type=str, help='Check a specific file for corruption (useful for testing)')

    parser.add_argument('--delete', action='store_true', help='Delete corrupt image files (without this flag, runs in dry-run mode)')
    parser.add_argument('--move-to', type=str, help='Move corrupt files to this directory instead of deleting them')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes (default: CPU count)')
    parser.add_argument('--non-recursive', action='store_true', help='Only search in the specified directory, not subdirectories')
    parser.add_argument('--output', type=str, help='Save list of corrupt files to this file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--version', action='version', version=f'Bad Image Finder v{VERSION} by Richard Young')

    repair_group = parser.add_argument_group('Repair options')
    repair_group.add_argument('--repair', action='store_true', help='Attempt to repair corrupt image files')
    repair_group.add_argument('--backup-dir', type=str, help='Directory to store backups of files before repair')
    repair_group.add_argument('--repair-report', type=str, help='Save list of repaired files to this file')

    format_group = parser.add_argument_group('Image format options')
    format_group.add_argument('--formats', type=str, nargs='+', choices=SUPPORTED_FORMATS.keys(),
                             help=f'Image formats to check (default: all formats)')
    format_group.add_argument('--jpeg', action='store_true', help='Check JPEG files only')
    format_group.add_argument('--png', action='store_true', help='Check PNG files only')
    format_group.add_argument('--tiff', action='store_true', help='Check TIFF files only')
    format_group.add_argument('--gif', action='store_true', help='Check GIF files only')
    format_group.add_argument('--bmp', action='store_true', help='Check BMP files only')

    validation_group = parser.add_argument_group('Validation options')
    validation_group.add_argument('--thorough', action='store_true',
                                 help='Perform thorough image validation (slower but catches more subtle corruption)')
    validation_group.add_argument('--sensitivity', type=str, choices=['low', 'medium', 'high'], default='medium',
                                help='Set validation sensitivity level: low (basic checks), medium (standard checks), high (most strict)')
    validation_group.add_argument('--ignore-eof', action='store_true',
                                help='Ignore missing end-of-file markers (useful for truncated but viewable files)')
    validation_group.add_argument('--check-visual', action='store_true',
                                help='Analyze image content to detect visible corruption like gray/black areas')
    validation_group.add_argument('--visual-strictness', type=str, choices=['low', 'medium', 'high'], default='medium',
                                help='Set strictness level for visual corruption detection: low (most permissive), medium (balanced), high (only clear corruption)')

    security_group = parser.add_argument_group('Security options')
    security_group.add_argument('--security-checks', action='store_true',
                               help='Enable enhanced security validation (file size limits, dimension checks, format verification)')
    security_group.add_argument('--max-file-size', type=int, default=MAX_FILE_SIZE,
                               help=f'Maximum file size in bytes to process (default: {MAX_FILE_SIZE} = 100MB)')
    security_group.add_argument('--max-pixels', type=int, default=MAX_IMAGE_PIXELS,
                               help=f'Maximum image dimensions in pixels (default: {MAX_IMAGE_PIXELS} = 50MP)')

    progress_group = parser.add_argument_group('Progress options')
    progress_group.add_argument('--save-interval', type=int, default=5,
                              help='Save progress every N minutes (0 to disable progress saving)')
    progress_group.add_argument('--progress-dir', type=str, default=DEFAULT_PROGRESS_DIR,
                               help='Directory to store progress files')
    progress_group.add_argument('--resume', type=str, metavar='SESSION_ID',
                              help='Resume from a previously saved session')

    args = parser.parse_args()

    setup_logging(args.verbose, args.no_color)

    if args.check_file:
        file_path = args.check_file
        if not os.path.exists(file_path):
            logging.error(f"Error: File not found: {file_path}")
            sys.exit(1)

        print(f"\n{colorama.Style.BRIGHT}Checking file: {file_path}{colorama.Style.RESET_ALL}\n")

        print(f"{colorama.Fore.CYAN}Basic validation:{colorama.Style.RESET_ALL}")
        try:
            with Image.open(file_path) as img:
                print(f"\u2713 File can be opened by PIL")
                print(f"  Format: {img.format}")
                print(f"  Mode: {img.mode}")
                print(f"  Size: {img.size[0]}x{img.size[1]}")

                try:
                    img.verify()
                    print(f"\u2713 Header verification passed")
                except Exception as e:
                    print(f"\u274c Header verification failed: {str(e)}")

                try:
                    with Image.open(file_path) as img2:
                        img2.load()
                    print(f"\u2713 Data loading test passed")
                except Exception as e:
                    print(f"\u274c Data loading test failed: {str(e)}")
        except Exception as e:
            print(f"\u274c Cannot open file with PIL: {str(e)}")

        if file_path.lower().endswith(tuple(SUPPORTED_FORMATS['JPEG'])):
            print(f"\n{colorama.Fore.CYAN}JPEG structure checks:{colorama.Style.RESET_ALL}")
            is_valid, msg = check_jpeg_structure(file_path)
            if is_valid:
                print(f"\u2713 JPEG structure valid: {msg}")
            else:
                print(f"\u274c JPEG structure invalid: {msg}")
        elif file_path.lower().endswith(tuple(SUPPORTED_FORMATS['PNG'])):
            print(f"\n{colorama.Fore.CYAN}PNG structure checks:{colorama.Style.RESET_ALL}")
            is_valid, msg = check_png_structure(file_path)
            if is_valid:
                print(f"\u2713 PNG structure valid: {msg}")
            else:
                print(f"\u274c PNG structure invalid: {msg}")

        print(f"\n{colorama.Fore.CYAN}Full decode test:{colorama.Style.RESET_ALL}")
        is_valid, msg = try_full_decode_check(file_path)
        if is_valid:
            print(f"\u2713 Full decode test passed: {msg}")
        else:
            print(f"\u274c Full decode test failed: {msg}")

        print(f"\n{colorama.Fore.CYAN}External tools check:{colorama.Style.RESET_ALL}")
        is_valid, msg = try_external_tools(file_path)
        if is_valid:
            print(f"\u2713 External tools: {msg}")
        else:
            print(f"\u274c External tools: {msg}")

        print(f"\n{colorama.Fore.CYAN}Visual content analysis:{colorama.Style.RESET_ALL}")
        is_visually_corrupt, vis_msg = check_visual_corruption(file_path)
        if not is_visually_corrupt:
            print(f"\u2713 No visual corruption detected: {vis_msg}")
        else:
            print(f"\u274c {vis_msg}")

        print(f"\n{colorama.Fore.CYAN}Final verdict:{colorama.Style.RESET_ALL}")
        is_valid_basic = is_valid_image(file_path, thorough=False)
        is_valid_thorough = is_valid_image(file_path, thorough=True)
        is_valid_visual = not is_visually_corrupt

        if is_valid_basic and is_valid_thorough and is_valid_visual:
            print(f"{colorama.Fore.GREEN}This file appears to be valid by all checks.{colorama.Style.RESET_ALL}")
        elif not is_valid_visual:
            print(f"{colorama.Fore.RED}This file shows visible corruption in the image content.{colorama.Style.RESET_ALL}")
            print(f"Recommendation: Use --check-visual to detect this type of corruption.")
        elif is_valid_basic and not is_valid_thorough:
            print(f"{colorama.Fore.YELLOW}This file passes basic validation but fails thorough checks.{colorama.Style.RESET_ALL}")
            print(f"Recommendation: Use --thorough mode to detect this type of corruption.")
        else:
            print(f"{colorama.Fore.RED}This file is corrupt and would be detected by the basic scan.{colorama.Style.RESET_ALL}")

        sys.exit(0)

    if args.list_sessions:
        sessions = list_saved_sessions(args.progress_dir)
        if sessions:
            print(f"\n{colorama.Style.BRIGHT}Saved Sessions:{colorama.Style.RESET_ALL}")
            for i, session in enumerate(sessions):
                ts = datetime.fromisoformat(session['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n{colorama.Fore.CYAN}Session ID: {session['id']}{colorama.Style.RESET_ALL}")
                print(f"  Created: {ts}")
                print(f"  Directory: {session['directory']}")
                print(f"  Formats: {', '.join(session['formats'])}")
                print(f"  Progress: {session['processed_count']} files processed, "
                      f"{session['bad_count']} corrupt, {session['repaired_count']} repaired")

                resume_cmd = f"find_bad_images.py --resume {session['id']}"
                if os.path.exists(session['directory']):
                    print(f"  {colorama.Fore.GREEN}Resume command: {resume_cmd}{colorama.Style.RESET_ALL}")
                else:
                    print(f"  {colorama.Fore.YELLOW}Directory no longer exists, cannot resume{colorama.Style.RESET_ALL}")
        else:
            print("No saved sessions found.")
        sys.exit(0)

    if not args.directory and not args.resume:
        logging.error("Error: You must specify a directory to scan or use --resume to continue a session")
        sys.exit(1)

    directory = None
    if args.resume and not args.directory:
        progress = load_progress(args.resume, args.progress_dir)
        if progress:
            directory = Path(progress['directory'])
            logging.info(f"Using directory from saved session: {directory}")
        else:
            logging.error(f"Could not load session {args.resume}")
            sys.exit(1)
    elif args.directory:
        directory = Path(args.directory)

    if not directory.exists() or not directory.is_dir():
        logging.error(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    if args.delete and args.move_to:
        logging.error("Error: Cannot use both --delete and --move-to options")
        sys.exit(1)

    formats = []
    if args.formats:
        formats = args.formats
    elif args.jpeg:
        formats.append('JPEG')
    elif args.png:
        formats.append('PNG')
    elif args.tiff:
        formats.append('TIFF')
    elif args.gif:
        formats.append('GIF')
    elif args.bmp:
        formats.append('BMP')
    else:
        formats = DEFAULT_FORMATS

    dry_run = not (args.delete or args.move_to)

    if args.repair:
        mode_str = f"{colorama.Fore.MAGENTA}REPAIR MODE{colorama.Style.RESET_ALL}: Attempting to fix corrupt files"
        logging.info(mode_str)

        repairable_formats = [fmt for fmt in formats if fmt in REPAIRABLE_FORMATS]
        if repairable_formats:
            logging.info(f"Repairable formats: {', '.join(repairable_formats)}")
        else:
            logging.warning("None of the selected formats support repair")

    if dry_run:
        mode_str = f"{colorama.Fore.YELLOW}DRY RUN MODE{colorama.Style.RESET_ALL}: No files will be deleted or moved"
        logging.info(mode_str)
    elif args.move_to:
        mode_str = f"{colorama.Fore.BLUE}MOVE MODE{colorama.Style.RESET_ALL}: Corrupt files will be moved to {args.move_to}"
        logging.info(mode_str)
    else:
        mode_str = f"{colorama.Fore.RED}DELETE MODE{colorama.Style.RESET_ALL}: Corrupt files will be permanently deleted"
        logging.info(mode_str)

    if args.save_interval > 0:
        save_interval_str = f"{colorama.Fore.CYAN}PROGRESS SAVING{colorama.Style.RESET_ALL}: Every {args.save_interval} minutes"
        logging.info(save_interval_str)
    else:
        logging.info("Progress saving is disabled")

    if args.resume:
        resume_str = f"{colorama.Fore.CYAN}RESUMING{colorama.Style.RESET_ALL}: From session {args.resume}"
        logging.info(resume_str)

    if args.thorough:
        thorough_str = f"{colorama.Fore.MAGENTA}THOROUGH MODE{colorama.Style.RESET_ALL}: Using deep validation checks (slower but more accurate)"
        logging.info(thorough_str)

    sensitivity_colors = {
        'low': colorama.Fore.GREEN,
        'medium': colorama.Fore.YELLOW,
        'high': colorama.Fore.RED
    }
    sensitivity_color = sensitivity_colors.get(args.sensitivity, colorama.Fore.YELLOW)
    sensitivity_str = f"{sensitivity_color}SENSITIVITY: {args.sensitivity.upper()}{colorama.Style.RESET_ALL}"
    logging.info(sensitivity_str)

    if args.ignore_eof:
        eof_str = f"{colorama.Fore.CYAN}IGNORING EOF MARKERS{colorama.Style.RESET_ALL}: Allowing truncated but viewable files"
        logging.info(eof_str)

    if args.check_visual:
        strictness_color = {
            'low': colorama.Fore.GREEN,
            'medium': colorama.Fore.YELLOW,
            'high': colorama.Fore.RED
        }.get(args.visual_strictness, colorama.Fore.YELLOW)

        visual_str = f"{colorama.Fore.MAGENTA}VISUAL CHECK{colorama.Style.RESET_ALL}: " + \
                     f"Analyzing image content (strictness: {strictness_color}{args.visual_strictness.upper()}{colorama.Style.RESET_ALL})"
        logging.info(visual_str)

    if args.security_checks:
        security_str = f"{colorama.Fore.RED}SECURITY CHECKS ENABLED{colorama.Style.RESET_ALL}: " + \
                      f"Validating file sizes (max {humanize.naturalsize(MAX_FILE_SIZE)}), " + \
                      f"dimensions (max {MAX_IMAGE_PIXELS:,} pixels), and format integrity"
        logging.info(security_str)

    format_list = ", ".join(formats)
    logging.info(f"Checking image formats: {format_list}")
    logging.info(f"Searching for corrupt image files in {directory}")

    try:
        bad_files, repaired_files, total_size_saved = process_images(
            directory,
            formats,
            dry_run=dry_run,
            repair=args.repair,
            max_workers=args.workers,
            recursive=not args.non_recursive,
            move_to=args.move_to,
            repair_dir=args.backup_dir,
            save_progress_interval=args.save_interval,
            resume_session=args.resume,
            progress_dir=args.progress_dir,
            thorough_check=args.thorough,
            sensitivity=args.sensitivity,
            ignore_eof=args.ignore_eof,
            check_visual=args.check_visual,
            visual_strictness=args.visual_strictness,
            enable_security_checks=args.security_checks
        )

        count_color = colorama.Fore.RED if bad_files else colorama.Fore.GREEN
        file_count = f"{count_color}{len(bad_files)}{colorama.Style.RESET_ALL}"
        logging.info(f"Found {file_count} corrupt image files")

        if args.repair:
            repair_color = colorama.Fore.GREEN if repaired_files else colorama.Fore.YELLOW
            repair_count = f"{repair_color}{len(repaired_files)}{colorama.Style.RESET_ALL}"
            logging.info(f"Successfully repaired {repair_count} files")

            if args.repair_report and repaired_files:
                with open(args.repair_report, 'w') as f:
                    for file_path in repaired_files:
                        f.write(f"{file_path}\n")
                logging.info(f"Saved list of repaired files to {args.repair_report}")

        savings_str = humanize.naturalsize(total_size_saved)
        savings_color = colorama.Fore.GREEN if total_size_saved > 0 else colorama.Fore.RESET
        savings_msg = f"Total space savings: {savings_color}{savings_str}{colorama.Style.RESET_ALL}"
        logging.info(savings_msg)

        if not args.no_color:
            signature = f"\n{colorama.Fore.CYAN}2PAC v{VERSION} by Richard Young{colorama.Style.RESET_ALL}"
            quote = f"{colorama.Fore.YELLOW}\"{random.choice(QUOTES)}\"{colorama.Style.RESET_ALL}"
            print(signature)
            print(quote)

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
