"""
Admin dashboard, KYC activation, and user management pages.
"""

import base64
from datetime import datetime
from pathlib import Path

import streamlit as st

from authentication import logout, navigate
from database import (
    approve_user,
    get_all_complaints,
    get_all_transactions,
    get_audit_logs,
    get_complaint_stats,
    get_dashboard_stats,
    get_transaction_stats,
    get_user_by_id,
    get_users_by_status,
    reject_user,
    resolve_complaint,
)
from encryption import decrypt_data


def _mask_sensitive(value: str, visible: int = 4) -> str:
    if not value or len(value) <= visible:
        return value
    return "•" * (len(value) - visible) + value[-visible:]


def _photo_to_base64(photo_path: str) -> str:
    path = Path(photo_path)
    if path.exists():
        return base64.b64encode(path.read_bytes()).decode()
    return ""


def render_admin_dashboard() -> None:
    section = st.session_state.admin_section

    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">🔐 Admin Portal</div>',
            unsafe_allow_html=True,
        )
        sections = {
            "dashboard": "📊 Dashboard",
            "activations": "⏳ Activations",
            "approved": "✅ Approved Users",
            "rejected": "❌ Rejected Users",
            "history": "📜 Activation History",
            "transactions": "💳 Transactions",
            "complaints": "📋 Complaints",
        }
        for key, label in sections.items():
            if st.button(label, key=f"sidebar_{key}", use_container_width=True):
                st.session_state.admin_section = key
                st.session_state.selected_kyc_id = None
                st.rerun()

        st.markdown("---")
        if st.button("Logout", key="admin_logout", use_container_width=True):
            logout()
            st.rerun()

    if section == "dashboard":
        _render_admin_home()
    elif section == "activations":
        _render_activations()
    elif section == "approved":
        _render_approved_users()
    elif section == "rejected":
        _render_rejected_users()
    elif section == "history":
        _render_activation_history()
    elif section == "transactions":
        _render_transactions()
    elif section == "complaints":
        _render_complaints_admin()


