"""
KYC registration form and confirmation page.
"""

from datetime import date

import streamlit as st

from authentication import navigate
from config import PHOTO_MAX_SIZE_KB, PHOTO_MIN_SIZE_KB
from database import register_user
from validation import max_dob_date, validate_kyc_form


def render_kyc_registration() -> None:
    st.markdown(
        """
        <div class="page-header compact">
            <h2 class="auth-title">Create Your Account</h2>
            <p class="auth-subtitle">Complete KYC verification to register (Demo — use test data only)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    min_dob = date(1950, 1, 1)
    max_dob = max_dob_date()

    with st.form("kyc_form"):
        st.markdown('<p class="section-label">Personal Information</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("Full Name *")
            dob = st.date_input(
                "Date of Birth *",
                value=max_dob,
                min_value=min_dob,
                max_value=max_dob,
                help=f"Must be at least 18 years old. Selectable range: 1950 to {max_dob.isoformat()}",
            )
            gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
            mobile = st.text_input("Mobile Number *", placeholder="10-digit Indian mobile")
        with c2:
            email = st.text_input("Email *")
            address = st.text_area("Address *", height=68)
            city = st.text_input("City *")
            state = st.text_input("State *")
            pin_code = st.text_input("PIN Code *", placeholder="6 digits")

        st.markdown('<p class="section-label">Identity Information</p>', unsafe_allow_html=True)
        ic1, ic2 = st.columns(2)
        with ic1:
            aadhaar = st.text_input("Aadhaar Number *", placeholder="12 digits")
        with ic2:
            pan = st.text_input("PAN Number *", placeholder="ABCDE1234F")

        st.markdown('<p class="section-label">Account Information</p>', unsafe_allow_html=True)
        ac1, ac2 = st.columns(2)
        with ac1:
            username = st.text_input("Username *")
            password = st.text_input("Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
        with ac2:
            pin = st.text_input("4-digit PIN *", type="password", max_chars=4)
            confirm_pin = st.text_input("Confirm PIN *", type="password", max_chars=4)

        st.markdown('<p class="section-label">Photograph</p>', unsafe_allow_html=True)
        st.caption(
            f"Upload passport-size photo (JPG/JPEG/PNG). "
            f"Size: {PHOTO_MIN_SIZE_KB} KB – {PHOTO_MAX_SIZE_KB} KB."
        )
        photo = st.file_uploader("Profile Photo *", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("Submit KYC Application", use_container_width=True)

        if submitted:
            form_data = {
                "full_name": full_name,
                "date_of_birth": dob,
                "gender": gender,
                "mobile": mobile,
                "email": email,
                "address": address,
                "city": city,
                "state": state,
                "pin_code": pin_code,
                "aadhaar": aadhaar,
                "pan": pan,
                "username": username,
                "password": password,
                "confirm_password": confirm_password,
                "pin": pin,
                "confirm_pin": confirm_pin,
            }

            errors, photo_data = validate_kyc_form(form_data, photo)
            if errors:
                for err in errors:
                    st.error(err)
            else:
                success, message = register_user(form_data, photo_data)
                if success:
                    st.session_state.kyc_submitted = True
                    st.session_state.page = "kyc_confirmation"
                    st.rerun()
                else:
                    st.error(message)

    if st.button("← Back to Login", key="kyc_back_login"):
        navigate("login")


def render_kyc_confirmation() -> None:
    st.markdown(
        """
        <div class="confirmation-box">
            <div style="font-size:3rem;margin-bottom:1rem;">✅</div>
            <h2>KYC Application Submitted Successfully</h2>
            <p style="color:#8892b0;margin-top:1rem;line-height:1.6;">
                Your registration has been received and is awaiting administrator verification.
                You will be able to access your dashboard once your account is approved.
            </p>
            <div class="status-badge">PENDING ADMIN VERIFICATION</div>
        </div>
        <div class="info-panel compact">
            <h4>What happens next?</h4>
            <ul class="security-list">
                <li>Admin reviews your KYC details in the Activations portal</li>
                <li>You receive account activation upon approval</li>
                <li>Login with your credentials to access banking services</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Return to Login", key="confirm_back_login", use_container_width=True):
        st.session_state.kyc_submitted = False
        navigate("login")
