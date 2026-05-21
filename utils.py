"""
Shared utilities for the 2PAC toolkit.
"""

import logging
import tempfile
import os
from contextlib import contextmanager

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init()
    _HAS_COLORAMA = True
except ImportError:
    _HAS_COLORAMA = False
    Fore = None
    Style = None


def setup_logging(verbose, no_color=False):
    level = logging.DEBUG if verbose else logging.INFO

    if not no_color and _HAS_COLORAMA:
        COLORS = {
            'DEBUG': Fore.CYAN,
            'INFO': Fore.GREEN,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED,
            'CRITICAL': Fore.MAGENTA + Style.BRIGHT,
            'RESET': Style.RESET_ALL,
        }

        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in COLORS:
                    record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
                    record.msg = f"{COLORS[levelname]}{record.msg}{COLORS['RESET']}"
                return super().format(record)

        formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=[handler],
    )


def slider_to_sensitivity(slider_value, default='medium'):
    """
    Map a 1-10 slider value to a sensitivity string.

    Args:
        slider_value: Integer 1-10
        default: Default sensitivity if mapping fails

    Returns:
        'low', 'medium', or 'high'
    """
    sens_map = {
        1: 'low', 2: 'low', 3: 'low',
        4: 'medium', 5: 'medium', 6: 'medium',
        7: 'high', 8: 'high', 9: 'high', 10: 'high',
    }
    return sens_map.get(slider_value, default)


@contextmanager
def temp_image_path(suffix='.png'):
    """
    Context manager that creates a temp file, yields its path,
    and ensures cleanup on exit.
    """
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            path = tmp.name
        yield path
    finally:
        if path and os.path.exists(path):
            os.unlink(path)
