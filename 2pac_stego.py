#!/usr/bin/env python3
"""
2PAC Stego - Unified steganography CLI.

Hides and extracts data using LSB or DCT steganography,
and detects hidden data using RAT Finder analysis.
"""

import argparse
import sys
import os

from steg_embedder import StegEmbedder
from dct_steg import DctStegEmbedder


def cmd_hide(args):
    output = args.output or os.path.splitext(args.image)[0] + '_stego.png'

    if args.dct:
        embedder = DctStegEmbedder(quality=args.quality)
        success, msg, stats = embedder.embed_data(
            args.image, args.data, output, password=args.password
        )
    else:
        embedder = StegEmbedder()
        success, msg, stats = embedder.embed_data(
            args.image, args.data, output,
            password=args.password,
            bits_per_channel=args.bits
        )

    print(msg)
    if success:
        print(f"Output: {output}")
        print(f"Stats: {stats}")
    return 0 if success else 1


def cmd_extract(args):
    if args.dct:
        embedder = DctStegEmbedder()
        success, msg, data = embedder.extract_data(
            args.image, password=args.password
        )
    else:
        embedder = StegEmbedder()
        success, msg, data = embedder.extract_data(
            args.image, password=args.password,
            bits_per_channel=args.bits
        )

    print(msg)
    if success:
        print(data)
    return 0 if success else 1


def cmd_detect(args):
    import rat_finder

    target = args.path
    if os.path.isfile(target):
        sensitivity = args.sensitivity
        sens_map = {'low': 'low', 'medium': 'medium', 'high': 'high'}
        confidence, details = rat_finder.analyze_image(
            target, sensitivity=sens_map.get(sensitivity, 'medium')
        )

        if confidence >= 70:
            label = "HIGH SUSPICION"
        elif confidence >= 40:
            label = "MODERATE SUSPICION"
        else:
            label = "LOW SUSPICION"

        print(f"Confidence: {confidence:.1f}% - {label}")
        for d in details:
            print(f"  - {d}")

    elif os.path.isdir(target):
        import logging
        from utils import setup_logging
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
                print(f"  {s['path']} - {s['confidence']:.1f}%")
            return 1
        else:
            print("No suspicious images found.")
            return 0
    else:
        print(f"Error: '{target}' is not a valid file or directory")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="2PAC Stego - Steganography toolkit",
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # hide
    p_hide = sub.add_parser('hide', help='Hide data in an image')
    p_hide.add_argument('--image', required=True, help='Input image path')
    p_hide.add_argument('--data', required=True, help='Text to hide')
    p_hide.add_argument('--output', help='Output image path (default: <input>_stego.png)')
    p_hide.add_argument('--password', help='Encryption password')
    p_hide.add_argument('--dct', action='store_true', help='Use DCT steganography (default: LSB)')
    p_hide.add_argument('--bits', type=int, default=1, help='LSB bits per channel 1-4 (LSB only)')
    p_hide.add_argument('--quality', type=int, default=95, help='JPEG quality (DCT only)')

    # extract
    p_ext = sub.add_parser('extract', help='Extract hidden data from an image')
    p_ext.add_argument('--image', required=True, help='Image path')
    p_ext.add_argument('--password', help='Decryption password')
    p_ext.add_argument('--dct', action='store_true', help='Use DCT extraction (default: LSB)')
    p_ext.add_argument('--bits', type=int, default=1, help='LSB bits per channel (LSB only)')

    # detect
    p_det = sub.add_parser('detect', help='Detect steganography in images')
    p_det.add_argument('path', help='File or directory to scan')
    p_det.add_argument('--sensitivity', default='medium', choices=['low', 'medium', 'high'])
    p_det.add_argument('--non-recursive', action='store_true')
    p_det.add_argument('--workers', type=int, default=os.cpu_count())
    p_det.add_argument('--visual-reports', action='store_true')
    p_det.add_argument('--reports-dir', help='Directory for visual reports')
    p_det.add_argument('--verbose', '-v', action='store_true')
    p_det.add_argument('--no-color', action='store_true')

    args = parser.parse_args()

    if args.command == 'hide':
        return cmd_hide(args)
    elif args.command == 'extract':
        return cmd_extract(args)
    elif args.command == 'detect':
        return cmd_detect(args)


if __name__ == '__main__':
    sys.exit(main())
