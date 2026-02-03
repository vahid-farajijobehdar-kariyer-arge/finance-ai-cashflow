"""
💰 Gelecek Değer Hesaplayıcı

Banka faiz oranları ile mevduat gelecek değerini hesaplayın.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from processing.future_value import FutureValueCalculator, DEPOSIT_RATES
from storage.metadata import MetadataManager

# Import auth module
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password


def init_calculator():
    """Initialize future value calculator."""
    if "fv_calculator" not in st.session_state:
        st.session_state.fv_calculator = FutureValueCalculator()
    return st.session_state.fv_calculator


def render_single_deposit(calculator: FutureValueCalculator):
    """Render single deposit future value calculator."""
    st.subheader("💵 Tek Seferlik Yatırım")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        principal = st.number_input(
            "Anapara (₺)",
            min_value=0.0,
            value=100000.0,
            step=10000.0,
            format="%.2f"
        )
    
    with col2:
        banks = calculator.get_all_banks()
        selected_bank = st.selectbox("Banka", banks)
    
    with col3:
        available_rates = calculator.get_rates_for_bank(selected_bank)
        terms = sorted(set(r.term_months for r in available_rates))
        term_months = st.selectbox("Vade (Ay)", terms if terms else [3, 6, 12])
    
    # Get rate for selected bank and term
    rate = None
    for r in available_rates:
        if r.term_months == term_months:
            rate = r.rate_annual
            break
    
    if rate is None:
        rate = 0.40  # Default
    
    st.markdown(f"**Yıllık Faiz Oranı:** %{rate*100:.1f}")
    
    # Calculate
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Basit Faiz")
        simple_result = calculator.calculate_simple_interest(principal, rate, term_months)
        
        st.metric("Gelecek Değer", f"₺{simple_result['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{simple_result['interest_earned']:,.2f}")
        st.metric("Efektif Oran", f"%{simple_result['effective_rate']*100:.2f}")
    
    with col2:
        st.markdown("#### Bileşik Faiz")
        compound_result = calculator.calculate_compound_interest(principal, rate, term_months)
        
        st.metric("Gelecek Değer", f"₺{compound_result['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{compound_result['interest_earned']:,.2f}")
        st.metric("Efektif Oran", f"%{compound_result['effective_rate']*100:.2f}")
    
    # Comparison chart
    st.markdown("---")
    st.markdown("#### 📊 Banka Karşılaştırması")
    
    best_options = calculator.calculate_best_option(principal, term_months)[:10]
    
    if best_options:
        df = pd.DataFrame(best_options)
        
        fig = px.bar(
            df,
            x="bank_name",
            y="total_interest",
            color="annual_rate",
            title=f"En İyi Mevduat Seçenekleri ({term_months} Ay)",
            labels={"total_interest": "Faiz Geliri (₺)", "bank_name": "Banka"},
            color_continuous_scale="Greens",
            text_auto=".2s"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, key="bank_comparison")
        
        # Table
        st.dataframe(
            df[["bank_name", "term_months", "annual_rate", "future_value", "total_interest"]].style.format({
                "annual_rate": "{:.1%}",
                "future_value": "₺{:,.2f}",
                "total_interest": "₺{:,.2f}"
            }),
            hide_index=True
        )


def render_monthly_projection(calculator: FutureValueCalculator):
    """Render monthly cash flow projection."""
    st.subheader("📅 Aylık Nakit Akışı Projeksiyonu")
    
    st.markdown("""
    Aylık net tutarları yatırıma dönüştürürseniz ne kadar kazanabilirsiniz?
    """)
    
    # Input monthly amounts
    col1, col2 = st.columns(2)
    
    with col1:
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        
        st.markdown("**Aylık Net Tutarlar:**")
        monthly_amounts = []
        
        # Default values (sample)
        defaults = [50000, 55000, 60000, 58000, 62000, 65000, 
                   70000, 68000, 72000, 75000, 80000, 85000]
        
        for i, month in enumerate(months):
            amount = st.number_input(
                month, 
                min_value=0.0, 
                value=float(defaults[i]), 
                step=1000.0,
                key=f"month_{i}"
            )
            monthly_amounts.append((month, amount))
    
    with col2:
        annual_rate = st.slider(
            "Yıllık Faiz Oranı",
            min_value=0.20,
            max_value=0.60,
            value=0.40,
            step=0.01,
            format="%.0f%%"
        )
        
        projection_months = st.slider(
            "Projeksiyon Süresi (Ay)",
            min_value=6,
            max_value=36,
            value=12,
            step=3
        )
        
        # Calculate projection
        result = calculator.project_monthly_deposits(
            monthly_amounts, 
            annual_rate, 
            projection_months
        )
        
        st.markdown("---")
        st.markdown("### 📊 Projeksiyon Sonuçları")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Anapara", f"₺{result['total_principal']:,.2f}")
        c2.metric("Gelecek Değer", f"₺{result['total_future_value']:,.2f}")
        c3.metric("Toplam Faiz", f"₺{result['total_interest']:,.2f}", 
                  delta=f"+{result['total_interest']/result['total_principal']*100:.1f}%")
    
    # Chart
    if result["projections"]:
        proj_df = pd.DataFrame(result["projections"])
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=proj_df["month"],
            y=proj_df["deposit_amount"],
            name="Anapara",
            marker_color="steelblue"
        ))
        
        fig.add_trace(go.Bar(
            x=proj_df["month"],
            y=proj_df["interest_earned"],
            name="Faiz Geliri",
            marker_color="green"
        ))
        
        fig.update_layout(
            title="Aylık Yatırım ve Faiz Geliri",
            xaxis_title="Ay",
            yaxis_title="Tutar (₺)",
            barmode="stack"
        )
        
        st.plotly_chart(fig, key="monthly_projection")


def render_rates_table(calculator: FutureValueCalculator):
    """Render deposit rates table."""
    st.subheader("📋 Mevduat Faiz Oranları")
    
    st.markdown("""
    **Not:** Bu oranlar yaklaşık değerlerdir ve güncel olmayabilir.
    """)
    
    # Create rates DataFrame
    data = []
    for rate in DEPOSIT_RATES:
        data.append({
            "Banka": rate.bank_name,
            "Vade (Ay)": rate.term_months,
            "Yıllık Oran": rate.rate_annual,
        })
    
    df = pd.DataFrame(data)
    
    # Pivot table
    pivot = df.pivot(index="Banka", columns="Vade (Ay)", values="Yıllık Oran")
    
    # Heatmap
    fig = px.imshow(
        pivot.values * 100,
        x=[f"{c} Ay" for c in pivot.columns],
        y=pivot.index.tolist(),
        title="Mevduat Faiz Oranları (%)",
        labels=dict(x="Vade", y="Banka", color="Oran (%)"),
        color_continuous_scale="Greens",
        text_auto=".1f",
        aspect="auto"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, key="rates_heatmap")
    
    # Table
    st.dataframe(
        pivot.style.format("{:.1%}"),
        height=350
    )


def render_file_projection(calculator: FutureValueCalculator):
    """Render projection for uploaded files."""
    st.subheader("📁 Dosya Bazlı Projeksiyon")
    
    # Initialize metadata manager
    if "metadata_manager" not in st.session_state:
        st.session_state.metadata_manager = MetadataManager()
    
    metadata_manager = st.session_state.metadata_manager
    files = metadata_manager.get_all_files()
    
    if not files:
        st.info("Henüz dosya yüklenmedi. Önce '📤 Dosya Yükle' sayfasından dosya yükleyin.")
        return
    
    # Select file
    file_options = {f"{f.original_name} ({f.file_id})": f for f in files}
    selected_key = st.selectbox("Dosya Seçin", list(file_options.keys()))
    
    if selected_key:
        file = file_options[selected_key]
        
        st.markdown(f"""
        **Dosya:** {file.original_name}  
        **Toplam Tutar:** ₺{file.total_amount:,.2f}  
        **Toplam Komisyon:** ₺{file.total_commission:,.2f}  
        **Net Tutar:** ₺{file.total_amount - file.total_commission:,.2f}
        """)
        
        # Calculate projection on net amount
        net_amount = file.total_amount - file.total_commission
        
        col1, col2 = st.columns(2)
        
        with col1:
            rate = st.slider("Yıllık Oran", 0.20, 0.60, 0.40, 0.01, format="%.0f%%", key="file_rate")
        with col2:
            months = st.slider("Vade (Ay)", 3, 36, 12, 3, key="file_months")
        
        result = calculator.calculate_compound_interest(net_amount, rate, months)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Tutar (Anapara)", f"₺{result['principal']:,.2f}")
        c2.metric("Gelecek Değer", f"₺{result['future_value']:,.2f}")
        c3.metric("Faiz Geliri", f"₺{result['interest_earned']:,.2f}")
        
        # Save projection to metadata
        if st.button("💾 Projeksiyonu Kaydet"):
            metadata_manager.update_file(file.file_id, future_value={
                "principal": result["principal"],
                "future_value": result["future_value"],
                "interest_earned": result["interest_earned"],
                "annual_rate": rate,
                "months": months,
                "calculated_at": pd.Timestamp.now().isoformat()
            })
            st.success("✅ Projeksiyon kaydedildi")


def main():
    st.set_page_config(
        page_title="Gelecek Değer - Nakit Akış Paneli",
        page_icon="💰",
        layout="wide"
    )
    
    # Require authentication
    if not check_password():
        return
    
    st.title("💰 Gelecek Değer Hesaplayıcı")
    st.markdown("---")
    
    calculator = init_calculator()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "💵 Tek Yatırım",
        "📅 Aylık Projeksiyon", 
        "📋 Faiz Oranları",
        "📁 Dosya Projeksiyonu"
    ])
    
    with tab1:
        render_single_deposit(calculator)
    
    with tab2:
        render_monthly_projection(calculator)
    
    with tab3:
        render_rates_table(calculator)
    
    with tab4:
        render_file_projection(calculator)


if __name__ == "__main__":
    main()
