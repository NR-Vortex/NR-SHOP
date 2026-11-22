import re


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,19}$")


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(username.strip()))


def automatic_username(telegram_user_id: int) -> str:
    return f"u{telegram_user_id}"[:20]
