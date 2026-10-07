"""
UI components: landing page, login, and shared layout helpers.
"""

import streamlit as st

from authentication import navigate
from config import APP_TAGLINE, APP_TITLE


def render_landing_page() -> None:
    st.markdown(
        f"""
        <div class="hero-section">
            <div>
                <div class="secure-badge">🛡️ Bank-Grade Security Enabled</div>
                <h1 class="hero-title">{APP_TITLE}</h1>
                <p class="hero-subtitle">{APP_TAGLINE}. A secure academic demonstration
                platform featuring AES-256 encryption, SHA-256 hashing, KYC verification,
                and encrypted transaction-ready account management.</p>
            </div>
            <div class="hero-visual">
                <div style="text-align:center;padding:2rem;">
                    <div style="font-size:4rem;margin-bottom:1rem;">🏦</div>
                    <h3 style="color:#00d4aa;font-family:'Space Grotesk',sans-serif;">
                        Secure Online Transactions
                    </h3>
                    <p style="color:#8892b0;margin-top:0.5rem;">
                        End-to-end encrypted banking demo with virtual ATM card,
                        admin KYC portal, and cryptographic data protection.
                    </p>
                    <div style="display:flex;gap:1rem;justify-content:center;margin-top:1.5rem;">
                        <span style="background:rgba(0,212,170,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.8rem;">AES-256</span>
                        <span style="background:rgba(0,212,170,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.8rem;">SHA-256</span>
                        <span style="background:rgba(0,212,170,0.2);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.8rem;">KYC</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-header">
            <h2>Security Features</h2>
            <p>Enterprise-grade cryptographic protection for your academic banking demo</p>
        </div>

        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <h3>AES-256 Encryption</h3>
                <p>Sensitive data including PIN, PAN, and Aadhaar are encrypted using AES-256-GCM for reversible secure storage.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">#️⃣</div>
                <h3>SHA-256 Security</h3>
                <p>Passwords are hashed with SHA-256. Integrity hashes enable duplicate detection without exposing raw data.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔑</div>
                <h3>Secure Authentication</h3>
                <p>Role-based login for users and administrators with session management and account status verification.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📋</div>
                <h3>KYC Verification</h3>
                <p>Complete Know Your Customer workflow with admin approval, rejection tracking, and audit logging.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">💳</div>
                <h3>Secure Transactions</h3>
                <p>Virtual ATM card generation upon approval with encrypted account credentials and balance tracking.</p>
            </div>
        </div>

        <div class="stats-section">
            <div class="stat-card">
                <div class="stat-value">256</div>
                <div class="stat-label">Bit AES Encryption</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">SHA</div>
                <div class="stat-label">256 Hash Algorithm</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">KYC</div>
                <div class="stat-label">Verified Onboarding</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">24/7</div>
                <div class="stat-label">Secure Access Demo</div>
            </div>
        </div>

        <div class="security-section">
            <div>
                <h2 style="font-family:'Space Grotesk',sans-serif;margin-bottom:1rem;">Security Assurance</h2>
                <p style="color:#8892b0;line-height:1.7;">
                    This academic demonstration implements industry-standard cryptographic
                    practices. All sensitive fields are encrypted at rest, passwords are
                    never stored in plaintext, and every admin action is recorded in audit logs.
                </p>
            </div>
            <ul class="security-list">
                <li>AES-256-GCM encryption for PIN, PAN & Aadhaar</li>
                <li>SHA-256 password hashing with application salt</li>
                <li>Parameterized SQL queries prevent injection</li>
                <li>Admin KYC approval with full audit trail</li>
                <li>Account status gates before dashboard access</li>
                <li>Virtual demo card — not a real banking instrument</li>
            </ul>
        </div>

        <div class="site-footer">
            <p>{APP_TITLE} — Academic Capstone Project Demo</p>
            <p style="margin-top:0.5rem;font-size:0.8rem;">
                This is a local demonstration system. Not connected to any real banking or government services.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Get Started — Login", key="hero_login", use_container_width=True):
            navigate("login")


def render_login_page() -> None:
    st.markdown(
        """
        <div class="auth-container">
            <h2 class="auth-title">Welcome Back</h2>
            <p class="auth-subtitle">Sign in to access your secure account</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    from authentication import authenticate_user, set_flash

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Username and password are required.")
            else:
                success, message = authenticate_user(username, password)
                if success:
                    set_flash(message, "success")
                    st.rerun()
                else:
                    st.error(message)

    st.markdown(
        """
        <div class="auth-link">
            New user? <span>Create an Account below</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Create an Account", key="goto_register", use_container_width=True):
            navigate("register")


def render_admin_login_page() -> None:
    st.markdown(
        """
        <div class="auth-container">
            <h2 class="auth-title">Admin Portal</h2>
            <p class="auth-subtitle">Secure administrator access only</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    from authentication import authenticate_admin

    with st.form("admin_login_form"):
        username = st.text_input("Admin Username")
        password = st.text_input("Admin Password", type="password")
        submitted = st.form_submit_button("Admin Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Admin username and password are required.")
            else:
                success, message = authenticate_admin(username, password)
                if success:
                    st.rerun()
                else:
                    st.error(message)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("← Back to Home", key="admin_back_home"):
            navigate("home")
