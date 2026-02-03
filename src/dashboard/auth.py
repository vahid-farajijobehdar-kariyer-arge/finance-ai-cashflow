"""
Authentication Module for Cash Flow Dashboard.

Provides password protection for all pages.
"""

import os
import streamlit as st


def get_password() -> str:
    """Get password from secrets, environment, or fallback."""
    try:
        return st.secrets["passwords"]["dashboard_password"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("DASHBOARD_PASSWORD", "kariyer2026")


def check_password() -> bool:
    """Returns True if the user has entered the correct password.
    
    Must be called at the start of every page to enforce authentication.
    """
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state.get("password") == get_password():
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
    
    # Already authenticated
    if st.session_state.get("password_correct", False):
        return True
    
    # Show login form (page config should be set by the calling page)
    st.title("🔐 Cash Flow Dashboard")
    st.markdown("---")
    
    st.text_input(
        "Şifre / Password", 
        type="password", 
        on_change=password_entered, 
        key="password",
        placeholder="Şifrenizi girin..."
    )
    
    # Show error if password was incorrect
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Hatalı şifre / Incorrect password")
    
    st.markdown("---")
    st.caption("Kariyer.net Finans Ekibi © 2026")
    
    return False


def require_auth():
    """Decorator-style function to require authentication.
    
    Call at the top of main() in each page:
        if not require_auth():
            st.stop()
    """
    if not check_password():
        st.stop()
        return False
    return True
