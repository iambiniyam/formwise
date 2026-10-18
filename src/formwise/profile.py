"""Private local profile and field-name matching."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

ALIASES: dict[str, tuple[str, ...]] = {
    "first_name": ("first name", "firstname", "given name", "givenname", "fname"),
    "middle_name": ("middle name", "middlename", "mname"),
    "last_name": ("last name", "lastname", "surname", "family name", "lname"),
    "full_name": ("full name", "fullname", "your name", "applicant name", "name"),
    "email": ("email", "e mail", "email address", "mail"),
    "phone": ("phone", "phone number", "mobile", "mobile number", "telephone", "tel", "cell"),
    "address_line1": ("address", "address line 1", "address1", "street", "street address", "mailing address"),
    "address_line2": ("address line 2", "address2", "apartment", "suite", "unit"),
    "city": ("city", "town", "municipality"),
    "state": ("state", "province", "region", "county"),
    "postal_code": ("zip", "zip code", "postal code", "postcode"),
    "country": ("country", "nation"),
    "date_of_birth": ("date of birth", "dob", "birth date", "birthdate", "birthday"),
}

ENVELOPE_VERSION = 1
PBKDF2_ITERATIONS = 390_000


class ProfileLocked(RuntimeError):
    """Raised when an encrypted profile needs a passphrase."""


def _derive(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    ).derive(password.encode("utf-8"))


def _encrypt(profile: dict[str, str], password: str) -> str:
    from cryptography.fernet import Fernet

    salt = os.urandom(16)
    key = base64.urlsafe_b64encode(_derive(password, salt))
    token = Fernet(key).encrypt(json.dumps(profile, ensure_ascii=False).encode("utf-8"))
    return json.dumps(
        {
            "formwise": ENVELOPE_VERSION,
            "kdf": "pbkdf2-sha256",
            "iterations": PBKDF2_ITERATIONS,
            "salt": base64.b64encode(salt).decode("ascii"),
            "token": token.decode("ascii"),
        }
    )


def _decrypt(payload: dict[str, object], password: str) -> dict[str, str]:
    from cryptography.fernet import Fernet, InvalidToken

    if payload.get("kdf") != "pbkdf2-sha256":
        raise ProfileLocked("unsupported profile encryption")
    try:
        salt = base64.b64decode(str(payload["salt"]))
        token = str(payload["token"]).encode("ascii")
        key = base64.urlsafe_b64encode(_derive(password, salt))
        data = json.loads(Fernet(key).decrypt(token))
    except (KeyError, ValueError, InvalidToken) as exc:
        raise ProfileLocked("wrong passphrase or damaged profile") from exc
    return {str(key): str(value) for key, value in data.items() if value is not None}


SAMPLE = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone": "+1 555 123 4567",
    "address_line1": "42 Main Street",
    "city": "Springfield",
    "state": "IL",
    "postal_code": "62704",
    "country": "United States",
    "date_of_birth": "1990-04-12",
}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _read(path: Path, password: str | None) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("formwise") == ENVELOPE_VERSION:
        if not password:
            raise ProfileLocked("profile is encrypted; pass a passphrase")
        return _decrypt(payload, password)
    return {str(key): str(value) for key, value in payload.items() if value is not None}


def load_profile(path: Path | str | None = None, password: str | None = None) -> dict[str, str]:
    path = Path(path) if path else None
    if path and path.exists():
        return _read(path, password)
    default = Path(os.getenv("FORMWISE_PROFILE", str(Path.home() / ".formwise" / "profile.json")))
    if default.exists():
        return _read(default, password)
    return dict(SAMPLE)


def save_profile(profile: dict[str, str], path: Path | str, password: str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _encrypt(profile, password) if password else json.dumps(profile, indent=2)
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o600)
    return path


def canonical_key(field_name: str) -> str | None:
    words = normalize(field_name)
    if not words:
        return None
    best: tuple[int, str] | None = None
    for key, aliases in ALIASES.items():
        for alias in (key.replace("_", " "), *aliases):
            alias_words = normalize(alias)
            if not alias_words:
                continue
            if re.search(rf"\b{re.escape(alias_words)}\b", words):
                score = len(alias_words.split())
                if best is None or score > best[0]:
                    best = (score, key)
    return best[1] if best else None


def value_for_field(field_name: str, profile: dict[str, str]) -> str:
    key = canonical_key(field_name)
    if key and key in profile:
        return profile[key]
    normalized = normalize(field_name)
    for profile_key, value in profile.items():
        if normalize(profile_key) == normalized:
            return value
    return ""


def is_encrypted(path: Path | str) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("formwise") == ENVELOPE_VERSION
