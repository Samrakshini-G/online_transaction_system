"""
User dashboard with Profile, Deposit, Withdrawal, Transfer, History, Complaints, Virtual Card.
"""

from datetime import datetime

import streamlit as st

from authentication import logout
from config import APP_TITLE, CURRENCY_SYMBOL
from database import (
    create_complaint,
    get_user_by_id,
    get_user_complaints,
    get_user_transactions,
    update_user_pin,
)
from encryption import decrypt_data
from notifications import render_pending_notification, set_notification
from transactions import lookup_recipient, process_deposit, process_transfer, process_withdrawal
from validation import validate_pin, validate_transaction_amount, validate_transaction_pin

USER_VIEWS = [
    ("dashboard", "📊 Dashboard"),
    ("profile", "👤 Profile"),
    ("deposit", "💰 Deposit"),
    ("withdrawal", "💸 Withdrawal"),
    ("transfer", "🔄 Transfer"),
    ("history", "📜 Transaction History"),
    ("complaints", "📋 Complaints"),
    ("card", "💳 Virtual Card"),
]


def _mask_account(account_number: str) -> str:
    if not account_number or len(account_number) < 8:
        return account_number or "****"
    return "**** **** " + account_number[-4:]


def _reset_txn_state(prefix: str) -> None:
    st.session_state[f"{prefix}_step"] = 1
    st.session_state[f"{prefix}_data"] = {}


def _set_view(view: str) -> None:
    st.session_state.user_view = view
    for prefix in ("deposit", "withdrawal", "transfer"):
        _reset_txn_state(prefix)
    st.rerun()


def render_user_dashboard() -> None:
    user = get_user_by_id(st.session_state.user_id)
    if not user:
        st.error("Unable to load user data.")
        return

    render_pending_notification()

    with st.sidebar:
        st.markdown('<div class="sidebar-brand">🏦 My Account</div>', unsafe_allow_html=True)
        st.markdown(f"**{user['full_name']}**")
        st.markdown(f"<small style='color:#8892b0;'>{user['username']}</small>", unsafe_allow_html=True)
        st.markdown(f"<small style='color:#00d4aa;'>Bal: {CURRENCY_SYMBOL}{user['balance']:.2f}</small>", unsafe_allow_html=True)
        st.markdown("---")
        for key, label in USER_VIEWS:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                _set_view(key)

        st.markdown("---")
        if st.button("Logout", key="user_logout", use_container_width=True):
            logout()
            st.rerun()

    view = st.session_state.get("user_view", "dashboard")
    renderers = {
        "dashboard": lambda: _render_main_dashboard(user),
        "profile": lambda: _render_profile(user),
        "deposit": lambda: _render_deposit(user),
        "withdrawal": lambda: _render_withdrawal(user),
        "transfer": lambda: _render_transfer(user),
        "history": lambda: _render_history(user),
        "complaints": lambda: _render_complaints(user),
        "card": lambda: _render_virtual_card(user),
    }
    renderers.get(view, renderers["dashboard"])()


