"""
Input validation for KYC registration and authentication forms.
"""

import re
from datetime import date, datetime
from typing import Optional, Tuple

from config import PHOTO_ALLOWED_EXTENSIONS, PHOTO_MAX_SIZE_KB, PHOTO_MIN_SIZE_KB


def validate_required(value, field_name: str) -> Optional[str]:
    if value is None:
        return f"{field_name} is required."
    if isinstance(value, (date, datetime)):
        return None
    if isinstance(value, str) and value.strip() == "":
        return f"{field_name} is required."
    return None


def validate_gender(gender: str) -> Optional[str]:
    if not gender or gender.strip() == "":
        return "Gender is required."
    return None


def max_dob_date() -> date:
    """Latest allowed DOB — user must be at least 18 years old."""
    today = date.today()
    try:
        return date(today.year - 18, today.month, today.day)
    except ValueError:
        return date(today.year - 18, today.month, min(today.day, 28))


def validate_mobile(mobile: str) -> Optional[str]:
    mobile = mobile.strip()
    if not re.fullmatch(r"\d{10}", mobile):
        return "Mobile number must be exactly 10 digits."
    if mobile[0] not in "6789":
        return "Invalid Indian mobile number format."
    return None


def validate_aadhaar(aadhaar: str) -> Optional[str]:
    aadhaar = aadhaar.strip()
    if not re.fullmatch(r"\d{12}", aadhaar):
        return "Aadhaar number must be exactly 12 digits."
    return None


def validate_pan(pan: str) -> Optional[str]:
    pan = pan.strip().upper()
    if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
        return "Invalid PAN format. Example: ABCDE1234F"
    return None


def validate_pin(pin: str, confirm_pin: str) -> Optional[str]:
    if not re.fullmatch(r"\d{4}", pin):
        return "PIN must be exactly 4 digits."
    if pin != confirm_pin:
        return "PIN and Confirm PIN do not match."
    return None


def validate_password(password: str, confirm_password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character."
    if password != confirm_password:
        return "Password and Confirm Password do not match."
    return None


def validate_email(email: str) -> Optional[str]:
    email = email.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.fullmatch(pattern, email):
        return "Invalid email address."
    return None


def validate_pin_code(pin_code: str) -> Optional[str]:
    if not re.fullmatch(r"\d{6}", pin_code.strip()):
        return "PIN code must be exactly 6 digits."
    return None


def validate_dob(dob) -> Optional[str]:
    if isinstance(dob, datetime):
        dob = dob.date()
    elif isinstance(dob, str):
        try:
            dob = date.fromisoformat(dob.strip())
        except ValueError:
            return "Invalid date of birth."

    if not isinstance(dob, date):
        return "Invalid date of birth."

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        return "You must be at least 18 years old to register."
    if dob.year < 1950:
        return "Date of birth must be from 1950 onwards."
    return None


def validate_transaction_amount(amount) -> Optional[str]:
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return "Amount must be a valid number."
    if val <= 0:
        return "Amount must be greater than zero."
    if val > 10_000_000:
        return "Amount exceeds maximum allowed limit."
    return None


def validate_transaction_pin(pin: str) -> Optional[str]:
    if not re.fullmatch(r"\d{4}", str(pin).strip()):
        return "PIN must be exactly 4 digits."
    return None


def validate_photo(uploaded_file) -> Tuple[Optional[str], Optional[bytes]]:
    if uploaded_file is None:
        return "Profile photograph is required.", None

    filename = uploaded_file.name.lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in PHOTO_ALLOWED_EXTENSIONS:
        return "Photo must be JPG, JPEG, or PNG format.", None

    data = uploaded_file.getvalue()
    size_kb = len(data) / 1024
    if size_kb < PHOTO_MIN_SIZE_KB:
        return (
            f"Photo is too small. Minimum size is {PHOTO_MIN_SIZE_KB} KB "
            f"(uploaded: {size_kb:.1f} KB)."
        ), None
    if size_kb > PHOTO_MAX_SIZE_KB:
        return (
            f"Photo is too large. Maximum size is {PHOTO_MAX_SIZE_KB} KB "
            f"(uploaded: {size_kb:.1f} KB)."
        ), None

    return None, data


def validate_kyc_form(form_data: dict, uploaded_file) -> Tuple[list, Optional[bytes]]:
    errors = []

    required_fields = [
        ("full_name", "Full Name"),
        ("date_of_birth", "Date of Birth"),
        ("gender", "Gender"),
        ("mobile", "Mobile Number"),
        ("email", "Email"),
        ("address", "Address"),
        ("city", "City"),
        ("state", "State"),
        ("pin_code", "PIN Code"),
        ("aadhaar", "Aadhaar Number"),
        ("pan", "PAN Number"),
        ("username", "Username"),
        ("password", "Password"),
        ("confirm_password", "Confirm Password"),
        ("pin", "PIN"),
        ("confirm_pin", "Confirm PIN"),
    ]

    for key, label in required_fields:
        err = validate_required(form_data.get(key, ""), label)
        if err:
            errors.append(err)

    if errors:
        return errors, None

    for validator, key in [
        (validate_mobile, "mobile"),
        (validate_email, "email"),
        (validate_pin_code, "pin_code"),
        (validate_aadhaar, "aadhaar"),
        (validate_pan, "pan"),
    ]:
        err = validator(form_data[key])
        if err:
            errors.append(err)

    err = validate_password(form_data["password"], form_data["confirm_password"])
    if err:
        errors.append(err)

    err = validate_pin(form_data["pin"], form_data["confirm_pin"])
    if err:
        errors.append(err)

    err = validate_gender(form_data.get("gender", ""))
    if err:
        errors.append(err)

    if form_data.get("date_of_birth"):
        err = validate_dob(form_data["date_of_birth"])
        if err:
            errors.append(err)

    photo_err, photo_data = validate_photo(uploaded_file)
    if photo_err:
        errors.append(photo_err)

    return errors, photo_data
