#!/usr/bin/env python3
"""
2PAC Scan - Image corruption scanner CLI.

Detects corrupt, truncated, and visually damaged image files.
Supports repair, session resuming, and security validation.
"""

import sys
from find_bad_images import main as scan_main


if __name__ == '__main__':
    sys.exit(scan_main())
