from typing import Optional
import secrets
import string


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure filename with random prefix."""
    # Extract file extension
    if "." in original_filename:
        name, ext = original_filename.rsplit(".", 1)
        ext = f".{ext}"
    else:
        name = original_filename
        ext = ""

    # Generate random prefix
    alphabet = string.ascii_letters + string.digits
    random_prefix = "".join(secrets.choice(alphabet) for _ in range(16))

    # Sanitize original name (remove special chars, keep alphanumeric and basic punctuation)
    safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")[:50]

    return f"{random_prefix}_{safe_name}{ext}"


def validate_file_type(filename: str, allowed_types: Optional[list] = None) -> bool:
    """Validate file type based on extension."""
    if allowed_types is None:
        allowed_types = [".pdf", ".txt", ".doc", ".docx", ".md"]

    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()
    return f".{ext}" in [t.lower() for t in allowed_types]
