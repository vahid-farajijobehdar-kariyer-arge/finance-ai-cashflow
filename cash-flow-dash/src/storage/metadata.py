"""Metadata Manager for uploaded files.

Stores file metadata in a JSON file for persistence across sessions.
Tracks upload history, file properties, and processing status.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class FileMetadata:
    """Metadata for an uploaded file."""
    file_id: str
    original_name: str
    stored_path: str
    upload_date: str
    file_size: int
    file_hash: str
    sheet_names: list[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    processing_status: str = "pending"  # pending, processed, error
    bank_name: Optional[str] = None
    date_range: Optional[dict] = None  # {"start": "2025-01-01", "end": "2025-12-31"}
    total_amount: float = 0.0
    total_commission: float = 0.0
    notes: str = ""
    future_value: Optional[dict] = None  # Investment projection data
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "FileMetadata":
        return cls(**data)


class MetadataManager:
    """Manages file metadata storage and retrieval."""
    
    def __init__(self, storage_path: Path | str = None):
        if storage_path is None:
            storage_path = Path(__file__).parent.parent.parent / "data" / "metadata"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_path / "files_metadata.json"
        self._metadata: dict[str, FileMetadata] = {}
        self._load()
    
    def _load(self) -> None:
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._metadata = {
                        k: FileMetadata.from_dict(v) for k, v in data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self._metadata = {}
    
    def _save(self) -> None:
        """Save metadata to disk."""
        data = {k: v.to_dict() for k, v in self._metadata.items()}
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def generate_file_id(file_content: bytes) -> str:
        """Generate unique ID based on file content hash."""
        return hashlib.md5(file_content).hexdigest()[:12]
    
    @staticmethod
    def calculate_hash(file_content: bytes) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    def add_file(self, metadata: FileMetadata) -> None:
        """Add or update file metadata."""
        self._metadata[metadata.file_id] = metadata
        self._save()
    
    def get_file(self, file_id: str) -> Optional[FileMetadata]:
        """Get metadata for a specific file."""
        return self._metadata.get(file_id)
    
    def get_all_files(self) -> list[FileMetadata]:
        """Get all file metadata, sorted by upload date (newest first)."""
        files = list(self._metadata.values())
        files.sort(key=lambda x: x.upload_date, reverse=True)
        return files
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file metadata."""
        if file_id in self._metadata:
            del self._metadata[file_id]
            self._save()
            return True
        return False
    
    def update_file(self, file_id: str, **kwargs) -> bool:
        """Update specific fields of file metadata."""
        if file_id not in self._metadata:
            return False
        
        metadata = self._metadata[file_id]
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        self._save()
        return True
    
    def file_exists(self, file_hash: str) -> Optional[str]:
        """Check if a file with this hash already exists. Returns file_id if found."""
        for file_id, metadata in self._metadata.items():
            if metadata.file_hash == file_hash:
                return file_id
        return None
    
    def get_summary(self) -> dict:
        """Get summary statistics of all files."""
        files = self.get_all_files()
        return {
            "total_files": len(files),
            "total_size_mb": sum(f.file_size for f in files) / (1024 * 1024),
            "total_amount": sum(f.total_amount for f in files),
            "total_commission": sum(f.total_commission for f in files),
            "banks": list(set(f.bank_name for f in files if f.bank_name)),
            "processed_count": sum(1 for f in files if f.processing_status == "processed"),
            "pending_count": sum(1 for f in files if f.processing_status == "pending"),
        }
