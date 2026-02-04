"""
⚙️ Ayarlar - Komisyon oranları ve Excel sütun eşleştirmeleri

Özellikler:
- Komisyon oranlarını görüntüle ve düzenle
- Excel/CSV sütun eşleştirmelerini görüntüle
- Dosyadan veya URL'den içe aktar
- Değişiklik geçmişi
"""

import streamlit as st
import pandas as pd
import yaml
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password

# Config paths
CONFIG_PATH = PROJECT_ROOT.parent / "config"
BANKS_CONFIG = CONFIG_PATH / "banks.yaml"
SETTINGS_CONFIG = CONFIG_PATH / "settings.yaml"


def load_settings():
    """Load settings.yaml configuration."""
    try:
        if SETTINGS_CONFIG.exists():
            with open(SETTINGS_CONFIG, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    except Exception:
        pass
    return {}


def save_settings(settings: dict):
    """Save settings.yaml configuration."""
    try:
        with open(SETTINGS_CONFIG, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False


st.set_page_config(
    page_title="Ayarlar - POS Komisyon",
    page_icon="⚙️",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("⚙️ Ayarlar")
st.markdown("**Komisyon oranları ve sütun eşleştirmeleri**")
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
main_tabs = st.tabs(["💳 Komisyon Oranları", "� Mevduat Oranları", "📊 Excel Sütunları"])

with main_tabs[0]:
    # Komisyon Oranları Tab
    tabs = st.tabs(["📋 Oranlar", "✏️ Düzenle", "📥 İçe/Dışa Aktar", "📜 Geçmiş"])

    with tabs[0]:
        display_current_rates()

    with tabs[1]:
        display_rate_editor()

    with tabs[2]:
        display_import_export()

    with tabs[3]:
        display_history()

with main_tabs[1]:
    # Mevduat Oranları Tab (Gelecek Değer için)
    st.subheader("💹 Mevduat Faiz Oranları")
    st.markdown("Gelecek Değer hesaplayıcısında kullanılan banka mevduat faiz oranları.")
    
    # Load current settings
    settings = load_settings()
    deposit_rates = settings.get("deposit_rates", {})
    
    if not deposit_rates:
        st.warning("Henüz mevduat oranı tanımlanmamış. Varsayılan oranlar kullanılacak.")
    
    # Display current rates
    st.markdown("#### 📋 Mevcut Mevduat Oranları")
    
    rate_rows = []
    for bank_key, bank_data in deposit_rates.items():
        bank_name = bank_data.get("name", bank_key)
        rates = bank_data.get("rates", {})
        rate_rows.append({
            "Banka": bank_name,
            "Kod": bank_key,
            "3 Ay": f"%{rates.get(3, 0)*100:.1f}" if rates.get(3) else "-",
            "6 Ay": f"%{rates.get(6, 0)*100:.1f}" if rates.get(6) else "-",
            "12 Ay": f"%{rates.get(12, 0)*100:.1f}" if rates.get(12) else "-"
        })
    
    if rate_rows:
        st.dataframe(pd.DataFrame(rate_rows), use_container_width=True, hide_index=True)
    
    # Edit rates
    st.markdown("---")
    st.markdown("#### ✏️ Oranları Düzenle")
    
    bank_list = list(deposit_rates.keys()) if deposit_rates else ["ziraat", "halkbank", "vakifbank", "garanti", "akbank", "isbank", "ykb", "qnb"]
    bank_names = {k: deposit_rates.get(k, {}).get("name", k.title()) for k in bank_list}
    
    selected_deposit_bank = st.selectbox(
        "Banka Seçin",
        options=bank_list,
        format_func=lambda x: bank_names.get(x, x),
        key="deposit_bank_select"
    )
    
    if selected_deposit_bank:
        current_bank_rates = deposit_rates.get(selected_deposit_bank, {}).get("rates", {})
        
        with st.form(key=f"deposit_rates_{selected_deposit_bank}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                rate_3 = st.number_input(
                    "3 Aylık Oran (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=current_bank_rates.get(3, 0.40) * 100,
                    step=0.1,
                    format="%.1f",
                    key=f"dep_rate_3_{selected_deposit_bank}"
                )
            
            with col2:
                rate_6 = st.number_input(
                    "6 Aylık Oran (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=current_bank_rates.get(6, 0.38) * 100,
                    step=0.1,
                    format="%.1f",
                    key=f"dep_rate_6_{selected_deposit_bank}"
                )
            
            with col3:
                rate_12 = st.number_input(
                    "12 Aylık Oran (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=current_bank_rates.get(12, 0.36) * 100,
                    step=0.1,
                    format="%.1f",
                    key=f"dep_rate_12_{selected_deposit_bank}"
                )
            
            submitted = st.form_submit_button("💾 Oranları Kaydet", use_container_width=True)
            
            if submitted:
                # Update settings
                if "deposit_rates" not in settings:
                    settings["deposit_rates"] = {}
                
                if selected_deposit_bank not in settings["deposit_rates"]:
                    settings["deposit_rates"][selected_deposit_bank] = {
                        "name": bank_names.get(selected_deposit_bank, selected_deposit_bank.title())
                    }
                
                settings["deposit_rates"][selected_deposit_bank]["rates"] = {
                    3: round(rate_3 / 100, 4),
                    6: round(rate_6 / 100, 4),
                    12: round(rate_12 / 100, 4)
                }
                
                if save_settings(settings):
                    st.success(f"✅ {bank_names.get(selected_deposit_bank)} mevduat oranları güncellendi!")
                    st.rerun()
                else:
                    st.error("❌ Oranlar kaydedilemedi.")

with main_tabs[2]:
    # Excel Sütunları Tab
    st.subheader("📊 Banka Sütun Eşleştirmeleri")
    st.markdown("Her banka için Excel/CSV sütunlarının nasıl eşleştirildiğini gösterir.")
    
    # Load banks.yaml
    try:
        if BANKS_CONFIG.exists():
            with open(BANKS_CONFIG, "r", encoding="utf-8") as f:
                banks_config = yaml.safe_load(f)
        else:
            st.error(f"banks.yaml dosyası bulunamadı: {BANKS_CONFIG}")
            banks_config = {}
    except Exception as e:
        st.error(f"Yapılandırma dosyası okunamadı: {e}")
        banks_config = {}
    
    if banks_config:
        banks = banks_config.get("banks", {})
        
        # Banka seçimi
        bank_options = {
            key: data.get("display_name", data.get("name", key))
            for key, data in banks.items()
        }
        
        selected_bank = st.selectbox(
            "Banka Seçin",
            options=list(bank_options.keys()),
            format_func=lambda x: bank_options[x],
            key="excel_bank_select"
        )
        
        if selected_bank:
            bank_data = banks[selected_bank]
            
            col1, col2 = st.columns(2, gap="large")
            
            with col1:
                st.markdown("#### 📄 Banka Bilgileri")
                info_data = {
                    "Özellik": ["Kod", "Görünen Ad", "Dosya Deseni", "Ayırıcı", "Encoding", "Atlanan Satır"],
                    "Değer": [
                        selected_bank,
                        bank_data.get("display_name", "-"),
                        bank_data.get("file_pattern", "-"),
                        bank_data.get("delimiter", "Excel"),
                        bank_data.get("encoding", "UTF-8"),
                        str(bank_data.get("skip_rows", 0))
                    ]
                }
                st.dataframe(pd.DataFrame(info_data), use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 🔄 Sütun Eşleştirmeleri")
                raw_columns = bank_data.get("raw_columns", {})
                
                if raw_columns:
                    mapping_data = {
                        "Ham Sütun": list(raw_columns.keys()),
                        "Hedef Sütun": list(raw_columns.values())
                    }
                    st.dataframe(pd.DataFrame(mapping_data), use_container_width=True, hide_index=True)
                else:
                    st.info("Bu banka için sütun eşleştirmesi tanımlanmamış.")
        
        # Tüm eşleştirmeleri gösteren özet tablo
        st.markdown("---")
        st.markdown("#### 📋 Tüm Bankaların Özet Tablosu")
        
        summary_rows = []
        for bank_key, bank_data in banks.items():
            raw_columns = bank_data.get("raw_columns", {})
            summary_rows.append({
                "Banka": bank_data.get("display_name", bank_key),
                "Kod": bank_key,
                "Dosya Formatı": "CSV" if bank_data.get("delimiter") else "Excel",
                "Sütun Sayısı": len(raw_columns),
                "Encoding": bank_data.get("encoding", "UTF-8")
            })
        
        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # banks.yaml dosyasını indir
        st.markdown("---")
        with open(BANKS_CONFIG, "r", encoding="utf-8") as f:
            yaml_content = f.read()
        
        st.download_button(
            label="📥 banks.yaml İndir",
            data=yaml_content,
            file_name="banks.yaml",
            mime="text/yaml"
        )

# Footer
st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi")
