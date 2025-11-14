"""
Utility functions for comfyui-save-file-extended.
"""
import os


def sanitize_filename(filename: str) -> str | None:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized basename or None if invalid/empty.

    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        'passwd'
        >>> sanitize_filename("..\\windows\\system32")
        'system32'
        >>> sanitize_filename("")
        None
        >>> sanitize_filename(".")
        None
        >>> sanitize_filename("..")
        None
    """
    if not filename:
        return None

    # Strip whitespace
    cleaned = filename.strip()
    if not cleaned:
        return None

    # Get basename to remove any directory components
    basename = os.path.basename(cleaned)

    # Reject empty, ".", or ".." results
    if not basename or basename == "." or basename == "..":
        return None

    # Remove any remaining path separators and null bytes
    basename = basename.replace(os.sep, "").replace("/", "").replace("\\", "").replace("\x00", "")

    # Reject if empty after removing separators and null bytes
    if not basename:
        return None

    # Forbid absolute paths (basename should handle this, but double-check)
    if os.path.isabs(basename):
        return None

    # Limit filename length (e.g., 255 characters, which is a common filesystem limit)
    if len(basename) > 255:
        basename = basename[:255]

    return basename

