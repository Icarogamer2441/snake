"""
Snake: A statically typed superset of Python
"""

__version__ = "0.2.0"

from .parser import parse_snake
from .transformer import transform_to_python
from .cli import run_snake_file
from .snakelib import build_library, install_library