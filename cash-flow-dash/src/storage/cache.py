"""File Cache Manager for uploaded Excel files.

Manages file storage, caching, and retrieval of uploaded files.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd


class FileCache:
    """Manages cached uploaded files."""
    
    def __init__(self, cache_path: Path | str = None):
        if cache_path is None:
            cache_path = Path(__file__).parent.parent.parent / "data" / "uploads"
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_id: str, file_content: bytes, original_name: str) -> Path:
        """Save uploaded file to cache."""
        # Create subdirectory for this file
        file_dir = self.cache_path / file_id
        file_dir.mkdir(exist_ok=True)
        
        # Preserve original extension
        ext = Path(original_name).suffix
        stored_path = file_dir / f"data{ext}"
        
        with open(stored_path, "wb") as f:
            f.write(file_content)
        
        return stored_path
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get path to cached file."""
        file_dir = self.cache_path / file_id
        if not file_dir.exists():
            return None
        
        # Find the data file
        for ext in [".xlsx", ".xls", ".csv"]:
            path = file_dir / f"data{ext}"
            if path.exists():
                return path
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """Delete cached file and its directory."""
        file_dir = self.cache_path / file_id
        if file_dir.exists():
            shutil.rmtree(file_dir)
            return True
        return False
    
    def load_dataframe(self, file_id: str, sheet_name: str | int = 0) -> Optional[pd.DataFrame]:
        """Load DataFrame from cached file."""
        path = self.get_file_path(file_id)
        if path is None:
            return None
        
        try:
            if path.suffix == ".csv":
                return pd.read_csv(path)
            else:
                return pd.read_excel(path, sheet_name=sheet_name)
        except Exception:
            return None
    
    def get_sheet_names(self, file_id: str) -> list[str]:
        """Get sheet names from Excel file."""
        path = self.get_file_path(file_id)
        if path is None:
            return []
        
        try:
            if path.suffix == ".csv":
                return ["Sheet1"]
            xl = pd.ExcelFile(path)
            return xl.sheet_names
        except Exception:
            return []
    
    def get_cache_size(self) -> int:
        """Get total size of cached files in bytes."""
        total = 0
        for file_path in self.cache_path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total
    
    def clear_cache(self) -> int:
        """Clear all cached files. Returns number of files deleted."""
        count = 0
        for item in self.cache_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                count += 1
        return count
