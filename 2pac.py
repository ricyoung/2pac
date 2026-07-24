#!/usr/bin/env python3
"""
2PAC — Steganography Tool

Hide secret data inside images. Extract hidden data from images.

Usage:
    python 2pac.py hide --image photo.png --data "secret message" --output out.png
    python 2pac.py extract --image out.png --password hunter2
"""

import argparse
import os
import sys

from steg_embedder import StegEmbedder
from dct_steg import DctStegEmbedder


def cmd_hide(args):
    output = args.output or os.path.splitext(args.image)[0] + '_stego.png'

    if args.dct:
        print("WARNING: DCT mode is non-functional — extraction does not reliably roundtrip.")
        print("         Use LSB (default) for reliable embedding. Proceeding anyway...\n")
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
        print("WARNING: DCT mode is non-functional — extraction does not reliably roundtrip.\n")
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


def main():
    parser = argparse.ArgumentParser(
        prog='2pac',
        description='2PAC — Hide data inside images, or extract hidden data.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_hide = sub.add_parser('hide', help='Hide data inside an image')
    p_hide.add_argument('--image', required=True, help='Input image path')
    p_hide.add_argument('--data', required=True, help='Text to hide')
    p_hide.add_argument('--output', help='Output path (default: <input>_stego.png)')
    p_hide.add_argument('--password', help='Encryption password')
    p_hide.add_argument('--dct', action='store_true', help='Use DCT (experimental, lower capacity)')
    p_hide.add_argument('--bits', type=int, default=1, help='LSB bits per channel 1-4 (default: 1)')
    p_hide.add_argument('--quality', type=int, default=95, help='DCT quality (default: 95)')

    p_ext = sub.add_parser('extract', help='Extract hidden data from an image')
    p_ext.add_argument('--image', required=True, help='Image to extract from')
    p_ext.add_argument('--password', help='Decryption password')
    p_ext.add_argument('--dct', action='store_true', help='DCT extraction (default: LSB)')
    p_ext.add_argument('--bits', type=int, default=1, help='LSB bits per channel (default: 1)')

    args = parser.parse_args()

    if args.command == 'hide':
        return cmd_hide(args)
    elif args.command == 'extract':
        return cmd_extract(args)


if __name__ == '__main__':
    sys.exit(main())
