"""
Authentication helpers and session management for Streamlit.
"""

from typing import Tuple

import streamlit as st

from database import get_admin_by_username, get_user_by_username
from encryption import verify_password


def init_session_state() -> None:
    defaults = {
        "page": "home",
        "auth_role": None,
        "user_id": None,
        "username": None,
        "admin_id": None,
        "admin_section": "dashboard",
        "selected_kyc_id": None,
        "flash_message": None,
        "flash_type": "info",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate(page: str) -> None:
    st.session_state.page = page


def logout() -> None:
    st.session_state.auth_role = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.admin_id = None
    st.session_state.admin_section = "dashboard"
    st.session_state.selected_kyc_id = None
    st.session_state.page = "home"


def set_flash(message: str, flash_type: str = "info") -> None:
    st.session_state.flash_message = message
    st.session_state.flash_type = flash_type


def show_flash() -> None:
    if st.session_state.flash_message:
        css_class = st.session_state.flash_type
        st.markdown(
            f'<div class="flash-banner flash-{css_class}">{st.session_state.flash_message}</div>',
            unsafe_allow_html=True,
        )
        st.session_state.flash_message = None


def authenticate_user(username: str, password: str) -> Tuple[bool, str]:
    user = get_user_by_username(username)
    if not user:
        return False, "Invalid username or password."

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid username or password."

    if user["status"] == "PENDING":
        return False, "KYC verification is still pending."

    if user["status"] == "REJECTED":
        reason = user.get("rejection_reason") or "No reason provided."
        return False, f"Your account application has been rejected. Reason: {reason}"

    st.session_state.auth_role = "user"
    st.session_state.user_id = user["id"]
    st.session_state.username = user["username"]
    st.session_state.page = "user_dashboard"
    return True, "Login successful."


def authenticate_admin(username: str, password: str) -> Tuple[bool, str]:
    admin = get_admin_by_username(username)
    if not admin or not verify_password(password, admin["password_hash"]):
        return False, "Invalid admin credentials."

    st.session_state.auth_role = "admin"
    st.session_state.admin_id = admin["id"]
    st.session_state.username = admin["username"]
    st.session_state.page = "admin_dashboard"
    return True, "Admin login successful."
