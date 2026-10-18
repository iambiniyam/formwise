"""Private local profile and field-name matching."""

from __future__ import annotations

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


def load_profile(path: Path | str | None = None) -> dict[str, str]:
    path = Path(path) if path else None
    if path and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(key): str(value) for key, value in data.items() if value is not None}
    default = Path(os.getenv("FORMWISE_PROFILE", str(Path.home() / ".formwise" / "profile.json")))
    if default.exists():
        data = json.loads(default.read_text(encoding="utf-8"))
        return {str(key): str(value) for key, value in data.items() if value is not None}
    return dict(SAMPLE)


def save_profile(profile: dict[str, str], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
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
