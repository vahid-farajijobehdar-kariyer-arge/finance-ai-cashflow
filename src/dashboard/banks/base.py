"""
Banka Detay Sayfası Temel Şablonu

Tüm banka detay sayfaları bu şablonu kullanır.
DRY prensibi: Ortak kod tek yerde.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sys

# Proje yolunu ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.reader import BankFileReader
from src.processing.commission_control import add_commission_control
from src.processing.calculator import filter_successful_transactions


# Sabitler
RAW_PATH = PROJECT_ROOT / "data" / "raw"

# Banka tanımları
BANK_DEFINITIONS = {
    "akbank": {
        "name": "Akbank",
        "display_name": "AKBANK T.A.Ş.",
        "icon": "🏦",
        "color": "#E30613",
        "patterns": ["akbank", "AKBANK"]
    },
    "garanti": {
        "name": "Garanti BBVA",
        "display_name": "T. GARANTİ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#00A651",
        "patterns": ["garanti", "GARANTI", "GARANTİ"]
    },
    "halkbank": {
        "name": "Halkbank",
        "display_name": "TÜRKİYE HALK BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#0066B3",
        "patterns": ["halkbank", "HALKBANK", "halk"]
    },
    "isbank": {
        "name": "İşbank",
        "display_name": "TÜRKİYE İŞ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#003366",
        "patterns": ["isbank", "ISBANK", "İŞBANK", "işbank"]
    },
    "qnb": {
        "name": "QNB Finansbank",
        "display_name": "QNB FİNANSBANK A.Ş.",
        "icon": "🏦",
        "color": "#7B2D8E",
        "patterns": ["qnb", "QNB", "finansbank", "FINANSBANK"]
    },
    "vakifbank": {
        "name": "Vakıfbank",
        "display_name": "T. VAKIFLAR BANKASI T.A.O.",
        "icon": "🏦",
        "color": "#FFCC00",
        "patterns": ["vakif", "VAKIF", "vakıf", "VAKIFBANK"]
    },
    "ykb": {
        "name": "Yapı Kredi",
        "display_name": "YAPI VE KREDİ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#0033A0",
        "patterns": ["ykb", "YKB", "yapikredi", "yapıkredi", "YAPI"]
    },
    "ziraat": {
        "name": "Ziraat Bankası",
        "display_name": "T.C. ZİRAAT BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#009639",
        "patterns": ["ziraat", "ZIRAAT", "ZİRAAT"]
    }
}


def format_currency(value: float) -> str:
    """Türk Lirası formatı."""
    if pd.isna(value):
        return "-"
    return f"₺{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    """Yüzde formatı."""
    if pd.isna(value):
        return "-"
    return f"%{value*100:.2f}".replace(".", ",")


def load_all_data() -> pd.DataFrame:
    """Tüm banka verilerini yükle."""
    if not RAW_PATH.exists():
        return pd.DataFrame()
    
    reader = BankFileReader()
    
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return pd.DataFrame()
    
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Temizle ve işle
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()]
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    
    return df


def filter_bank_data(df: pd.DataFrame, bank_key: str) -> pd.DataFrame:
    """Belirtilen banka verilerini filtrele."""
    if df.empty:
        return pd.DataFrame()
    
    bank_def = BANK_DEFINITIONS.get(bank_key, {})
    patterns = bank_def.get("patterns", [bank_key])
    
    # bank_name veya _source_bank sütununda ara
    mask = pd.Series([False] * len(df))
    
    for col in ["bank_name", "_source_bank"]:
        if col in df.columns:
            for pattern in patterns:
                mask = mask | df[col].astype(str).str.contains(pattern, case=False, na=False)
    
    return df[mask].copy()


class BankDetailPage:
    """Banka detay sayfası şablonu."""
    
    def __init__(self, bank_key: str):
        self.bank_key = bank_key
        self.bank_def = BANK_DEFINITIONS.get(bank_key, {})
        self.name = self.bank_def.get("name", bank_key.title())
        self.display_name = self.bank_def.get("display_name", self.name)
        self.icon = self.bank_def.get("icon", "🏦")
        self.color = self.bank_def.get("color", "#1f77b4")
    
    def render(self):
        """Ana sayfa render."""
        # Sayfa başlığı
        st.title(f"{self.icon} {self.name} Detay")
        st.markdown(f"**{self.display_name}** için detaylı komisyon analizi")
        st.markdown("---")
        
        # Veri yükle
        all_df = load_all_data()
        
        if all_df.empty:
            self._render_no_data()
            return
        
        # Banka verilerini filtrele
        df = filter_bank_data(all_df, self.bank_key)
        
        if df.empty:
            self._render_no_bank_data()
            return
        
        # Sayfa bölümleri
        self._render_summary_metrics(df)
        self._render_pesin_taksitli(df)
        self._render_commission_diff_analysis(df)
        self._render_monthly_trend(df)
        self._render_installment_distribution(df)
        self._render_detail_table(df)
        self._render_export(df)
        
        # Footer
        st.markdown("---")
        st.caption("© 2026 Kariyer.net Finans Ekibi")
    
    def _render_no_data(self):
        """Veri yok mesajı."""
        st.warning("""
        ⚠️ **Veri Bulunamadı**
        
        Henüz yüklenmiş dosya yok.
        
        1. **📤 Dosya Yükle** sayfasına gidin
        2. Banka ekstre dosyalarını yükleyin
        3. Bu sayfaya geri dönün
        """)
    
    def _render_no_bank_data(self):
        """Banka verisi yok mesajı."""
        st.info(f"""
        ℹ️ **{self.name} Verisi Bulunamadı**
        
        {self.name} için yüklenmiş dosya yok.
        
        Dosya yüklediyseniz, dosya adının banka adını içerdiğinden emin olun.
        """)
    
    def _render_summary_metrics(self, df: pd.DataFrame):
        """Özet metrikler."""
        st.subheader("📊 Özet Metrikler")
        
        total_gross = df["gross_amount"].sum() if "gross_amount" in df.columns else 0
        total_commission = df["commission_amount"].sum() if "commission_amount" in df.columns else 0
        total_net = df["net_amount"].sum() if "net_amount" in df.columns else total_gross - total_commission
        avg_rate = (total_commission / total_gross * 100) if total_gross > 0 else 0
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📊 İşlem Sayısı", f"{len(df):,}")
        c2.metric("💵 Brüt Tutar", format_currency(total_gross))
        c3.metric("💳 Komisyon", format_currency(total_commission))
        c4.metric("💰 Net Tutar", format_currency(total_net))
        c5.metric("📈 Ort. Oran", f"%{avg_rate:.2f}")
    
    def _render_pesin_taksitli(self, df: pd.DataFrame):
        """Peşin vs Taksitli karşılaştırma."""
        st.markdown("---")
        st.subheader("💵 Peşin vs Taksitli")
        
        # Taksit sayısına göre ayır
        inst_col = "installment_count" if "installment_count" in df.columns else None
        
        if inst_col is None:
            st.info("Taksit bilgisi bulunamadı.")
            return
        
        pesin_mask = df[inst_col].isin([1, "1", "Peşin", "peşin", "PESIN", "TEK"])
        pesin_df = df[pesin_mask]
        taksitli_df = df[~pesin_mask]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💵 Tek Çekim / Peşin")
            if len(pesin_df) > 0:
                p_gross = pesin_df["gross_amount"].sum()
                p_comm = pesin_df["commission_amount"].sum()
                p_rate = (p_comm / p_gross * 100) if p_gross > 0 else 0
                
                st.metric("İşlem Sayısı", f"{len(pesin_df):,}")
                st.metric("Brüt Tutar", format_currency(p_gross))
                st.metric("Komisyon", format_currency(p_comm))
                st.metric("Ortalama Oran", f"%{p_rate:.2f}")
            else:
                st.info("Tek çekim işlemi yok.")
        
        with col2:
            st.markdown("#### 💳 Taksitli")
            if len(taksitli_df) > 0:
                t_gross = taksitli_df["gross_amount"].sum()
                t_comm = taksitli_df["commission_amount"].sum()
                t_rate = (t_comm / t_gross * 100) if t_gross > 0 else 0
                
                st.metric("İşlem Sayısı", f"{len(taksitli_df):,}")
                st.metric("Brüt Tutar", format_currency(t_gross))
                st.metric("Komisyon", format_currency(t_comm))
                st.metric("Ortalama Oran", f"%{t_rate:.2f}")
            else:
                st.info("Taksitli işlem yok.")
    
    def _render_commission_diff_analysis(self, df: pd.DataFrame):
        """Komisyon fark analizi."""
        st.markdown("---")
        st.subheader("⚠️ Komisyon Fark Analizi")
        
        # Kontrol sütunları var mı?
        has_control = "rate_match" in df.columns and "commission_diff" in df.columns
        
        if not has_control:
            st.info("Komisyon kontrol verisi henüz hesaplanmamış.")
            return
        
        # Özet metrikler
        total_diff = df["commission_diff"].sum()
        diff_count = (df["rate_match"] == False).sum()
        match_count = df["rate_match"].sum()
        match_rate = (match_count / len(df) * 100) if len(df) > 0 else 0
        max_diff = df["commission_diff"].abs().max()
        
        c1, c2, c3, c4 = st.columns(4)
        
        # Renk kodları
        diff_delta = "normal" if abs(total_diff) < 100 else ("inverse" if total_diff > 0 else "normal")
        
        c1.metric(
            "Fark Olan İşlem", 
            f"{diff_count:,}",
            delta=f"{len(df) - diff_count:,} eşleşen",
            delta_color="off"
        )
        c2.metric(
            "Toplam Fark", 
            format_currency(total_diff),
            delta="Fazla ödeme" if total_diff > 0 else ("Az ödeme" if total_diff < 0 else "Tam eşleşme"),
            delta_color=diff_delta
        )
        c3.metric("Maks Fark", format_currency(max_diff))
        c4.metric(
            "Uyum Oranı", 
            f"%{match_rate:.1f}",
            delta="✓" if match_rate > 95 else "⚠️",
            delta_color="off"
        )
        
        # Taksit bazlı fark tablosu
        st.markdown("#### 📊 Taksit Bazında Fark")
        
        inst_col = "installment_count"
        if inst_col in df.columns:
            taksit_diff = df.groupby(inst_col).agg({
                "gross_amount": "sum",
                "commission_amount": "sum",
                "commission_expected": "sum" if "commission_expected" in df.columns else "commission_amount",
                "commission_diff": "sum"
            }).reset_index()
            
            taksit_diff.columns = ["Taksit", "Brüt Tutar", "Gerçek Komisyon", "Beklenen Komisyon", "Fark"]
            
            # Fark yüzdesi
            taksit_diff["Fark %"] = (taksit_diff["Fark"] / taksit_diff["Beklenen Komisyon"].replace(0, 1) * 100).round(2)
            
            # Durum
            taksit_diff["Durum"] = taksit_diff["Fark"].apply(
                lambda x: "✅" if abs(x) < 1 else ("🔴 Fazla" if x > 0 else "🟢 Az")
            )
            
            st.dataframe(
                taksit_diff.style.format({
                    "Brüt Tutar": "₺{:,.2f}",
                    "Gerçek Komisyon": "₺{:,.2f}",
                    "Beklenen Komisyon": "₺{:,.2f}",
                    "Fark": "₺{:,.2f}",
                    "Fark %": "{:.2f}%"
                }),
                width="stretch",
                hide_index=True
            )
            
            # Fark grafiği
            if diff_count > 0:
                fig = px.bar(
                    taksit_diff[taksit_diff["Fark"].abs() > 0],
                    x="Taksit",
                    y="Fark",
                    color="Fark",
                    color_continuous_scale="RdYlGn_r",
                    title="Taksit Bazında Komisyon Farkı"
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, width="stretch")
        
        # Fark olan işlemler detayı
        if diff_count > 0:
            with st.expander(f"📋 Fark Olan İşlemler ({diff_count:,} adet)", expanded=False):
                diff_df = df[df["rate_match"] == False].copy()
                
                display_cols = ["transaction_date", "gross_amount", "commission_amount", 
                              "commission_expected", "commission_diff", "installment_count"]
                display_cols = [c for c in display_cols if c in diff_df.columns]
                
                diff_df["Durum"] = diff_df["commission_diff"].apply(
                    lambda x: "🔴 Fazla" if x > 0 else "🟢 Az"
                )
                display_cols.append("Durum")
                
                st.dataframe(
                    diff_df[display_cols].head(100).style.format({
                        "gross_amount": "₺{:,.2f}",
                        "commission_amount": "₺{:,.2f}",
                        "commission_expected": "₺{:,.2f}",
                        "commission_diff": "₺{:,.2f}"
                    }),
                    width="stretch",
                    hide_index=True
                )
    
    def _render_monthly_trend(self, df: pd.DataFrame):
        """Aylık trend grafiği."""
        st.markdown("---")
        st.subheader("📅 Aylık Trend")
        
        date_col = "transaction_date"
        if date_col not in df.columns:
            st.info("Tarih bilgisi bulunamadı.")
            return
        
        df_copy = df.copy()
        df_copy["_date"] = pd.to_datetime(df_copy[date_col], errors="coerce")
        df_copy["_month"] = df_copy["_date"].dt.to_period("M").astype(str)
        
        monthly = df_copy.groupby("_month").agg({
            "gross_amount": "sum",
            "commission_amount": "sum"
        }).reset_index()
        monthly.columns = ["Ay", "Brüt Tutar", "Komisyon"]
        monthly = monthly.sort_values("Ay")
        
        if len(monthly) == 0:
            st.info("Aylık veri bulunamadı.")
            return
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=monthly["Ay"],
            y=monthly["Brüt Tutar"],
            name="Brüt Tutar",
            marker_color=self.color
        ))
        
        fig.add_trace(go.Scatter(
            x=monthly["Ay"],
            y=monthly["Komisyon"],
            mode="lines+markers",
            name="Komisyon",
            yaxis="y2",
            line=dict(color="red", width=2)
        ))
        
        fig.update_layout(
            title=f"{self.name} - Aylık Çekim ve Komisyon Trendi",
            xaxis_title="Ay",
            yaxis=dict(title="Brüt Tutar (₺)", side="left"),
            yaxis2=dict(title="Komisyon (₺)", side="right", overlaying="y"),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, width="stretch")
    
    def _render_installment_distribution(self, df: pd.DataFrame):
        """Taksit dağılımı."""
        st.markdown("---")
        st.subheader("📊 Taksit Dağılımı")
        
        inst_col = "installment_count"
        if inst_col not in df.columns:
            st.info("Taksit bilgisi bulunamadı.")
            return
        
        taksit_summary = df.groupby(inst_col).agg({
            "gross_amount": "sum",
            "commission_amount": "sum"
        }).reset_index()
        taksit_summary.columns = ["Taksit", "Tutar", "Komisyon"]
        
        # Oran hesapla
        taksit_summary["Oran %"] = (taksit_summary["Komisyon"] / taksit_summary["Tutar"] * 100).round(2)
        taksit_summary["İşlem Sayısı"] = df.groupby(inst_col).size().values
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                taksit_summary,
                x="Taksit",
                y="Tutar",
                title="Taksit Bazında Tutar",
                color="Oran %",
                color_continuous_scale="RdYlGn_r",
                text_auto=".2s"
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            fig = px.pie(
                taksit_summary,
                values="Tutar",
                names="Taksit",
                title="Taksit Dağılımı",
                hole=0.4
            )
            st.plotly_chart(fig, width="stretch")
        
        st.dataframe(
            taksit_summary.style.format({
                "Tutar": "₺{:,.2f}",
                "Komisyon": "₺{:,.2f}",
                "Oran %": "{:.2f}%",
                "İşlem Sayısı": "{:,}"
            }),
            width="stretch",
            hide_index=True
        )
    
    def _render_detail_table(self, df: pd.DataFrame):
        """Detay tablosu."""
        st.markdown("---")
        st.subheader("📋 İşlem Detayları")
        
        with st.expander("Detay Tablosunu Göster", expanded=False):
            display_cols = [
                "transaction_date", "gross_amount", "commission_amount", 
                "net_amount", "installment_count", "commission_rate",
                "rate_expected", "commission_diff", "rate_match"
            ]
            available_cols = [c for c in display_cols if c in df.columns]
            
            # Türkçe isimler
            col_names = {
                "transaction_date": "Tarih",
                "gross_amount": "Brüt Tutar",
                "commission_amount": "Komisyon",
                "net_amount": "Net Tutar",
                "installment_count": "Taksit",
                "commission_rate": "Oran",
                "rate_expected": "Beklenen Oran",
                "commission_diff": "Fark",
                "rate_match": "Eşleşme"
            }
            
            display_df = df[available_cols].head(500).copy()
            display_df = display_df.rename(columns=col_names)
            
            st.dataframe(display_df, width="stretch", hide_index=True)
            
            if len(df) > 500:
                st.caption(f"İlk 500 satır gösteriliyor. Toplam: {len(df):,} işlem")
    
    def _render_export(self, df: pd.DataFrame):
        """Export butonu."""
        st.markdown("---")
        st.subheader("📥 Dışa Aktar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV İndir",
                data=csv,
                file_name=f"{self.bank_key}_detay_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=self.name, index=False)
            
            st.download_button(
                label="📥 Excel İndir",
                data=output.getvalue(),
                file_name=f"{self.bank_key}_detay_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def render_bank_page(bank_key: str):
    """Banka sayfası render yardımcı fonksiyonu."""
    page = BankDetailPage(bank_key)
    page.render()
