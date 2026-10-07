"""
SQLite database initialization and data access layer.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    CARD_VALIDITY_DAYS,
    DATABASE_DIR,
    DATABASE_PATH,
    INITIAL_BALANCE,
    UPLOADS_DIR,
)
from encryption import encrypt_data, hash_for_lookup, hash_password


def ensure_directories() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Create tables and seed default admin account."""
    ensure_directories()
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                pin_encrypted TEXT NOT NULL,
                account_number TEXT UNIQUE,
                balance REAL DEFAULT 0.0,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT,
                rejected_at TEXT,
                rejection_reason TEXT,
                card_expiry TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS kyc_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                gender TEXT NOT NULL,
                mobile TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                pin_code TEXT NOT NULL,
                aadhaar_encrypted TEXT NOT NULL,
                aadhaar_hash TEXT UNIQUE NOT NULL,
                pan_encrypted TEXT NOT NULL,
                pan_hash TEXT UNIQUE NOT NULL,
                photo_path TEXT,
                kyc_submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES admin(id),
                FOREIGN KEY (target_user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                related_account TEXT,
                related_user_name TEXT,
                status TEXT DEFAULT 'SUCCESS',
                reference_encrypted TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'OPEN',
                admin_remarks TEXT,
                resolved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            "SELECT id FROM admin WHERE username = ?",
            (ADMIN_USERNAME,),
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
                (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD)),
            )


def _generate_account_number() -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        while True:
            candidate = datetime.now().strftime("%Y%m%d") + str(
                int(datetime.now().timestamp() * 1000) % 100000
            ).zfill(5)
            cursor.execute(
                "SELECT id FROM users WHERE account_number = ?",
                (candidate,),
            )
            if cursor.fetchone() is None:
                return candidate


def check_duplicate(field: str, value: str) -> Optional[str]:
    """Return user-friendly duplicate error message if value exists."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if field == "username":
            cursor.execute("SELECT id FROM users WHERE username = ?", (value,))
            if cursor.fetchone():
                return "Registration failed: This username is already associated with an existing account."
        elif field == "mobile":
            cursor.execute("SELECT id FROM kyc_details WHERE mobile = ?", (value.strip(),))
            if cursor.fetchone():
                return "Registration failed: This mobile number is already associated with an existing account."
        elif field == "pan":
            pan_hash = hash_for_lookup(value)
            cursor.execute("SELECT id FROM kyc_details WHERE pan_hash = ?", (pan_hash,))
            if cursor.fetchone():
                return "Registration failed: This PAN is already associated with an existing account."
        elif field == "aadhaar":
            aadhaar_hash = hash_for_lookup(value)
            cursor.execute(
                "SELECT id FROM kyc_details WHERE aadhaar_hash = ?",
                (aadhaar_hash,),
            )
            if cursor.fetchone():
                return "Registration failed: This Aadhaar is already associated with an existing account."
    return None


def register_user(form_data: dict, photo_bytes: bytes) -> Tuple[bool, str]:
    dup_checks = [
        ("username", form_data["username"]),
        ("mobile", form_data["mobile"]),
        ("pan", form_data["pan"]),
        ("aadhaar", form_data["aadhaar"]),
    ]
    for field, value in dup_checks:
        err = check_duplicate(field, value)
        if err:
            return False, err

    username = form_data["username"].strip()
    photo_filename = f"{username}_{int(datetime.now().timestamp())}.jpg"
    photo_path = UPLOADS_DIR / photo_filename
    photo_path.write_bytes(photo_bytes)

    now = datetime.now().isoformat(sep=" ", timespec="seconds")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, pin_encrypted, status, created_at)
            VALUES (?, ?, ?, 'PENDING', ?)
            """,
            (
                username,
                hash_password(form_data["password"]),
                encrypt_data(form_data["pin"]),
                now,
            ),
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO kyc_details (
                user_id, full_name, date_of_birth, gender, mobile, email,
                address, city, state, pin_code,
                aadhaar_encrypted, aadhaar_hash,
                pan_encrypted, pan_hash,
                photo_path, kyc_submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                form_data["full_name"].strip(),
                form_data["date_of_birth"].isoformat(),
                form_data["gender"],
                form_data["mobile"].strip(),
                form_data["email"].strip(),
                form_data["address"].strip(),
                form_data["city"].strip(),
                form_data["state"].strip(),
                form_data["pin_code"].strip(),
                encrypt_data(form_data["aadhaar"].strip()),
                hash_for_lookup(form_data["aadhaar"]),
                encrypt_data(form_data["pan"].strip().upper()),
                hash_for_lookup(form_data["pan"]),
                str(photo_path),
                now,
            ),
        )

    return True, "KYC Application Submitted Successfully"


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.*, k.full_name, k.mobile, k.email
            FROM users u
            LEFT JOIN kyc_details k ON u.id = k.user_id
            WHERE u.username = ?
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.*, k.*
            FROM users u
            JOIN kyc_details k ON u.id = k.user_id
            WHERE u.id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_admin_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_dashboard_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        stats = {}
        for status, key in [
            (None, "total"),
            ("PENDING", "pending"),
            ("ACTIVE", "approved"),
            ("REJECTED", "rejected"),
        ]:
            if status:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM users WHERE status = ?",
                    (status,),
                )
            else:
                cursor.execute("SELECT COUNT(*) as cnt FROM users")
            stats[key] = cursor.fetchone()["cnt"]

        cursor.execute(
            """
            SELECT k.full_name, k.mobile, k.email, u.status, u.created_at
            FROM users u
            JOIN kyc_details k ON u.id = k.user_id
            ORDER BY u.created_at DESC
            LIMIT 8
            """
        )
        stats["recent"] = [dict(r) for r in cursor.fetchall()]
        return stats


