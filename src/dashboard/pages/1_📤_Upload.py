"""
📤 File Upload & Management

Upload Excel files for processing and manage uploaded file history.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.storage.metadata import MetadataManager, FileMetadata
from src.storage.cache import FileCache


def init_managers():
    """Initialize storage managers."""
    if "metadata_manager" not in st.session_state:
        st.session_state.metadata_manager = MetadataManager()
    if "file_cache" not in st.session_state:
        st.session_state.file_cache = FileCache()
    return st.session_state.metadata_manager, st.session_state.file_cache


def analyze_excel_file(file_content: bytes, filename: str) -> dict:
    """Analyze uploaded Excel file and extract metadata."""
    import io
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_content))
            sheet_names = ["Sheet1"]
        else:
            xl = pd.ExcelFile(io.BytesIO(file_content))
            sheet_names = xl.sheet_names
            # Read first sheet for analysis
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=0)
        
        # Try to detect bank name from filename or content
        bank_name = None
        bank_keywords = ["ziraat", "akbank", "garanti", "halkbank", "vakıf", 
                        "ykb", "yapı kredi", "iş bankası", "işbank", "qnb", "finans"]
        
        filename_lower = filename.lower()
        for keyword in bank_keywords:
            if keyword in filename_lower:
                bank_name = keyword.title()
                break
        
        # Try to find amount columns
        total_amount = 0
        amount_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ["tutar", "amount", "brüt", "gross"]
        )]
        if amount_cols:
            total_amount = pd.to_numeric(df[amount_cols[0]], errors="coerce").sum()
        
        # Try to find date range
        date_range = None
        date_cols = [c for c in df.columns if any(
            x in str(c).lower() for x in ["tarih", "date", "işlem"]
        )]
        if date_cols:
            dates = pd.to_datetime(df[date_cols[0]], errors="coerce").dropna()
            if not dates.empty:
                date_range = {
                    "start": dates.min().strftime("%Y-%m-%d"),
                    "end": dates.max().strftime("%Y-%m-%d")
                }
        
        return {
            "sheet_names": sheet_names,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "bank_name": bank_name,
            "total_amount": total_amount,
            "date_range": date_range,
        }
    except Exception as e:
        return {
            "error": str(e),
            "sheet_names": [],
            "row_count": 0,
            "column_count": 0,
        }


def render_upload_section(metadata_manager: MetadataManager, file_cache: FileCache):
    """Render file upload section."""
    st.header("📤 Dosya Yükle / Upload Files")
    
    st.markdown("""
    Excel veya CSV dosyalarınızı buraya sürükleyip bırakın.
    
    Drag and drop your Excel or CSV files here.
    """)
    
    uploaded_files = st.file_uploader(
        "Excel/CSV dosyaları seçin",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_content = uploaded_file.read()
            file_hash = MetadataManager.calculate_hash(file_content)
            
            # Check if file already exists
            existing_id = metadata_manager.file_exists(file_hash)
            if existing_id:
                st.warning(f"⚠️ '{uploaded_file.name}' zaten yüklendi / already uploaded (ID: {existing_id})")
                continue
            
            # Analyze file
            with st.spinner(f"Analyzing {uploaded_file.name}..."):
                analysis = analyze_excel_file(file_content, uploaded_file.name)
            
            if "error" in analysis:
                st.error(f"❌ Error analyzing {uploaded_file.name}: {analysis['error']}")
                continue
            
            # Generate ID and save file
            file_id = MetadataManager.generate_file_id(file_content)
            stored_path = file_cache.save_file(file_id, file_content, uploaded_file.name)
            
            # Create metadata
            metadata = FileMetadata(
                file_id=file_id,
                original_name=uploaded_file.name,
                stored_path=str(stored_path),
                upload_date=datetime.now().isoformat(),
                file_size=len(file_content),
                file_hash=file_hash,
                sheet_names=analysis["sheet_names"],
                row_count=analysis["row_count"],
                column_count=analysis["column_count"],
                bank_name=analysis.get("bank_name"),
                total_amount=analysis.get("total_amount", 0),
                date_range=analysis.get("date_range"),
                processing_status="pending"
            )
            
            metadata_manager.add_file(metadata)
            
            st.success(f"""
            ✅ **{uploaded_file.name}** yüklendi / uploaded
            - ID: `{file_id}`
            - Sheets: {', '.join(analysis['sheet_names'])}
            - Rows: {analysis['row_count']:,}
            - Bank: {analysis.get('bank_name', 'Unknown')}
            """)


def render_file_list(metadata_manager: MetadataManager, file_cache: FileCache):
    """Render list of uploaded files."""
    st.header("📁 Yüklenen Dosyalar / Uploaded Files")
    
    files = metadata_manager.get_all_files()
    
    if not files:
        st.info("Henüz dosya yüklenmedi / No files uploaded yet")
        return
    
    # Summary
    summary = metadata_manager.get_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Dosya", summary["total_files"])
    col2.metric("Toplam Boyut", f"{summary['total_size_mb']:.2f} MB")
    col3.metric("İşlenen", summary["processed_count"])
    col4.metric("Bekleyen", summary["pending_count"])
    
    st.markdown("---")
    
    # File list
    for metadata in files:
        with st.expander(f"📄 {metadata.original_name}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **ID:** `{metadata.file_id}`  
                **Yükleme Tarihi:** {metadata.upload_date[:10]}  
                **Boyut:** {metadata.file_size / 1024:.1f} KB  
                **Sheets:** {', '.join(metadata.sheet_names)}  
                **Satır Sayısı:** {metadata.row_count:,}  
                **Banka:** {metadata.bank_name or 'Belirtilmedi'}  
                **Toplam Tutar:** ₺{metadata.total_amount:,.2f}  
                **Durum:** {'✅ İşlendi' if metadata.processing_status == 'processed' else '⏳ Bekliyor'}
                """)
                
                if metadata.date_range:
                    st.markdown(f"**Tarih Aralığı:** {metadata.date_range['start']} - {metadata.date_range['end']}")
                
                if metadata.notes:
                    st.markdown(f"**Notlar:** {metadata.notes}")
            
            with col2:
                # Actions
                if st.button("🔍 Önizle", key=f"preview_{metadata.file_id}"):
                    df = file_cache.load_dataframe(metadata.file_id)
                    if df is not None:
                        st.dataframe(df.head(100), height=300)
                
                if st.button("🗑️ Sil", key=f"delete_{metadata.file_id}"):
                    file_cache.delete_file(metadata.file_id)
                    metadata_manager.delete_file(metadata.file_id)
                    st.rerun()
                
                # Edit notes
                new_notes = st.text_input("Notlar", value=metadata.notes, key=f"notes_{metadata.file_id}")
                if new_notes != metadata.notes:
                    metadata_manager.update_file(metadata.file_id, notes=new_notes)


