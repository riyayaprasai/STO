import secrets
import string

_CHARS = string.ascii_lowercase + string.digits


def generate_article_id() -> str:
    """Return a compact unique article ID, e.g. ``art_k3xm9vp2qr4t``."""
    suffix = "".join(secrets.choice(_CHARS) for _ in range(12))
    return f"art_{suffix}"