def get_users_by_status(status: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.username, u.account_number, u.status, u.created_at,
                   u.approved_at, u.rejected_at, u.rejection_reason,
                   k.full_name, k.mobile, k.email, k.kyc_submitted_at
            FROM users u
            JOIN kyc_details k ON u.id = k.user_id
            WHERE u.status = ?
            ORDER BY u.created_at DESC
            """,
            (status,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_all_users_summary() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.username, u.account_number, u.status, u.created_at,
                   u.approved_at, u.rejected_at, u.rejection_reason,
                   k.full_name, k.mobile, k.email
            FROM users u
            JOIN kyc_details k ON u.id = k.user_id
            ORDER BY u.created_at DESC
            """
        )
        return [dict(r) for r in cursor.fetchall()]


def approve_user(user_id: int, admin_id: int) -> bool:
    account_number = _generate_account_number()
    now = datetime.now()
    expiry = (now + timedelta(days=CARD_VALIDITY_DAYS)).date().isoformat()
    approved_at = now.isoformat(sep=" ", timespec="seconds")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET status = 'ACTIVE', account_number = ?, approved_at = ?,
                card_expiry = ?, balance = ?
            WHERE id = ? AND status = 'PENDING'
            """,
            (account_number, approved_at, expiry, INITIAL_BALANCE, user_id),
        )
        if cursor.rowcount == 0:
            return False

        cursor.execute(
            """
            INSERT INTO audit_logs (admin_id, action, target_user_id, details)
            VALUES (?, 'APPROVE_ACCOUNT', ?, ?)
            """,
            (admin_id, user_id, f"Account approved. Account No: {account_number}"),
        )
    return True


def reject_user(user_id: int, admin_id: int, reason: str) -> bool:
    rejected_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET status = 'REJECTED', rejected_at = ?, rejection_reason = ?
            WHERE id = ? AND status = 'PENDING'
            """,
            (rejected_at, reason.strip(), user_id),
        )
        if cursor.rowcount == 0:
            return False

        cursor.execute(
            """
            INSERT INTO audit_logs (admin_id, action, target_user_id, details)
            VALUES (?, 'REJECT_ACCOUNT', ?, ?)
            """,
            (admin_id, user_id, f"Account rejected. Reason: {reason.strip()}"),
        )
    return True