def render_cache_management(metadata_manager: MetadataManager, file_cache: FileCache):
    """Render cache management section."""
    st.header("🗄️ Önbellek Yönetimi / Cache Management")
    
    cache_size = file_cache.get_cache_size()
    st.metric("Önbellek Boyutu / Cache Size", f"{cache_size / (1024*1024):.2f} MB")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Önbelleği Temizle / Clear Cache", type="secondary"):
            count = file_cache.clear_cache()
            # Also clear metadata
            for f in metadata_manager.get_all_files():
                metadata_manager.delete_file(f.file_id)
            st.success(f"✅ {count} dosya silindi / files deleted")
            st.rerun()
    
    with col2:
        # Export metadata
        if st.button("📥 Metadata İndir / Export Metadata"):
            import json
            files = metadata_manager.get_all_files()
            data = [f.to_dict() for f in files]
            st.download_button(
                label="Download JSON",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="files_metadata.json",
                mime="application/json"
            )


def main():
    st.set_page_config(
        page_title="File Upload - Cash Flow Dashboard",
        page_icon="📤",
        layout="wide"
    )
    
    st.title("📤 Dosya Yönetimi / File Management")
    st.markdown("---")
    
    metadata_manager, file_cache = init_managers()
    
    tab1, tab2, tab3 = st.tabs(["📤 Yükle", "📁 Dosyalar", "🗄️ Önbellek"])
    
    with tab1:
        render_upload_section(metadata_manager, file_cache)
    
    with tab2:
        render_file_list(metadata_manager, file_cache)
    
    with tab3:
        render_cache_management(metadata_manager, file_cache)


if __name__ == "__main__":
    main()
