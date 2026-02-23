"""
Azure Blob Storage - Kariyer.net Finans

Banka dosyalarını Azure Blob Storage'da yedekler ve geri yükler.

© 2026 Kariyer.net Finans Ekibi
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import streamlit as st

logger = logging.getLogger(__name__)

# Data paths
DATA_RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"


def get_azure_connection() -> Optional[str]:
    """Azure connection string'i al (secrets veya environment)."""
    try:
        return st.secrets["azure"]["storage_connection_string"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("AZURE_STORAGE_CONNECTION")


def get_container_name() -> str:
    """Container adını al."""
    try:
        return st.secrets["azure"]["container_name"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("AZURE_CONTAINER_NAME", "pos-data")


def is_azure_configured() -> bool:
    """Azure yapılandırması mevcut mu kontrol et."""
    return get_azure_connection() is not None


def upload_file_to_azure(file_path: Path, blob_name: Optional[str] = None) -> bool:
    """
    Dosyayı Azure Blob Storage'a yükle.
    
    Args:
        file_path: Yüklenecek dosyanın yolu
        blob_name: Blob adı (opsiyonel, varsayılan: dosya adı)
    
    Returns:
        Başarılı ise True
    """
    connection_string = get_azure_connection()
    if not connection_string:
        logger.warning("Azure Storage yapılandırılmamış")
        return False
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        container_name = get_container_name()
        blob_name = blob_name or file_path.name
        
        # Tarih prefix'i ekle (backup versiyonlama)
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        blob_path = f"{date_prefix}/{blob_name}"
        
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)
        
        # Container yoksa oluştur
        try:
            container_client.create_container()
            logger.info(f"Container oluşturuldu: {container_name}")
        except Exception:
            pass  # Container zaten var
        
        blob_client = container_client.get_blob_client(blob_path)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        logger.info(f"Dosya yüklendi: {blob_path}")
        return True
        
    except ImportError:
        logger.error("azure-storage-blob paketi yüklü değil. 'pip install azure-storage-blob' çalıştırın.")
        return False
    except Exception as e:
        logger.error(f"Azure upload hatası: {e}")
        return False


def download_file_from_azure(blob_name: str, file_path: Path) -> bool:
    """
    Dosyayı Azure Blob Storage'dan indir.
    
    Args:
        blob_name: Blob adı
        file_path: Kaydedilecek dosya yolu
    
    Returns:
        Başarılı ise True
    """
    connection_string = get_azure_connection()
    if not connection_string:
        logger.warning("Azure Storage yapılandırılmamış")
        return False
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        container_name = get_container_name()
        
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service.get_blob_client(container_name, blob_name)
        
        # Klasör yoksa oluştur
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as data:
            data.write(blob_client.download_blob().readall())
        
        logger.info(f"Dosya indirildi: {blob_name} -> {file_path}")
        return True
        
    except ImportError:
        logger.error("azure-storage-blob paketi yüklü değil")
        return False
    except Exception as e:
        logger.error(f"Azure download hatası: {e}")
        return False


def list_azure_files(prefix: str = "") -> List[str]:
    """
    Azure'daki dosyaları listele.
    
    Args:
        prefix: Blob prefix (klasör filtresi)
    
    Returns:
        Blob adları listesi
    """
    connection_string = get_azure_connection()
    if not connection_string:
        return []
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        container_name = get_container_name()
        
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
        
    except Exception as e:
        logger.error(f"Azure list hatası: {e}")
        return []


def get_latest_backup(filename: str) -> Optional[str]:
    """
    Belirli bir dosyanın en son backup'ını bul.
    
    Args:
        filename: Dosya adı
    
    Returns:
        En son backup'ın blob path'i
    """
    all_files = list_azure_files()
    matching = [f for f in all_files if f.endswith(filename)]
    
    if not matching:
        return None
    
    # En son tarihe göre sırala
    matching.sort(reverse=True)
    return matching[0]


def backup_all_raw_files() -> dict:
    """
    data/raw/ klasöründeki tüm dosyaları Azure'a yedekle.
    
    Returns:
        Sonuç özeti: {"success": [...], "failed": [...]}
    """
    if not is_azure_configured():
        return {"success": [], "failed": [], "error": "Azure yapılandırılmamış"}
    
    results = {"success": [], "failed": []}
    
    for file_path in DATA_RAW_PATH.glob("*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            if upload_file_to_azure(file_path):
                results["success"].append(file_path.name)
            else:
                results["failed"].append(file_path.name)
    
    return results


def restore_from_azure() -> dict:
    """
    Azure'dan en güncel dosyaları geri yükle.
    
    Returns:
        Sonuç özeti: {"restored": [...], "failed": [...]}
    """
    if not is_azure_configured():
        return {"restored": [], "failed": [], "error": "Azure yapılandırılmamış"}
    
    results = {"restored": [], "failed": []}
    
    # En son tarih klasörünü bul
    all_files = list_azure_files()
    if not all_files:
        return {"restored": [], "failed": [], "error": "Azure'da dosya bulunamadı"}
    
    # Benzersiz dosya adlarını bul ve en güncel versiyonları al
    file_map = {}
    for blob_path in all_files:
        filename = blob_path.split("/")[-1]
        if filename and not filename.startswith("."):
            if filename not in file_map or blob_path > file_map[filename]:
                file_map[filename] = blob_path
    
    # En güncel dosyaları indir
    for filename, blob_path in file_map.items():
        local_path = DATA_RAW_PATH / filename
        if download_file_from_azure(blob_path, local_path):
            results["restored"].append(filename)
        else:
            results["failed"].append(filename)
    
    return results


def delete_old_backups(keep_days: int = 30) -> int:
    """
    Eski backup'ları sil.
    
    Args:
        keep_days: Kaç günlük backup tutulsun
    
    Returns:
        Silinen dosya sayısı
    """
    connection_string = get_azure_connection()
    if not connection_string:
        return 0
    
    try:
        from azure.storage.blob import BlobServiceClient
        from datetime import timedelta
        
        container_name = get_container_name()
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)
        
        deleted_count = 0
        for blob in container_client.list_blobs():
            if blob.last_modified < cutoff_date:
                container_client.delete_blob(blob.name)
                deleted_count += 1
        
        logger.info(f"{deleted_count} eski backup silindi")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Backup silme hatası: {e}")
        return 0