def _render_admin_home() -> None:
    stats = get_dashboard_stats()
    st.markdown(
        """
        <div class="admin-header">
            <h1>Admin Dashboard</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Registered</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Pending KYC</div><div class="value">{stats['pending']}</div></div>
            <div class="dash-card"><div class="label">Approved Accounts</div><div class="value">{stats['approved']}</div></div>
            <div class="dash-card"><div class="label">Rejected Accounts</div><div class="value">{stats['rejected']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### Recent Registrations")
        if stats["recent"]:
            rows = ""
            for r in stats["recent"]:
                rows += f"""
                <tr>
                    <td>{r['full_name']}</td>
                    <td>{r['mobile']}</td>
                    <td>{r['email']}</td>
                    <td>{r['status']}</td>
                    <td>{r['created_at']}</td>
                </tr>
                """
            st.markdown(
                f"""
                <table class="data-table">
                    <thead><tr>
                        <th>Name</th><th>Mobile</th><th>Email</th><th>Status</th><th>Registered</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No registrations yet.")

    with col2:
        st.markdown("#### Security Overview")
        st.markdown(
            """
            <div class="info-card">
                <div class="card-label">Encryption</div>
                <div class="card-value" style="font-size:1rem;">AES-256-GCM Active</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="info-card" style="margin-top:1rem;">
                <div class="card-label">Password Security</div>
                <div class="card-value" style="font-size:1rem;">SHA-256 Hashing</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        logs = get_audit_logs(5)
        if logs:
            st.markdown("#### Recent Admin Actions")
            for log in logs:
                st.markdown(
                    f"<small style='color:#8892b0;'>{log['timestamp']} — "
                    f"{log['action']}: {log['details']}</small>",
                    unsafe_allow_html=True,
                )

    tx_stats = get_transaction_stats()
    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Transactions</div><div class="value">{tx_stats['total']}</div></div>
            <div class="dash-card"><div class="label">Total Deposits</div><div class="value">₹{tx_stats['deposits']:.0f}</div></div>
            <div class="dash-card"><div class="label">Total Withdrawals</div><div class="value">₹{tx_stats['withdrawals']:.0f}</div></div>
            <div class="dash-card"><div class="label">Transfer Operations</div><div class="value">{tx_stats['transfers']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_activations() -> None:
    if st.session_state.selected_kyc_id:
        _render_kyc_detail(st.session_state.selected_kyc_id)
        return

    st.markdown("<h1>Pending Activations</h1>", unsafe_allow_html=True)
    pending = get_users_by_status("PENDING")

    if not pending:
        st.info("No pending KYC applications.")
        return

    rows = ""
    for u in pending:
        rows += f"""
        <tr>
            <td>{u['full_name']}</td>
            <td>{u['mobile']}</td>
            <td>{u['email']}</td>
            <td>{u['created_at']}</td>
            <td><span class="status-pending">{u['status']}</span></td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Name</th><th>Mobile</th><th>Email</th><th>Registration Date</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_transactions() -> None:
    st.markdown("<h1>All Transactions</h1>", unsafe_allow_html=True)
    txs = get_all_transactions(200)
    stats = get_transaction_stats()

    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Records</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Deposits Volume</div><div class="value">₹{stats['deposits']:.0f}</div></div>
            <div class="dash-card"><div class="label">Withdrawals Volume</div><div class="value">₹{stats['withdrawals']:.0f}</div></div>
            <div class="dash-card"><div class="label">Transfers</div><div class="value">{stats['transfers']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        label = type_labels.get(t["transaction_type"], t["transaction_type"])
        rows += f"""
        <tr>
            <td>{t['created_at']}</td>
            <td>{t['full_name']}</td>
            <td>{t['account_number']}</td>
            <td>{label}</td>
            <td>₹{t['amount']:.2f}</td>
            <td>{t['status']}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Date/Time</th><th>User</th><th>Account</th><th>Type</th><th>Amount</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_complaints_admin() -> None:
    st.markdown("<h1>Complaint Management</h1>", unsafe_allow_html=True)
    stats = get_complaint_stats()
    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Complaints</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Open</div><div class="value">{stats['open']}</div></div>
            <div class="dash-card"><div class="label">Resolved</div><div class="value">{stats['resolved']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    complaints = get_all_complaints()
    if not complaints:
        st.info("No complaints submitted yet.")
        return

    for c in complaints:
        status_cls = "status-active" if c["status"] == "RESOLVED" else "status-pending"
        remarks_row = ""
        if c.get("admin_remarks"):
            remarks_row = f'<div class="detail-row"><span class="detail-label">Remarks</span><span>{c["admin_remarks"]}</span></div>'
        st.markdown(
            f"""
            <div class="info-card" style="margin-bottom:1rem;">
                <div class="detail-row"><span class="detail-label">ID</span><span>#{c['id']}</span></div>
                <div class="detail-row"><span class="detail-label">User</span><span>{c['full_name']} ({c['username']})</span></div>
                <div class="detail-row"><span class="detail-label">Subject</span><span>{c['subject']}</span></div>
                <div class="detail-row"><span class="detail-label">Description</span><span>{c['description']}</span></div>
                <div class="detail-row"><span class="detail-label">Status</span><span class="{status_cls}">{c['status']}</span></div>
                <div class="detail-row"><span class="detail-label">Submitted</span><span>{c['created_at']}</span></div>
                {remarks_row}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if c["status"] == "OPEN":
            remarks = st.text_area("Resolution Remarks", key=f"remarks_{c['id']}", height=80)
            if st.button(f"Mark Resolved — #{c['id']}", key=f"resolve_{c['id']}"):
                if not remarks.strip():
                    st.error("Resolution remarks are required.")
                elif resolve_complaint(c["id"], st.session_state.admin_id, remarks):
                    st.success("Complaint resolved.")
                    st.rerun()
                else:
                    st.error("Failed to resolve complaint.")

    st.markdown("#### Actions")
    for u in pending:
        if st.button(f"VIEW — {u['full_name']}", key=f"view_{u['id']}"):
            st.session_state.selected_kyc_id = u["id"]
            st.rerun()


def _render_kyc_detail(user_id: int) -> None:
    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found.")
        return

    pan = decrypt_data(user["pan_encrypted"])
    aadhaar = decrypt_data(user["aadhaar_encrypted"])
    photo_b64 = _photo_to_base64(user.get("photo_path", ""))
    photo_html = (
        f'<img class="kyc-photo" src="data:image/jpeg;base64,{photo_b64}" />'
        if photo_b64
        else '<div class="kyc-photo" style="display:flex;align-items:center;justify-content:center;background:#112240;">No Photo</div>'
    )

    st.markdown(
        f"""
        <div class="kyc-detail-grid">
            <div>{photo_html}</div>
            <div>
                <h3 style="color:#00d4aa;margin-bottom:1rem;">KYC Details — {user['full_name']}</h3>
                <div class="detail-row"><span class="detail-label">Full Name</span><span class="detail-value">{user['full_name']}</span></div>
                <div class="detail-row"><span class="detail-label">Date of Birth</span><span class="detail-value">{user['date_of_birth']}</span></div>
                <div class="detail-row"><span class="detail-label">Gender</span><span class="detail-value">{user['gender']}</span></div>
                <div class="detail-row"><span class="detail-label">Mobile</span><span class="detail-value">{user['mobile']}</span></div>
                <div class="detail-row"><span class="detail-label">Email</span><span class="detail-value">{user['email']}</span></div>
                <div class="detail-row"><span class="detail-label">Address</span><span class="detail-value">{user['address']}, {user['city']}, {user['state']} — {user['pin_code']}</span></div>
                <div class="detail-row"><span class="detail-label">PAN</span><span class="detail-value sensitive-mask">{_mask_sensitive(pan, 4)}</span></div>
                <div class="detail-row"><span class="detail-label">Aadhaar</span><span class="detail-value sensitive-mask">{_mask_sensitive(aadhaar, 4)}</span></div>
                <div class="detail-row"><span class="detail-label">Username</span><span class="detail-value">{user['username']}</span></div>
                <div class="detail-row"><span class="detail-label">Registered</span><span class="detail-value">{user['kyc_submitted_at']}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Back", key="kyc_detail_back"):
            st.session_state.selected_kyc_id = None
            st.rerun()
    with col2:
        if st.button("✅ APPROVE ACCOUNT", key="approve_btn", use_container_width=True):
            if approve_user(user_id, st.session_state.admin_id):
                st.success("Account approved successfully!")
                st.session_state.selected_kyc_id = None
                st.session_state.admin_section = "approved"
                st.rerun()
            else:
                st.error("Approval failed. User may no longer be pending.")
    with col3:
        if st.button("❌ REJECT ACCOUNT", key="reject_btn", use_container_width=True):
            st.session_state.show_reject_form = user_id

    if st.session_state.get("show_reject_form") == user_id:
        reason = st.text_area("Rejection Reason *", key="reject_reason")
        if st.button("Confirm Rejection", key="confirm_reject"):
            if not reason.strip():
                st.error("Rejection reason is required.")
            elif reject_user(user_id, st.session_state.admin_id, reason):
                st.warning("Account rejected.")
                st.session_state.selected_kyc_id = None
                st.session_state.show_reject_form = None
                st.session_state.admin_section = "rejected"
                st.rerun()
            else:
                st.error("Rejection failed.")


def _render_approved_users() -> None:
    st.markdown("<h1>Approved Users</h1>", unsafe_allow_html=True)
    approved = get_users_by_status("ACTIVE")

    if not approved:
        st.info("No approved users yet.")
        return

    rows = ""
    for u in approved:
        rows += f"""
        <tr>
            <td>{u['full_name']}</td>
            <td>{u['account_number']}</td>
            <td>{u['username']}</td>
            <td>{u['mobile']}</td>
            <td>{u['approved_at'] or u['created_at']}</td>
            <td><span class="status-active">{u['status']}</span></td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Name</th><th>Account No.</th><th>Username</th><th>Mobile</th>
                <th>Activation Date</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_transactions() -> None:
    st.markdown("<h1>All Transactions</h1>", unsafe_allow_html=True)
    txs = get_all_transactions(200)
    stats = get_transaction_stats()

    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Records</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Deposits Volume</div><div class="value">₹{stats['deposits']:.0f}</div></div>
            <div class="dash-card"><div class="label">Withdrawals Volume</div><div class="value">₹{stats['withdrawals']:.0f}</div></div>
            <div class="dash-card"><div class="label">Transfers</div><div class="value">{stats['transfers']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        label = type_labels.get(t["transaction_type"], t["transaction_type"])
        rows += f"""
        <tr>
            <td>{t['created_at']}</td>
            <td>{t['full_name']}</td>
            <td>{t['account_number']}</td>
            <td>{label}</td>
            <td>₹{t['amount']:.2f}</td>
            <td>{t['status']}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Date/Time</th><th>User</th><th>Account</th><th>Type</th><th>Amount</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_complaints_admin() -> None:
    st.markdown("<h1>Complaint Management</h1>", unsafe_allow_html=True)
    stats = get_complaint_stats()
    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Complaints</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Open</div><div class="value">{stats['open']}</div></div>
            <div class="dash-card"><div class="label">Resolved</div><div class="value">{stats['resolved']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    complaints = get_all_complaints()
    if not complaints:
        st.info("No complaints submitted yet.")
        return

    for c in complaints:
        status_cls = "status-active" if c["status"] == "RESOLVED" else "status-pending"
        remarks_row = ""
        if c.get("admin_remarks"):
            remarks_row = f'<div class="detail-row"><span class="detail-label">Remarks</span><span>{c["admin_remarks"]}</span></div>'
        st.markdown(
            f"""
            <div class="info-card" style="margin-bottom:1rem;">
                <div class="detail-row"><span class="detail-label">ID</span><span>#{c['id']}</span></div>
                <div class="detail-row"><span class="detail-label">User</span><span>{c['full_name']} ({c['username']})</span></div>
                <div class="detail-row"><span class="detail-label">Subject</span><span>{c['subject']}</span></div>
                <div class="detail-row"><span class="detail-label">Description</span><span>{c['description']}</span></div>
                <div class="detail-row"><span class="detail-label">Status</span><span class="{status_cls}">{c['status']}</span></div>
                <div class="detail-row"><span class="detail-label">Submitted</span><span>{c['created_at']}</span></div>
                {remarks_row}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if c["status"] == "OPEN":
            remarks = st.text_area("Resolution Remarks", key=f"remarks_{c['id']}", height=80)
            if st.button(f"Mark Resolved — #{c['id']}", key=f"resolve_{c['id']}"):
                if not remarks.strip():
                    st.error("Resolution remarks are required.")
                elif resolve_complaint(c["id"], st.session_state.admin_id, remarks):
                    st.success("Complaint resolved.")
                    st.rerun()
                else:
                    st.error("Failed to resolve complaint.")

    st.markdown("#### View Account Details")
    for u in approved:
        if st.button(f"View — {u['full_name']} ({u['account_number']})", key=f"view_approved_{u['id']}"):
            detail = get_user_by_id(u["id"])
            st.markdown(
                f"""
                <div class="info-card">
                    <div class="detail-row"><span class="detail-label">Name</span><span>{detail['full_name']}</span></div>
                    <div class="detail-row"><span class="detail-label">Account</span><span>{detail['account_number']}</span></div>
                    <div class="detail-row"><span class="detail-label">Balance</span><span>₹{detail['balance']:.2f}</span></div>
                    <div class="detail-row"><span class="detail-label">Card Expiry</span><span>{detail.get('card_expiry', 'N/A')}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_rejected_users() -> None:
    st.markdown("<h1>Rejected Users</h1>", unsafe_allow_html=True)
    rejected = get_users_by_status("REJECTED")

    if not rejected:
        st.info("No rejected users.")
        return

    rows = ""
    for u in rejected:
        rows += f"""
        <tr>
            <td>{u['full_name']}</td>
            <td>{u['created_at']}</td>
            <td>{u['rejection_reason'] or 'N/A'}</td>
            <td>{u['rejected_at'] or 'N/A'}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Name</th><th>Registration Date</th><th>Rejection Reason</th><th>Rejection Date</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_transactions() -> None:
    st.markdown("<h1>All Transactions</h1>", unsafe_allow_html=True)
    txs = get_all_transactions(200)
    stats = get_transaction_stats()

    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Records</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Deposits Volume</div><div class="value">₹{stats['deposits']:.0f}</div></div>
            <div class="dash-card"><div class="label">Withdrawals Volume</div><div class="value">₹{stats['withdrawals']:.0f}</div></div>
            <div class="dash-card"><div class="label">Transfers</div><div class="value">{stats['transfers']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        label = type_labels.get(t["transaction_type"], t["transaction_type"])
        rows += f"""
        <tr>
            <td>{t['created_at']}</td>
            <td>{t['full_name']}</td>
            <td>{t['account_number']}</td>
            <td>{label}</td>
            <td>₹{t['amount']:.2f}</td>
            <td>{t['status']}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Date/Time</th><th>User</th><th>Account</th><th>Type</th><th>Amount</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_complaints_admin() -> None:
    st.markdown("<h1>Complaint Management</h1>", unsafe_allow_html=True)
    stats = get_complaint_stats()
    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Complaints</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Open</div><div class="value">{stats['open']}</div></div>
            <div class="dash-card"><div class="label">Resolved</div><div class="value">{stats['resolved']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    complaints = get_all_complaints()
    if not complaints:
        st.info("No complaints submitted yet.")
        return

    for c in complaints:
        status_cls = "status-active" if c["status"] == "RESOLVED" else "status-pending"
        remarks_row = ""
        if c.get("admin_remarks"):
            remarks_row = f'<div class="detail-row"><span class="detail-label">Remarks</span><span>{c["admin_remarks"]}</span></div>'
        st.markdown(
            f"""
            <div class="info-card" style="margin-bottom:1rem;">
                <div class="detail-row"><span class="detail-label">ID</span><span>#{c['id']}</span></div>
                <div class="detail-row"><span class="detail-label">User</span><span>{c['full_name']} ({c['username']})</span></div>
                <div class="detail-row"><span class="detail-label">Subject</span><span>{c['subject']}</span></div>
                <div class="detail-row"><span class="detail-label">Description</span><span>{c['description']}</span></div>
                <div class="detail-row"><span class="detail-label">Status</span><span class="{status_cls}">{c['status']}</span></div>
                <div class="detail-row"><span class="detail-label">Submitted</span><span>{c['created_at']}</span></div>
                {remarks_row}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if c["status"] == "OPEN":
            remarks = st.text_area("Resolution Remarks", key=f"remarks_{c['id']}", height=80)
            if st.button(f"Mark Resolved — #{c['id']}", key=f"resolve_{c['id']}"):
                if not remarks.strip():
                    st.error("Resolution remarks are required.")
                elif resolve_complaint(c["id"], st.session_state.admin_id, remarks):
                    st.success("Complaint resolved.")
                    st.rerun()
                else:
                    st.error("Failed to resolve complaint.")


def _render_activation_history() -> None:
    st.markdown("<h1>Activation History</h1>", unsafe_allow_html=True)
    logs = get_audit_logs(50)

    if not logs:
        st.info("No audit logs yet.")
        return

    rows = ""
    for log in logs:
        rows += f"""
        <tr>
            <td>{log['timestamp']}</td>
            <td>{log['admin_username'] or 'System'}</td>
            <td>{log['action']}</td>
            <td>{log['details']}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Timestamp</th><th>Admin</th><th>Action</th><th>Details</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_transactions() -> None:
    st.markdown("<h1>All Transactions</h1>", unsafe_allow_html=True)
    txs = get_all_transactions(200)
    stats = get_transaction_stats()

    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Records</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Deposits Volume</div><div class="value">₹{stats['deposits']:.0f}</div></div>
            <div class="dash-card"><div class="label">Withdrawals Volume</div><div class="value">₹{stats['withdrawals']:.0f}</div></div>
            <div class="dash-card"><div class="label">Transfers</div><div class="value">{stats['transfers']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        label = type_labels.get(t["transaction_type"], t["transaction_type"])
        rows += f"""
        <tr>
            <td>{t['created_at']}</td>
            <td>{t['full_name']}</td>
            <td>{t['account_number']}</td>
            <td>{label}</td>
            <td>₹{t['amount']:.2f}</td>
            <td>{t['status']}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="data-table">
            <thead><tr>
                <th>Date/Time</th><th>User</th><th>Account</th><th>Type</th><th>Amount</th><th>Status</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_complaints_admin() -> None:
    st.markdown("<h1>Complaint Management</h1>", unsafe_allow_html=True)
    stats = get_complaint_stats()
    st.markdown(
        f"""
        <div class="dash-grid">
            <div class="dash-card"><div class="label">Total Complaints</div><div class="value">{stats['total']}</div></div>
            <div class="dash-card"><div class="label">Open</div><div class="value">{stats['open']}</div></div>
            <div class="dash-card"><div class="label">Resolved</div><div class="value">{stats['resolved']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    complaints = get_all_complaints()
    if not complaints:
        st.info("No complaints submitted yet.")
        return

    for c in complaints:
        status_cls = "status-active" if c["status"] == "RESOLVED" else "status-pending"
        remarks_row = ""
        if c.get("admin_remarks"):
            remarks_row = f'<div class="detail-row"><span class="detail-label">Remarks</span><span>{c["admin_remarks"]}</span></div>'
        st.markdown(
            f"""
            <div class="info-card" style="margin-bottom:1rem;">
                <div class="detail-row"><span class="detail-label">ID</span><span>#{c['id']}</span></div>
                <div class="detail-row"><span class="detail-label">User</span><span>{c['full_name']} ({c['username']})</span></div>
                <div class="detail-row"><span class="detail-label">Subject</span><span>{c['subject']}</span></div>
                <div class="detail-row"><span class="detail-label">Description</span><span>{c['description']}</span></div>
                <div class="detail-row"><span class="detail-label">Status</span><span class="{status_cls}">{c['status']}</span></div>
                <div class="detail-row"><span class="detail-label">Submitted</span><span>{c['created_at']}</span></div>
                {remarks_row}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if c["status"] == "OPEN":
            remarks = st.text_area("Resolution Remarks", key=f"remarks_{c['id']}", height=80)
            if st.button(f"Mark Resolved — #{c['id']}", key=f"resolve_{c['id']}"):
                if not remarks.strip():
                    st.error("Resolution remarks are required.")
                elif resolve_complaint(c["id"], st.session_state.admin_id, remarks):
                    st.success("Complaint resolved.")
                    st.rerun()
                else:
                    st.error("Failed to resolve complaint.")
