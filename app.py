"""
Online Transaction System with Cryptography — Stage 1
Main Streamlit application entry point.
"""

import streamlit as st

from admin import render_admin_dashboard
from authentication import init_session_state, navigate, show_flash
from config import APP_TITLE, STYLES_PATH
from database import init_database
from kyc import render_kyc_confirmation, render_kyc_registration
from ui_components import render_admin_login_page, render_landing_page, render_login_page
from user_dashboard import render_user_dashboard


def load_css() -> None:
    css = STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    init_database()
    init_session_state()
    load_css()
    show_flash()

    page = st.session_state.page

    if st.session_state.auth_role == "admin" and page != "admin_login":
        render_admin_dashboard()
        return

    if st.session_state.auth_role == "user" and page == "user_dashboard":
        render_user_dashboard()
        return

    if page in ("home", "login", "register", "kyc_confirmation", "admin_login"):
        _render_top_nav()

    pages = {
        "home": render_landing_page,
        "login": render_login_page,
        "register": render_kyc_registration,
        "kyc_confirmation": render_kyc_confirmation,
        "admin_login": render_admin_login_page,
    }

    renderer = pages.get(page, render_landing_page)
    renderer()


def _render_top_nav() -> None:
    st.markdown(
        f"""
        <div class="nav-bar">
            <div class="nav-brand">🔐 {APP_TITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
    with c2:
        if st.button("Home", key="top_home", use_container_width=True):
            navigate("home")
    with c3:
        if st.button("Services", key="top_services", use_container_width=True):
            navigate("home")
    with c4:
        if st.button("Login", key="top_login", use_container_width=True):
            navigate("login")
    with c5:
        if st.button("Admin", key="top_admin", use_container_width=True):
            navigate("admin_login")


if __name__ == "__main__":
    main()