def get_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.action, a.details, a.timestamp, ad.username as admin_username
            FROM audit_logs a
            LEFT JOIN admin ad ON a.admin_id = ad.id
            ORDER BY a.timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_user_by_account_number(account_number: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.*, k.full_name, k.mobile, k.email
            FROM users u
            JOIN kyc_details k ON u.id = k.user_id
            WHERE u.account_number = ? AND u.status = 'ACTIVE'
            """,
            (account_number.strip(),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def verify_user_pin(user_id: int, pin: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pin_encrypted FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
    from encryption import decrypt_data
    return decrypt_data(row["pin_encrypted"]) == pin.strip()


def update_user_pin(user_id: int, new_pin: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET pin_encrypted = ? WHERE id = ?",
            (encrypt_data(new_pin), user_id),
        )
        return cursor.rowcount > 0


def create_transaction(
    user_id: int,
    tx_type: str,
    amount: float,
    balance_after: float,
    related_account: str = "",
    related_user_name: str = "",
    reference: str = "",
) -> int:
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    ref_enc = encrypt_data(reference) if reference else ""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (
                user_id, transaction_type, amount, balance_after,
                related_account, related_user_name, status, reference_encrypted, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'SUCCESS', ?, ?)
            """,
            (user_id, tx_type, amount, balance_after, related_account, related_user_name, ref_enc, now),
        )
        return cursor.lastrowid


def get_user_transactions(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, transaction_type, amount, balance_after,
                   related_account, related_user_name, status, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_all_transactions(limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.*, k.full_name, u.account_number, u.username
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN kyc_details k ON u.id = k.user_id
            ORDER BY t.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_transaction_stats() -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM transactions")
        total = cursor.fetchone()["cnt"]
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE transaction_type = 'DEPOSIT'"
        )
        deposits = cursor.fetchone()["total"]
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE transaction_type = 'WITHDRAWAL'"
        )
        withdrawals = cursor.fetchone()["total"]
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE transaction_type LIKE 'TRANSFER%'"
        )
        transfers = cursor.fetchone()["cnt"]
        return {"total": total, "deposits": deposits, "withdrawals": withdrawals, "transfers": transfers}


def create_complaint(user_id: int, subject: str, description: str) -> int:
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO complaints (user_id, subject, description, status, created_at)
            VALUES (?, ?, ?, 'OPEN', ?)
            """,
            (user_id, subject.strip(), description.strip(), now),
        )
        return cursor.lastrowid


def get_user_complaints(user_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_all_complaints() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*, k.full_name, u.username, u.account_number
            FROM complaints c
            JOIN users u ON c.user_id = u.id
            JOIN kyc_details k ON u.id = k.user_id
            ORDER BY c.created_at DESC
            """
        )
        return [dict(r) for r in cursor.fetchall()]


def resolve_complaint(complaint_id: int, admin_id: int, remarks: str) -> bool:
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE complaints
            SET status = 'RESOLVED', admin_remarks = ?, resolved_at = ?
            WHERE id = ? AND status = 'OPEN'
            """,
            (remarks.strip(), now, complaint_id),
        )
        if cursor.rowcount == 0:
            return False
        cursor.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                INSERT INTO audit_logs (admin_id, action, target_user_id, details)
                VALUES (?, 'RESOLVE_COMPLAINT', ?, ?)
                """,
                (admin_id, row["user_id"], f"Complaint #{complaint_id} resolved. {remarks.strip()}"),
            )
    return True


def get_complaint_stats() -> Dict[str, int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        stats = {}
        for status, key in [(None, "total"), ("OPEN", "open"), ("RESOLVED", "resolved")]:
            if status:
                cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT COUNT(*) as cnt FROM complaints")
            stats[key] = cursor.fetchone()["cnt"]
        return stats
