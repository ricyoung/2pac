#!/usr/bin/env python3
"""
RAT Finder — Image Analysis Tool

Detect hidden steganography in images. Find corrupt, truncated, and damaged files.

Usage:
    python ratfinder.py detect suspicious.png --sensitivity high
    python ratfinder.py scan ./photos --thorough --repair
    python ratfinder.py check broken.jpg --check-visual
"""

import argparse
import os
import sys

from utils import setup_logging


def cmd_detect(args):
    import rat_finder

    target = args.path
    if os.path.isfile(target):
        is_suspicious, confidence, details = rat_finder.analyze_image(
            target, sensitivity=args.sensitivity
        )

        if confidence >= 70:
            label = "HIGH SUSPICION"
        elif confidence >= 40:
            label = "MODERATE SUSPICION"
        else:
            label = "LOW SUSPICION"

        print(f"\nConfidence: {confidence:.1f}% — {label}\n")
        for key, result in details.items():
            if isinstance(result, dict):
                susp = result.get('suspicious', False)
                conf = result.get('confidence', 0)
                status = "SUSPICIOUS" if susp else "clean"
                print(f"  {key}: {conf:.0f}% — {status}")
            else:
                print(f"  {key}: {result}")

    elif os.path.isdir(target):
        setup_logging(args.verbose, args.no_color)

        suspicious = rat_finder.analyze_images(
            target,
            sensitivity=args.sensitivity,
            recursive=not args.non_recursive,
            output_dir=args.reports_dir if args.visual_reports else None,
            max_workers=args.workers
        )

        if suspicious:
            print(f"\nFound {len(suspicious)} suspicious images:")
            for s in suspicious:
                print(f"  {s['path']} — {s['confidence']:.1f}%")
            return 1
        else:
            print("No suspicious images found.")
            return 0
    else:
        print(f"Error: '{target}' is not a valid file or directory")
        return 1


def cmd_scan(args):
    from find_bad_images import main as scan_main

    sys.argv = [
        'ratfinder.py', 'scan',
        args.directory,
    ]
    if args.thorough:
        sys.argv.append('--thorough')
    if args.check_visual:
        sys.argv.append('--check-visual')
    if args.sensitivity:
        sys.argv.extend(['--sensitivity', args.sensitivity])
    if args.repair:
        sys.argv.append('--repair')
    if args.backup_dir:
        sys.argv.extend(['--backup-dir', args.backup_dir])
    if args.move_to:
        sys.argv.extend(['--move-to', args.move_to])
    elif args.delete:
        sys.argv.append('--delete')
    if args.workers:
        sys.argv.extend(['--workers', str(args.workers)])
    if args.formats:
        sys.argv.extend(['--formats'] + args.formats)
    if args.resume:
        sys.argv.extend(['--resume', args.resume])
    if args.output:
        sys.argv.extend(['--output', args.output])
    if args.verbose:
        sys.argv.append('--verbose')
    if args.no_color:
        sys.argv.append('--no-color')

    return scan_main()


def cmd_check(args):
    from find_bad_images import is_valid_image, diagnose_image_issue

    path = args.file
    if not os.path.isfile(path):
        print(f"Error: '{path}' not found")
        return 1

    sens_map = {'low': 'low', 'medium': 'medium', 'high': 'high'}
    sensitivity = sens_map.get(args.sensitivity, 'medium')

    valid = is_valid_image(path, thorough=True,
                           sensitivity=sensitivity,
                           check_visual=args.check_visual)

    if valid:
        print(f"\n  VALID — {path}")
        print("  No structural or visual issues detected.")
        return 0
    else:
        issues = diagnose_image_issue(path)
        print(f"\n  ISSUES — {path}")
        if isinstance(issues, dict):
            for key, value in issues.items():
                print(f"  - {key}: {value}")
        else:
            print(f"  - {issues}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog='ratfinder',
        description='RAT Finder — Detect steganography and corrupt images.',
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Debug logging')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    sub = parser.add_subparsers(dest='command', required=True)

    p_detect = sub.add_parser('detect', help='Detect steganography in images')
    p_detect.add_argument('path', help='File or directory to scan')
    p_detect.add_argument('--sensitivity', default='medium', choices=['low', 'medium', 'high'])
    p_detect.add_argument('--non-recursive', action='store_true')
    p_detect.add_argument('--workers', type=int, default=os.cpu_count())
    p_detect.add_argument('--visual-reports', action='store_true')
    p_detect.add_argument('--reports-dir', help='Directory for visual reports')

    p_scan = sub.add_parser('scan', help='Scan directory for corrupt images')
    p_scan.add_argument('directory', help='Directory to scan')
    p_scan.add_argument('--thorough', action='store_true', help='Deep structure + decode checks')
    p_scan.add_argument('--check-visual', action='store_true', help='Detect visual corruption')
    p_scan.add_argument('--sensitivity', choices=['low', 'medium', 'high'])
    p_scan.add_argument('--repair', action='store_true', help='Attempt repair')
    p_scan.add_argument('--backup-dir', help='Backup originals before repair')
    p_scan.add_argument('--move-to', help='Move bad files to directory')
    p_scan.add_argument('--delete', action='store_true', help='Delete corrupt files')
    p_scan.add_argument('--workers', type=int)
    p_scan.add_argument('--formats', nargs='+', help='Formats to check (JPEG PNG GIF ...)')
    p_scan.add_argument('--resume', help='Resume session ID')
    p_scan.add_argument('--output', help='Save results to file')

    p_check = sub.add_parser('check', help='Check a single image file')
    p_check.add_argument('file', help='Image file to check')
    p_check.add_argument('--check-visual', action='store_true', help='Detect visual corruption')
    p_check.add_argument('--sensitivity', default='medium', choices=['low', 'medium', 'high'])

    args = parser.parse_args()

    if args.command == 'detect':
        return cmd_detect(args)
    elif args.command == 'scan':
        return cmd_scan(args)
    elif args.command == 'check':
        return cmd_check(args)


if __name__ == '__main__':
    sys.exit(main())
