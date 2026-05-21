import os

from PIL import ImageFile

try:
    from quotes import QUOTES
except ImportError:
    QUOTES = ["All Eyez On Your Images."]

ImageFile.LOAD_TRUNCATED_IMAGES = True

SUPPORTED_FORMATS = {
    'JPEG': ('.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi'),
    'PNG': ('.png',),
    'GIF': ('.gif',),
    'TIFF': ('.tiff', '.tif'),
    'BMP': ('.bmp', '.dib'),
    'WEBP': ('.webp',),
    'ICO': ('.ico',),
    'HEIC': ('.heic',),
}

DEFAULT_FORMATS = list(SUPPORTED_FORMATS.keys())

REPAIRABLE_FORMATS = ['JPEG', 'PNG', 'GIF']

DEFAULT_PROGRESS_DIR = os.path.expanduser("~/.bad_image_finder/progress")

VERSION = "1.5.1"

MAX_FILE_SIZE = 100 * 1024 * 1024

MAX_IMAGE_PIXELS = 50000 * 50000
