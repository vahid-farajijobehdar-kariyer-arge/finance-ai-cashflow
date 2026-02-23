"""
🏦 İşbank Detay Sayfası

Türkiye İş Bankası için özelleştirilmiş komisyon analizi.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import sys
from pathlib import Path

# Proje yolunu ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from auth import check_password
from banks.base import render_bank_page

# Sayfa yapılandırması
st.set_page_config(
    page_title="İşbank Detay - POS Komisyon",
    page_icon="🏦",
    layout="wide"
)

# Kimlik doğrulama
if not check_password():
    st.stop()

# Sayfa render
render_bank_page("isbank")
