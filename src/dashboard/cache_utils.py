"""
Cache Management Utilities.

Provides centralized cache clearing for data refresh on file import.
Design: Data resets each time new files are imported.

Streamlit 1.53.0+ Features:
- Session-scoped caching: st.cache_data(scope="session")
- Better cache isolation between users
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)

# Cache scope type for Streamlit 1.53.0+
CacheScope = Literal["app", "session"]


def get_cache_decorator(scope: CacheScope = "session"):
    """Get a cache decorator with specified scope.
    
    Streamlit 1.53.0+ supports session-scoped caching for better isolation.
    
    Args:
        scope: "app" (shared across all users) or "session" (per-user)
    
    Returns:
        Configured cache_data decorator
    
    Example:
        @get_cache_decorator(scope="session")
        def load_user_data():
            return expensive_operation()
    """
    return st.cache_data(scope=scope)


def clear_all_data_caches():
    """Clear ALL cached data across the entire application.
    
    Call this function after uploading/deleting files to ensure
    all pages reload fresh data from disk.
    
    This implements the "data reset on import" design pattern.
    
    Note: Streamlit 1.53.0+ clears both app-scoped and session-scoped caches.
    """
    # Clear Streamlit's built-in cache
    st.cache_data.clear()
    
    # Clear any resource caches
    try:
        st.cache_resource.clear()
    except Exception:
        pass  # May not exist in older Streamlit versions
    
    # Clear session state data caches
    keys_to_clear = [
        'loaded_data',
        'all_bank_data',
        'bank_data_cache',
        'metadata_cache',
        'file_cache',
        'last_data_load',
        'df_cache',
        'combined_df',
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear any bank-specific caches
    bank_prefixes = ['ziraat_', 'akbank_', 'garanti_', 'vakifbank_', 'halkbank_', 'qnb_', 'ykb_', 'isbank_']
    keys_to_remove = []
    for key in st.session_state.keys():
        for prefix in bank_prefixes:
            if key.startswith(prefix):
                keys_to_remove.append(key)
                break
    
    for key in keys_to_remove:
        del st.session_state[key]
    
    logger.info("All data caches cleared successfully")


def get_data_version() -> str:
    """Get current data version hash based on files in raw folder.
    
    Returns a hash that changes when files are added/removed/modified.
    """
    import hashlib
    from datetime import datetime
    
    raw_path = Path(__file__).parent.parent.parent / "data" / "raw"
    
    if not raw_path.exists():
        return "no_data"
    
    # Tüm dosyaları topla (kök + alt klasörler)
    all_files = []
    
    # Kök dizindeki dosyalar
    for f in raw_path.glob("*"):
        if f.is_file() and not f.name.startswith('.'):
            all_files.append(f)
    
    # Alt klasörlerdeki dosyalar (BANKA/YYYY-MM/dosya.xlsx)
    for bank_dir in raw_path.iterdir():
        if bank_dir.is_dir() and not bank_dir.name.startswith("."):
            for month_dir in bank_dir.iterdir():
                if month_dir.is_dir():
                    for f in month_dir.glob("*"):
                        if f.is_file() and not f.name.startswith("."):
                            all_files.append(f)
    
    files = sorted(all_files, key=lambda x: str(x))
    file_info = []
    
    for f in files:
        stat = f.stat()
        file_info.append(f"{f.name}:{stat.st_size}:{stat.st_mtime}")
    
    if not file_info:
        return "empty"
    
    content = "|".join(file_info)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def check_data_changed() -> bool:
    """Check if data has changed since last load.
    
    Returns True if files have been added/removed/modified.
    """
    current_version = get_data_version()
    last_version = st.session_state.get('_data_version', None)
    
    if last_version is None or last_version != current_version:
        st.session_state['_data_version'] = current_version
        return True
    
    return False


def auto_refresh_if_changed():
    """Automatically clear caches if data files have changed.
    
    Call this at the start of any page that loads data.
    """
    if check_data_changed():
        clear_all_data_caches()
        st.session_state['_data_version'] = get_data_version()


def invalidate_data():
    """Force invalidate data version to trigger refresh on next load."""
    st.session_state['_data_version'] = None


class DataRefreshManager:
    """Context manager for data refresh operations.
    
    Usage:
        with DataRefreshManager():
            # Upload files here
            pass
        # Caches automatically cleared after
    """
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        clear_all_data_caches()
        return False
