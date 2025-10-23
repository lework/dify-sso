import secrets
import string
from datetime import UTC, datetime
from typing import cast


def generate_string(n):
    letters_digits = string.ascii_letters + string.digits
    result = ""
    for i in range(n):
        result += secrets.choice(letters_digits)

    return result


def naive_utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def extract_remote_ip(request) -> str:
    if request.headers.get("Remoteip"):
        return cast(str, request.headers.get("Remoteip"))
    elif request.headers.getlist("X-Forwarded-For"):
        return cast(str, request.headers.getlist("X-Forwarded-For")[0])
    else:
        return cast(str, request.remote_addr)
