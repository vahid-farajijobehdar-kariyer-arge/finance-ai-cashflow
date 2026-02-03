"""
💳 Komisyon Oranları - Banka komisyon oranlarını görüntüle ve düzenle

Özellikler:
- Oranları görüntüle
- Oranları düzenle
- Dosyadan veya URL'den içe aktar
- Değişiklik geçmişi
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password


st.set_page_config(
    page_title="Komisyon Oranları - POS Komisyon",
    page_icon="💳",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("💳 Komisyon Oranları")
st.markdown("**Banka komisyon oranlarını görüntüle ve düzenle**")
st.markdown("---")

# Rate Manager import
try:
    from processing.rate_manager import get_rate_manager
    rate_manager = get_rate_manager()
except Exception as e:
    st.error(f"Oran yöneticisi yüklenemedi: {e}")
    st.stop()


def display_current_rates():
    """Mevcut oranları göster."""
    st.subheader("📋 Mevcut Komisyon Oranları")
    
    config = rate_manager.get_current_rates()
    banks = config.get("banks", {})
    
    if not banks:
        st.warning("Henüz komisyon oranı tanımlanmamış.")
        return
    
    # Versiyon bilgisi
    version_info = rate_manager.get_rate_version_info()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Versiyon", version_info.get("version", "-"))
    with col2:
        last_updated = version_info.get("last_updated", "-")
        if last_updated and last_updated != "-":
            try:
                last_updated = datetime.fromisoformat(last_updated).strftime("%d.%m.%Y %H:%M")
            except:
                pass
        st.metric("Son Güncelleme", last_updated)
    with col3:
        st.metric("Banka Sayısı", version_info.get("bank_count", 0))
    
    st.markdown("---")
    
    # Oran tablosu
    rows = []
    for bank_key, bank_data in banks.items():
        bank_name = bank_data.get("aliases", [bank_key])[0] if bank_data.get("aliases") else bank_key
        rates = bank_data.get("rates", {})
        
        row = {"Banka": bank_name, "Kod": bank_key}
        for inst in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
            rate = rates.get(inst)
            col_name = "Peşin" if inst == 1 else str(inst)
            if rate is not None:
                row[col_name] = f"%{rate*100:.2f}"
            else:
                row[col_name] = "-"
        rows.append(row)
    
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_rate_editor():
    """Oran düzenleme arayüzü."""
    st.subheader("✏️ Oran Düzenleme")
    
    config = rate_manager.get_current_rates()
    banks = config.get("banks", {})
    
    if not banks:
        st.warning("Düzenlenecek banka bulunamadı.")
        return
    
    bank_options = {
        bank_key: bank_data.get("aliases", [bank_key])[0] if bank_data.get("aliases") else bank_key
        for bank_key, bank_data in banks.items()
    }
    
    selected_bank = st.selectbox(
        "Banka Seçin",
        options=list(bank_options.keys()),
        format_func=lambda x: bank_options[x]
    )
    
    if selected_bank:
        bank_data = banks[selected_bank]
        current_rates = bank_data.get("rates", {})
        
        st.markdown(f"**{bank_options[selected_bank]}** için oranlar:")
        
        with st.form(key=f"edit_rates_{selected_bank}"):
            new_rates = {}
            cols = st.columns(6)
            
            for i, inst in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]):
                col_idx = i % 6
                with cols[col_idx]:
                    label = "Peşin" if inst == 1 else f"{inst} Taksit"
                    current_rate = current_rates.get(inst, 0.0)
                    
                    new_pct = st.number_input(
                        label,
                        min_value=0.0,
                        max_value=50.0,
                        value=current_rate * 100,
                        step=0.01,
                        format="%.2f",
                        key=f"rate_{selected_bank}_{inst}"
                    )
                    new_rates[inst] = new_pct / 100
            
            submitted = st.form_submit_button("💾 Oranları Kaydet", use_container_width=True)
            
            if submitted:
                final_rates = {inst: round(rate, 6) for inst, rate in new_rates.items() if rate > 0 or inst in current_rates}
                success = rate_manager.update_all_bank_rates(selected_bank, final_rates, user="dashboard")
                
                if success:
                    st.success(f"✅ {bank_options[selected_bank]} oranları güncellendi!")
                    st.rerun()
                else:
                    st.error("❌ Oranlar güncellenemedi.")


def display_import_export():
    """İçe/dışa aktarma arayüzü."""
    st.subheader("📥 İçe/Dışa Aktarma")
    
    tab1, tab2, tab3 = st.tabs(["📁 Dosyadan", "🌐 URL'den", "📤 Dışa Aktar"])
    
    with tab1:
        st.markdown("YAML veya CSV dosyası yükleyerek oranları güncelleyin.")
        
        uploaded_file = st.file_uploader(
            "Dosya Seçin",
            type=["yaml", "yml", "csv"],
            key="rate_file"
        )
        
        if uploaded_file:
            temp_path = Path("/tmp") / uploaded_file.name
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            if st.button("📥 İçe Aktar", key="import_file"):
                result = rate_manager.import_from_file(str(temp_path), user="dashboard")
                if result.get("success"):
                    st.success(f"✅ {result.get('message')}")
                    st.rerun()
                else:
                    st.error(f"❌ Hata: {result.get('error')}")
        
        st.markdown("---")
        st.markdown("**Beklenen CSV formatı:**")
        st.code("bank_key,installment,rate\nvakifbank,1,0.0336\nvakifbank,2,0.0499\n...")
    
    with tab2:
        st.markdown("Uzak bir URL'den YAML veya JSON formatında oranları içe aktarın.")
        
        url = st.text_input("URL", placeholder="https://example.com/rates.yaml", key="rate_url")
        
        if url:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Karşılaştır", key="compare_url"):
                    result = rate_manager.compare_with_source(url)
                    if result.get("success"):
                        if result.get("has_differences"):
                            st.warning(f"⚠️ {result.get('difference_count')} farklılık bulundu:")
                            diff_df = pd.DataFrame(result.get("differences", []))
                            st.dataframe(diff_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("✅ Oranlar güncel, fark yok.")
                    else:
                        st.error(f"❌ Hata: {result.get('error')}")
            
            with col2:
                if st.button("📥 İçe Aktar", key="import_url"):
                    result = rate_manager.import_from_url(url, user="dashboard")
                    if result.get("success"):
                        st.success(f"✅ {result.get('message')}")
                        st.rerun()
                    else:
                        st.error(f"❌ Hata: {result.get('error')}")
    
    with tab3:
        st.markdown("Mevcut oranları YAML veya CSV olarak indirin.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            yaml_content = rate_manager.export_current_rates(format="yaml")
            st.download_button(
                label="📥 YAML İndir",
                data=yaml_content,
                file_name=f"komisyon_oranlari_{datetime.now().strftime('%Y%m%d')}.yaml",
                mime="text/yaml",
                use_container_width=True
            )
        
        with col2:
            csv_content = rate_manager.export_current_rates(format="csv")
            st.download_button(
                label="📥 CSV İndir",
                data=csv_content,
                file_name=f"komisyon_oranlari_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )


def display_history():
    """Değişiklik geçmişi."""
    st.subheader("📜 Değişiklik Geçmişi")
    
    history = rate_manager.get_change_history(limit=20)
    
    if not history:
        st.info("Henüz değişiklik geçmişi yok.")
        return
    
    type_icons = {
        "rate_update": "✏️",
        "bulk_rate_update": "📝",
        "file_import": "📁",
        "csv_import": "📊",
        "url_import": "🌐"
    }
    
    for change in reversed(history):
        try:
            timestamp = datetime.fromisoformat(change.get("timestamp", "")).strftime("%d.%m.%Y %H:%M")
        except:
            timestamp = change.get("timestamp", "-")
        
        change_type = change.get("type", "unknown")
        user = change.get("user", "sistem")
        details = change.get("details", {})
        icon = type_icons.get(change_type, "📌")
        
        with st.expander(f"{icon} {timestamp} - {change_type} ({user})"):
            if change_type in ["rate_update", "bulk_rate_update"]:
                st.markdown(f"**Banka:** {details.get('bank', '-')}")
                if "changes" in details:
                    changes_df = pd.DataFrame(details["changes"])
                    st.dataframe(changes_df, use_container_width=True, hide_index=True)
            else:
                if details.get("source_file"):
                    st.markdown(f"**Kaynak:** {details.get('source_file')}")
                if details.get("source_url"):
                    st.markdown(f"**URL:** {details.get('source_url')}")


# Main layout with tabs
tabs = st.tabs(["📋 Oranlar", "✏️ Düzenle", "📥 İçe/Dışa Aktar", "📜 Geçmiş"])

with tabs[0]:
    display_current_rates()

with tabs[1]:
    display_rate_editor()

with tabs[2]:
    display_import_export()

with tabs[3]:
    display_history()

# Footer
st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi")
