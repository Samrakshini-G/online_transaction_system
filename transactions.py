"""
Transaction processing: deposit, withdrawal, and transfer operations.
"""

from typing import Optional, Tuple

from database import (
    create_transaction,
    get_connection,
    get_user_by_account_number,
    get_user_by_id,
    verify_user_pin,
)


def process_deposit(user_id: int, account_number: str, amount: float, pin: str) -> Tuple[bool, str]:
    user = get_user_by_id(user_id)
    if not user:
        return False, "User account not found."
    if user["account_number"] != account_number.strip():
        return False, "Account number does not match your profile."
    if not verify_user_pin(user_id, pin):
        return False, "Incorrect PIN."

    new_balance = user["balance"] + amount
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )

    ref = f"DEP-{user_id}-{account_number[-4:]}"
    create_transaction(user_id, "DEPOSIT", amount, new_balance, reference=ref)
    return True, f"Deposit of ₹{amount:.2f} successful."


def process_withdrawal(user_id: int, account_number: str, amount: float, pin: str) -> Tuple[bool, str]:
    user = get_user_by_id(user_id)
    if not user:
        return False, "User account not found."
    if user["account_number"] != account_number.strip():
        return False, "Account number does not match your profile."
    if not verify_user_pin(user_id, pin):
        return False, "Incorrect PIN."
    if user["balance"] < amount:
        return False, "Insufficient balance."

    new_balance = user["balance"] - amount
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )

    create_transaction(user_id, "WITHDRAWAL", amount, new_balance, reference=f"WDR-{user_id}")
    return True, f"Withdrawal of ₹{amount:.2f} successful."


def lookup_recipient(account_number: str) -> Optional[dict]:
    return get_user_by_account_number(account_number)


def process_transfer(
    sender_id: int,
    recipient_account: str,
    amount: float,
    pin: str,
) -> Tuple[bool, str]:
    sender = get_user_by_id(sender_id)
    if not sender:
        return False, "Sender account not found."
    if sender["account_number"] == recipient_account.strip():
        return False, "Cannot transfer to your own account."
    if not verify_user_pin(sender_id, pin):
        return False, "Incorrect PIN."
    if sender["balance"] < amount:
        return False, "Insufficient balance."

    recipient = get_user_by_account_number(recipient_account)
    if not recipient:
        return False, "Recipient account not found."

    sender_balance = sender["balance"] - amount
    recipient_balance = recipient["balance"] + amount

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (sender_balance, sender_id))
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (recipient_balance, recipient["id"]))

    create_transaction(
        sender_id, "TRANSFER_SENT", amount, sender_balance,
        related_account=recipient["account_number"],
        related_user_name=recipient["full_name"],
        reference=f"TXN-SND-{sender_id}-{recipient['id']}",
    )
    create_transaction(
        recipient["id"], "TRANSFER_RECEIVED", amount, recipient_balance,
        related_account=sender["account_number"],
        related_user_name=sender["full_name"],
        reference=f"TXN-RCV-{recipient['id']}-{sender_id}",
    )
    return True, f"Transfer of ₹{amount:.2f} to {recipient['full_name']} successful."
