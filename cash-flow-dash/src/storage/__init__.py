"""Storage module for file metadata and caching."""

from .metadata import MetadataManager
from .cache import FileCache

__all__ = ["MetadataManager", "FileCache"]
