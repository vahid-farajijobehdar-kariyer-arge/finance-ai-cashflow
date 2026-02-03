"""
🔍 Veri Kontrolü

Dosya bazında veri kalitesi kontrolü, eksik veri tespiti ve tutarlılık analizi.
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control, get_control_summary

# Data paths
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"

st.set_page_config(page_title="Veri Kontrolü", page_icon="🔍", layout="wide")


@st.cache_data
def load_all_files_with_metadata():
    """Load all files with per-file metadata for validation."""
    if not RAW_PATH.exists():
        return None, []
    
    reader = BankFileReader()
    files = list(RAW_PATH.glob("*.csv")) + list(RAW_PATH.glob("*.xlsx")) + list(RAW_PATH.glob("*.xls"))
    files = [f for f in files if not f.name.startswith(".")]
    
    if not files:
        return None, []
    
    all_data = []
    file_stats = []
    
    for file_path in files:
        try:
            df = reader.read_file(file_path)
            df["source_file"] = file_path.name
            
            # Get file stats
            stats = {
                "dosya": file_path.name,
                "satir_sayisi": len(df),
                "boyut_kb": file_path.stat().st_size / 1024,
                "degistirilme": datetime.fromtimestamp(file_path.stat().st_mtime),
                "banka": df["bank_name"].iloc[0] if "bank_name" in df.columns and len(df) > 0 else "Bilinmiyor",
            }
            
            # Check for common issues
            issues = []
            
            # Check for empty columns
            empty_cols = df.columns[df.isna().all()].tolist()
            if empty_cols:
                issues.append(f"Boş sütunlar: {', '.join(empty_cols[:3])}")
            
            # Check for missing critical columns
            required_cols = ["gross_amount", "transaction_date", "bank_name"]
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                issues.append(f"Eksik sütunlar: {', '.join(missing_cols)}")
            
            # Check for null values in critical columns
            if "gross_amount" in df.columns:
                null_amount = df["gross_amount"].isna().sum()
                if null_amount > 0:
                    issues.append(f"Tutar boş: {null_amount} satır")
            
            if "transaction_date" in df.columns:
                null_date = df["transaction_date"].isna().sum()
                if null_date > 0:
                    issues.append(f"Tarih boş: {null_date} satır")
            
            # Check for duplicate transactions
            if "gross_amount" in df.columns and "transaction_date" in df.columns:
                potential_dups = df.duplicated(subset=["gross_amount", "transaction_date"], keep=False).sum()
                if potential_dups > 10:
                    issues.append(f"Potansiyel tekrar: {potential_dups} satır")
            
            # Check date range
            if "transaction_date" in df.columns:
                dates = pd.to_datetime(df["transaction_date"], errors="coerce")
                valid_dates = dates.dropna()
                if len(valid_dates) > 0:
                    stats["min_tarih"] = valid_dates.min()
                    stats["max_tarih"] = valid_dates.max()
                    
                    # Check for future dates
                    future = (valid_dates > datetime.now()).sum()
                    if future > 0:
                        issues.append(f"Gelecek tarih: {future} satır")
            
            # Calculate totals
            if "gross_amount" in df.columns:
                stats["toplam_tutar"] = df["gross_amount"].sum()
            if "commission_amount" in df.columns:
                stats["toplam_komisyon"] = df["commission_amount"].sum()
            if "net_amount" in df.columns:
                stats["toplam_net"] = df["net_amount"].sum()
            
            stats["sorunlar"] = issues
            stats["sorun_sayisi"] = len(issues)
            stats["durum"] = "✅ Temiz" if len(issues) == 0 else f"⚠️ {len(issues)} Sorun"
            
            file_stats.append(stats)
            all_data.append(df)
            
        except Exception as e:
            file_stats.append({
                "dosya": file_path.name,
                "satir_sayisi": 0,
                "boyut_kb": file_path.stat().st_size / 1024,
                "degistirilme": datetime.fromtimestamp(file_path.stat().st_mtime),
                "banka": "Hata",
                "sorunlar": [f"Okuma hatası: {str(e)}"],
                "sorun_sayisi": 1,
                "durum": "❌ Hata"
            })
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df, file_stats
    
    return None, file_stats


def display_file_overview(file_stats: list):
    """Display overview of all loaded files."""
    st.subheader("📁 Dosya Durumu")
    
    if not file_stats:
        st.warning("Hiç dosya bulunamadı. Önce dosya yükleyin.")
        return
    
    # Summary metrics
    total_files = len(file_stats)
    clean_files = sum(1 for f in file_stats if f.get("sorun_sayisi", 0) == 0)
    problem_files = total_files - clean_files
    total_rows = sum(f.get("satir_sayisi", 0) for f in file_stats)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Dosya", total_files)
    col2.metric("Temiz Dosya", clean_files, delta=f"{clean_files/total_files*100:.0f}%")
    col3.metric("Sorunlu Dosya", problem_files, delta=f"-{problem_files}" if problem_files > 0 else None, delta_color="inverse")
    col4.metric("Toplam Satır", f"{total_rows:,}")
    
    st.markdown("---")
    
    # File details table
    st.markdown("### 📋 Dosya Detayları")
    
    df_stats = pd.DataFrame(file_stats)
    
    # Format for display
    display_cols = ["dosya", "banka", "satir_sayisi", "boyut_kb", "durum"]
    if "min_tarih" in df_stats.columns:
        display_cols.insert(3, "min_tarih")
        display_cols.insert(4, "max_tarih")
    
    available_cols = [c for c in display_cols if c in df_stats.columns]
    
    st.dataframe(
        df_stats[available_cols].style.format({
            "boyut_kb": "{:.1f} KB",
            "satir_sayisi": "{:,}"
        }),
        hide_index=True,
        use_container_width=True
    )
    
    # Show issues for problem files
    problem_stats = [f for f in file_stats if f.get("sorun_sayisi", 0) > 0]
    if problem_stats:
        st.markdown("### ⚠️ Tespit Edilen Sorunlar")
        
        for stat in problem_stats:
            with st.expander(f"📄 {stat['dosya']} - {stat['durum']}", expanded=True):
                for issue in stat.get("sorunlar", []):
                    st.warning(f"• {issue}")


def display_data_quality_checks(df: pd.DataFrame):
    """Display comprehensive data quality checks."""
    st.subheader("🔬 Veri Kalitesi Analizi")
    
    if df is None or df.empty:
        st.warning("Veri bulunamadı.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Sütun Doluluk Oranları")
        
        # Calculate fill rates
        fill_rates = []
        for col in df.columns:
            non_null = df[col].notna().sum()
            fill_rate = non_null / len(df) * 100
            fill_rates.append({
                "Sütun": col,
                "Dolu Satır": non_null,
                "Doluluk %": fill_rate
            })
        
        fill_df = pd.DataFrame(fill_rates)
        fill_df = fill_df.sort_values("Doluluk %")
        
        # Show only columns with < 100% fill rate
        incomplete = fill_df[fill_df["Doluluk %"] < 100]
        
        if len(incomplete) > 0:
            fig = px.bar(
                incomplete.tail(15),
                x="Doluluk %",
                y="Sütun",
                orientation="h",
                title="Eksik Veri Olan Sütunlar",
                color="Doluluk %",
                color_continuous_scale="RdYlGn"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, key="fill_rates")
        else:
            st.success("✅ Tüm sütunlar tam dolu!")
    
    with col2:
        st.markdown("#### 📈 Banka Bazında Veri Dağılımı")
        
        if "bank_name" in df.columns:
            bank_counts = df["bank_name"].value_counts()
            
            fig = px.pie(
                values=bank_counts.values,
                names=bank_counts.index,
                title="Banka Dağılımı",
                hole=0.4
            )
            st.plotly_chart(fig, key="bank_dist")
        else:
            st.info("Banka bilgisi bulunamadı.")
    
    st.markdown("---")
    
    # Date gap analysis
    st.markdown("#### 📅 Tarih Aralığı Analizi")
    
    if "transaction_date" in df.columns:
        dates = pd.to_datetime(df["transaction_date"], errors="coerce")
        valid_dates = dates.dropna()
        
        if len(valid_dates) > 0:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("En Eski Tarih", valid_dates.min().strftime("%d/%m/%Y"))
            col2.metric("En Yeni Tarih", valid_dates.max().strftime("%d/%m/%Y"))
            col3.metric("Gün Aralığı", f"{(valid_dates.max() - valid_dates.min()).days} gün")
            col4.metric("Geçersiz Tarih", f"{len(dates) - len(valid_dates)} satır")
            
            # Daily transaction count
            daily_counts = valid_dates.dt.date.value_counts().sort_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_counts.index,
                y=daily_counts.values,
                mode="lines+markers",
                name="İşlem Sayısı"
            ))
            fig.update_layout(
                title="Günlük İşlem Sayısı",
                xaxis_title="Tarih",
                yaxis_title="İşlem Sayısı"
            )
            st.plotly_chart(fig, key="daily_counts", use_container_width=True)
            
            # Check for missing days
            if len(daily_counts) > 1:
                all_days = pd.date_range(start=valid_dates.min(), end=valid_dates.max(), freq='D')
                existing_days = set(valid_dates.dt.date)
                missing_days = [d.date() for d in all_days if d.date() not in existing_days]
                
                # Filter out weekends
                missing_weekdays = [d for d in missing_days if d.weekday() < 5]
                
                if missing_weekdays:
                    st.warning(f"⚠️ **{len(missing_weekdays)} iş günü eksik** (hafta sonları hariç)")
                    
                    with st.expander("Eksik Günler"):
                        for d in missing_weekdays[:30]:
                            st.write(f"• {d.strftime('%d/%m/%Y (%A)')}")
                        if len(missing_weekdays) > 30:
                            st.write(f"... ve {len(missing_weekdays) - 30} gün daha")
                else:
                    st.success("✅ Tüm iş günleri mevcut!")


def display_commission_validation(df: pd.DataFrame):
    """Display commission rate validation."""
    st.subheader("💰 Komisyon Oranı Kontrolü")
    
    if df is None or df.empty:
        st.warning("Veri bulunamadı.")
        return
    
    # Apply commission control
    df_controlled = add_commission_control(df.copy())
    
    if "rate_match" not in df_controlled.columns:
        st.info("Komisyon kontrol bilgisi hesaplanamadı.")
        return
    
    # Summary
    total = len(df_controlled)
    matched = df_controlled["rate_match"].sum()
    mismatched = total - matched
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İşlem", f"{total:,}")
    col2.metric("Doğru Oran", f"{matched:,}", delta=f"{matched/total*100:.1f}%")
    col3.metric("Fark Var", f"{mismatched:,}", delta=f"-{mismatched/total*100:.1f}%" if mismatched > 0 else None, delta_color="inverse")
    
    if mismatched == 0:
        st.success("✅ Tüm komisyon oranları beklenen değerlerle eşleşiyor!")
    else:
        st.warning(f"⚠️ {mismatched:,} işlemde komisyon farkı tespit edildi.")
        
        # Show mismatched by bank
        if "bank_name" in df_controlled.columns:
            mismatch_by_bank = df_controlled[~df_controlled["rate_match"]].groupby("bank_name").size()
            
            if len(mismatch_by_bank) > 0:
                st.markdown("**Banka Bazında Fark:**")
                for bank, count in mismatch_by_bank.items():
                    st.write(f"• {bank}: {count:,} işlem")


def display_duplicate_check(df: pd.DataFrame):
    """Check for potential duplicate transactions."""
    st.subheader("🔄 Tekrar Eden İşlem Kontrolü")
    
    if df is None or df.empty:
        st.warning("Veri bulunamadı.")
        return
    
    # Check for exact duplicates
    dup_cols = ["gross_amount", "transaction_date", "bank_name"]
    available_cols = [c for c in dup_cols if c in df.columns]
    
    if len(available_cols) >= 2:
        duplicates = df[df.duplicated(subset=available_cols, keep=False)]
        
        if len(duplicates) > 0:
            st.warning(f"⚠️ **{len(duplicates):,} potansiyel tekrar eden işlem** tespit edildi.")
            
            with st.expander("Tekrar Eden İşlemler (ilk 50)"):
                display_cols = ["transaction_date", "bank_name", "gross_amount", "commission_amount"]
                display_cols = [c for c in display_cols if c in duplicates.columns]
                st.dataframe(duplicates[display_cols].head(50), hide_index=True)
        else:
            st.success("✅ Tekrar eden işlem tespit edilmedi!")
    else:
        st.info("Tekrar kontrolü için yeterli sütun bulunamadı.")


def main():
    st.title("🔍 Veri Kontrolü")
    st.markdown("Yüklenen dosyaların kalite kontrolü ve tutarlılık analizi.")
    st.markdown("---")
    
    # Load data
    df, file_stats = load_all_files_with_metadata()
    
    if not file_stats:
        st.error(f"""
        ❌ Dosya bulunamadı.
        
        Beklenen dizin: `{RAW_PATH}`
        
        Önce '📤 Dosya Yükle' sayfasından dosya yükleyin.
        """)
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📁 Dosya Durumu",
        "🔬 Veri Kalitesi",
        "💰 Komisyon Kontrolü",
        "🔄 Tekrar Kontrolü"
    ])
    
    with tab1:
        display_file_overview(file_stats)
    
    with tab2:
        display_data_quality_checks(df)
    
    with tab3:
        display_commission_validation(df)
    
    with tab4:
        display_duplicate_check(df)


if __name__ == "__main__":
    main()
