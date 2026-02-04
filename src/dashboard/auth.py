"""
Kimlik Doğrulama Modülü - Kariyer.net Finans

Tüm sayfalar için şifre koruması sağlar.

© 2026 Kariyer.net Finans Ekibi
"""

import os
import streamlit as st


def get_password() -> str:
    """Şifreyi secrets, environment veya varsayılandan al."""
    try:
        return st.secrets["passwords"]["dashboard_password"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("DASHBOARD_PASSWORD", "kariyer2026")


def check_password() -> bool:
    """Kullanıcının doğru şifreyi girip girmediğini kontrol eder.
    
    Her sayfanın başında çağrılmalıdır.
    """
    
    def password_entered():
        """Girilen şifrenin doğruluğunu kontrol eder."""
        if st.session_state.get("password") == get_password():
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    # Zaten giriş yapılmış
    if st.session_state.get("password_correct", False):
        return True
    
    # Giriş formu
    st.title("🔐 POS Komisyon Takip Sistemi")
    st.markdown("**Kariyer.net Finans Ekibi**")
    st.markdown("---")
    
    st.text_input(
        "Şifre", 
        type="password", 
        key="password",
        placeholder="Şifrenizi girin..."
    )
    
    # Giriş butonu
    if st.button("🔑 Giriş Yap", type="primary", use_container_width=True):
        password_entered()
    
    # Hatalı şifre mesajı
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Hatalı şifre")
    
    st.markdown("---")
    st.caption("© 2026 Kariyer.net Finans Ekibi")
    
    return False


def require_auth():
    """Kimlik doğrulama gerektiren fonksiyon.
    
    Her sayfanın main() fonksiyonunda çağrılmalı:
        if not require_auth():
            st.stop()
    """
    if not check_password():
        st.stop()
        return False
    return True