def _render_main_dashboard(user: dict) -> None:
    now = datetime.now().strftime("%A, %d %B %Y — %I:%M %p")
    txs = get_user_transactions(user["id"], 5)

    st.markdown(
        f"""
        <div class="admin-header">
            <h1>Welcome, {user['full_name']}</h1>
            <span style="color:#8892b0;font-size:0.9rem;">{now}</span>
        </div>
        <div class="user-dash-grid">
            <div class="info-card"><div class="card-label">Account Status</div>
                <div class="card-value status-active">{user['status']}</div></div>
            <div class="info-card"><div class="card-label">Available Balance</div>
                <div class="card-value">{CURRENCY_SYMBOL}{user['balance']:.2f}</div></div>
            <div class="info-card"><div class="card-label">Account Number</div>
                <div class="card-value" style="font-size:1.1rem;">{user['account_number']}</div></div>
            <div class="info-card"><div class="card-label">Security</div>
                <div class="card-value" style="font-size:1rem;color:#00d4aa;">🔒 Encrypted & Verified</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Quick Actions")
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if st.button("Deposit", use_container_width=True):
                _set_view("deposit")
        with qc2:
            if st.button("Withdraw", use_container_width=True):
                _set_view("withdrawal")
        with qc3:
            if st.button("Transfer", use_container_width=True):
                _set_view("transfer")

        st.markdown("#### Recent Transactions")
        if txs:
            rows = ""
            for t in txs:
                rows += f"""<tr><td>{t['created_at']}</td><td>{t['transaction_type']}</td>
                <td>{CURRENCY_SYMBOL}{t['amount']:.2f}</td><td>{t['status']}</td></tr>"""
            st.markdown(
                f"""<table class="data-table"><thead><tr>
                <th>Date/Time</th><th>Type</th><th>Amount</th><th>Status</th>
                </tr></thead><tbody>{rows}</tbody></table>""",
                unsafe_allow_html=True,
            )
        else:
            st.info("No transactions yet. Use Deposit to add funds.")

    with col2:
        st.markdown("#### Account Summary")
        st.markdown(
            f"""
            <div class="info-card">
                <div class="detail-row"><span class="detail-label">Email</span><span>{user['email']}</span></div>
                <div class="detail-row"><span class="detail-label">Mobile</span><span>{user['mobile']}</span></div>
                <div class="detail-row"><span class="detail-label">Activated</span><span>{user.get('approved_at', 'N/A')}</span></div>
                <div class="detail-row"><span class="detail-label">KYC</span><span style="color:#00d4aa;">Verified ✓</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("View Virtual ATM Card 💳", use_container_width=True):
            _set_view("card")


def _render_profile(user: dict) -> None:
    st.markdown("<h1>My Profile</h1>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="info-card">
            <div class="detail-row"><span class="detail-label">Full Name</span><span>{user['full_name']}</span></div>
            <div class="detail-row"><span class="detail-label">Account Number</span><span>{user['account_number']}</span></div>
            <div class="detail-row"><span class="detail-label">Account Status</span><span class="status-active">{user['status']}</span></div>
            <div class="detail-row"><span class="detail-label">Registration Time</span><span>{user['created_at']}</span></div>
            <div class="detail-row"><span class="detail-label">Activation Time</span><span>{user.get('approved_at', 'N/A')}</span></div>
            <div class="detail-row"><span class="detail-label">Mobile Number</span><span>{user['mobile']}</span></div>
            <div class="detail-row"><span class="detail-label">Email Address</span><span>{user['email']}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### PIN Management")
    st.caption("Your PIN is stored using AES-256 encryption.")

    if st.session_state.get("show_pin"):
        pin_val = decrypt_data(user["pin_encrypted"])
        st.markdown(f'<div class="info-card"><strong>PIN:</strong> <span class="sensitive-mask">{pin_val}</span></div>', unsafe_allow_html=True)
        if st.button("Hide PIN"):
            st.session_state.show_pin = False
            st.rerun()
    else:
        if st.button("Show PIN"):
            st.session_state.show_pin = True
            st.rerun()

    with st.form("update_pin_form"):
        st.markdown("**Update PIN**")
        new_pin = st.text_input("New 4-digit PIN", type="password", max_chars=4)
        confirm_pin = st.text_input("Confirm New PIN", type="password", max_chars=4)
        if st.form_submit_button("Update PIN", use_container_width=True):
            err = validate_pin(new_pin, confirm_pin)
            if err:
                st.error(err)
            elif update_user_pin(user["id"], new_pin):
                set_notification("PIN updated successfully.", "success")
                st.session_state.show_pin = False
                st.rerun()
            else:
                st.error("Failed to update PIN.")


def _render_deposit(user: dict) -> None:
    st.markdown("<h1>Deposit Funds</h1>", unsafe_allow_html=True)
    step = st.session_state.get("deposit_step", 1)
    data = st.session_state.get("deposit_data", {})

    if step == 1:
        with st.form("deposit_form"):
            account = st.text_input("Account Number", value=user["account_number"])
            amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0, format="%.2f")
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.form_submit_button("Continue to Confirmation", use_container_width=True):
                amt_err = validate_transaction_amount(amount)
                pin_err = validate_transaction_pin(pin)
                if amt_err:
                    st.error(amt_err)
                elif pin_err:
                    st.error(pin_err)
                elif account.strip() != user["account_number"]:
                    st.error("Account number does not match your profile.")
                else:
                    st.session_state.deposit_data = {"account": account.strip(), "amount": float(amount), "pin": pin}
                    st.session_state.deposit_step = 2
                    st.rerun()
    else:
        st.markdown(
            f"""
            <div class="confirm-panel">
                <h3>Confirm Deposit</h3>
                <div class="detail-row"><span class="detail-label">Current Balance</span><span>{CURRENCY_SYMBOL}{user['balance']:.2f}</span></div>
                <div class="detail-row"><span class="detail-label">Deposit Amount</span><span style="color:#00d4aa;font-weight:700;">{CURRENCY_SYMBOL}{data['amount']:.2f}</span></div>
                <div class="detail-row"><span class="detail-label">New Balance</span><span>{CURRENCY_SYMBOL}{user['balance'] + data['amount']:.2f}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm Deposit", use_container_width=True):
                ok, msg = process_deposit(user["id"], data["account"], data["amount"], data["pin"])
                if ok:
                    set_notification("Deposit Successful! " + msg, "success")
                    _reset_txn_state("deposit")
                    st.rerun()
                else:
                    st.error(msg)
        with c2:
            if st.button("Cancel", use_container_width=True):
                _reset_txn_state("deposit")
                st.rerun()


def _render_withdrawal(user: dict) -> None:
    st.markdown("<h1>Withdraw Funds</h1>", unsafe_allow_html=True)
    step = st.session_state.get("withdrawal_step", 1)
    data = st.session_state.get("withdrawal_data", {})

    if step == 1:
        with st.form("withdrawal_form"):
            account = st.text_input("Account Number", value=user["account_number"])
            amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0, format="%.2f")
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.form_submit_button("Continue to Confirmation", use_container_width=True):
                amt_err = validate_transaction_amount(amount)
                pin_err = validate_transaction_pin(pin)
                if amt_err:
                    st.error(amt_err)
                elif pin_err:
                    st.error(pin_err)
                elif account.strip() != user["account_number"]:
                    st.error("Account number does not match your profile.")
                elif float(amount) > user["balance"]:
                    st.error("Insufficient balance.")
                else:
                    st.session_state.withdrawal_data = {"account": account.strip(), "amount": float(amount), "pin": pin}
                    st.session_state.withdrawal_step = 2
                    st.rerun()
    else:
        st.markdown(
            f"""
            <div class="confirm-panel">
                <h3>Confirm Withdrawal</h3>
                <div class="detail-row"><span class="detail-label">Account Number</span><span>{data['account']}</span></div>
                <div class="detail-row"><span class="detail-label">Available Balance</span><span>{CURRENCY_SYMBOL}{user['balance']:.2f}</span></div>
                <div class="detail-row"><span class="detail-label">Requested Amount</span><span style="color:#ffd93d;font-weight:700;">{CURRENCY_SYMBOL}{data['amount']:.2f}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm Withdrawal", use_container_width=True):
                ok, msg = process_withdrawal(user["id"], data["account"], data["amount"], data["pin"])
                if ok:
                    set_notification("Withdrawal Successful! " + msg, "success")
                    _reset_txn_state("withdrawal")
                    st.rerun()
                else:
                    st.error(msg)
        with c2:
            if st.button("Cancel", use_container_width=True):
                _reset_txn_state("withdrawal")
                st.rerun()


def _render_transfer(user: dict) -> None:
    st.markdown("<h1>Transfer Funds</h1>", unsafe_allow_html=True)
    step = st.session_state.get("transfer_step", 1)
    data = st.session_state.get("transfer_data", {})

    if step == 1:
        recipient_acct = st.text_input("Recipient Account Number", key="transfer_recipient_input")
        if recipient_acct.strip():
            recipient = lookup_recipient(recipient_acct.strip())
            if recipient:
                st.markdown(
                    f'<div class="info-card"><strong>Recipient:</strong> {recipient["full_name"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No active account found for this number.")

        if st.button("Continue", key="transfer_step1_continue"):
            if not recipient_acct.strip():
                st.error("Enter recipient account number.")
            elif recipient_acct.strip() == user["account_number"]:
                st.error("Cannot transfer to your own account.")
            elif not lookup_recipient(recipient_acct.strip()):
                st.error("Recipient account not found.")
            else:
                st.session_state.transfer_data = {"recipient_account": recipient_acct.strip()}
                st.session_state.transfer_step = 2
                st.rerun()

    elif step == 2:
        recipient = lookup_recipient(data["recipient_account"])
        st.markdown(f'**Recipient:** {recipient["full_name"]} ({data["recipient_account"]})')
        with st.form("transfer_amount_form"):
            amount = st.number_input("Transfer Amount (₹)", min_value=0.01, step=100.0, format="%.2f")
            pin = st.text_input("PIN", type="password", max_chars=4)
            if st.form_submit_button("Continue to Confirmation", use_container_width=True):
                amt_err = validate_transaction_amount(amount)
                pin_err = validate_transaction_pin(pin)
                if amt_err:
                    st.error(amt_err)
                elif pin_err:
                    st.error(pin_err)
                elif float(amount) > user["balance"]:
                    st.error("Insufficient balance.")
                else:
                    data["amount"] = float(amount)
                    data["pin"] = pin
                    data["recipient_name"] = recipient["full_name"]
                    st.session_state.transfer_data = data
                    st.session_state.transfer_step = 3
                    st.rerun()
        if st.button("← Back"):
            st.session_state.transfer_step = 1
            st.rerun()

    elif step == 3:
        st.markdown(
            f"""
            <div class="confirm-panel">
                <h3>Confirm Transfer</h3>
                <div class="detail-row"><span class="detail-label">Recipient Name</span><span>{data['recipient_name']}</span></div>
                <div class="detail-row"><span class="detail-label">Recipient Account</span><span>{data['recipient_account']}</span></div>
                <div class="detail-row"><span class="detail-label">Transfer Amount</span><span style="color:#00d4aa;font-weight:700;">{CURRENCY_SYMBOL}{data['amount']:.2f}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm Transfer", use_container_width=True):
                ok, msg = process_transfer(user["id"], data["recipient_account"], data["amount"], data["pin"])
                if ok:
                    set_notification("Transfer Successful! " + msg, "success")
                    _reset_txn_state("transfer")
                    st.rerun()
                else:
                    st.error(msg)
        with c2:
            if st.button("Cancel", use_container_width=True):
                _reset_txn_state("transfer")
                st.rerun()


def _render_history(user: dict) -> None:
    st.markdown("<h1>Transaction History</h1>", unsafe_allow_html=True)
    txs = get_user_transactions(user["id"], 100)
    if not txs:
        st.info("No transactions recorded yet.")
        return

    type_labels = {
        "DEPOSIT": "Deposit",
        "WITHDRAWAL": "Withdrawal",
        "TRANSFER_SENT": "Transfer Sent",
        "TRANSFER_RECEIVED": "Transfer Received",
    }
    rows = ""
    for t in txs:
        dt = t["created_at"]
        parts = dt.split(" ") if " " in dt else [dt, ""]
        date_part, time_part = parts[0], parts[1] if len(parts) > 1 else ""
        label = type_labels.get(t["transaction_type"], t["transaction_type"])
        rows += f"""<tr><td>{date_part}</td><td>{time_part}</td><td>{label}</td>
        <td>{CURRENCY_SYMBOL}{t['amount']:.2f}</td><td>{t['status']}</td></tr>"""

    st.markdown(
        f"""<table class="data-table"><thead><tr>
        <th>Date</th><th>Time</th><th>Transaction Type</th><th>Amount</th><th>Status</th>
        </tr></thead><tbody>{rows}</tbody></table>""",
        unsafe_allow_html=True,
    )


def _render_complaints(user: dict) -> None:
    st.markdown("<h1>Complaints</h1>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Raise Complaint", "Complaint History"])
    with tab1:
        with st.form("complaint_form"):
            subject = st.text_input("Subject *")
            description = st.text_area("Description *", height=120)
            if st.form_submit_button("Submit Complaint", use_container_width=True):
                if not subject.strip() or not description.strip():
                    st.error("Subject and description are required.")
                else:
                    create_complaint(user["id"], subject, description)
                    set_notification("Complaint Submitted successfully. We will review it shortly.", "info")
                    st.rerun()

    with tab2:
        complaints = get_user_complaints(user["id"])
        if not complaints:
            st.info("No complaints submitted yet.")
        else:
            rows = ""
            for c in complaints:
                status_cls = "status-active" if c["status"] == "RESOLVED" else "status-pending"
                rows += f"""<tr><td>{c['created_at']}</td><td>{c['subject']}</td>
                <td><span class="{status_cls}">{c['status']}</span></td>
                <td>{c.get('admin_remarks') or '—'}</td></tr>"""
            st.markdown(
                f"""<table class="data-table"><thead><tr>
                <th>Date</th><th>Subject</th><th>Status</th><th>Remarks</th>
                </tr></thead><tbody>{rows}</tbody></table>""",
                unsafe_allow_html=True,
            )


def _render_virtual_card(user: dict) -> None:
    expiry = user.get("card_expiry", "12/30")
    if expiry and len(expiry) == 10:
        parts = expiry.split("-")
        expiry = f"{parts[1]}/{parts[0][2:]}"

    masked = _mask_account(user.get("account_number", ""))
    st.markdown(
        f"""
        <div class="card-section">
            <h2 style="text-align:center;font-family:'Space Grotesk',sans-serif;margin-bottom:1.5rem;">Virtual ATM Card</h2>
            <div class="virtual-card">
                <div class="card-chip"></div>
                <div class="card-bank-name">{APP_TITLE}</div>
                <div class="card-number">{masked}</div>
                <div class="card-holder">{user['full_name'].upper()}</div>
                <div class="card-footer">
                    <div><div style="font-size:0.65rem;text-transform:uppercase;">Valid Thru</div>
                    <div style="color:#e6f1ff;font-weight:600;">{expiry}</div></div>
                    <div><div style="font-size:0.65rem;text-transform:uppercase;">Balance</div>
                    <div style="color:#00d4aa;font-weight:600;">{CURRENCY_SYMBOL}{user['balance']:.2f}</div></div>
                    <div style="font-size:1.2rem;">💳</div>
                </div>
            </div>
            <p class="card-demo-label">⚠️ DEMO CARD ONLY — Simulated virtual card for academic demonstration.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
