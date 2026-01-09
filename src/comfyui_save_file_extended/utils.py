"""
Utility functions for comfyui-save-file-extended.
"""
import os
import re
from datetime import datetime


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


def process_date_variables(text: str, now: datetime | None = None) -> str:
    """
    Process custom date format variables in text.

    Replaces patterns like %date:yyyy-MM-dd% with the actual formatted date.
    Uses Java-style date format patterns which are converted to Python strftime.

    Args:
        text: The input text containing date patterns
        now: Optional datetime to use (defaults to datetime.now())

    Returns:
        Text with date patterns replaced with formatted dates

    Supported format patterns:
        - yyyy: 4-digit year (e.g., 2024)
        - yy: 2-digit year (e.g., 24)
        - MMMM: Full month name (e.g., January)
        - MMM: Abbreviated month name (e.g., Jan)
        - MM: 2-digit month (e.g., 01)
        - M: Month without leading zero (e.g., 1)
        - dd: 2-digit day (e.g., 05)
        - d: Day without leading zero (e.g., 5)
        - EEEE: Full weekday name (e.g., Monday)
        - EEE: Abbreviated weekday name (e.g., Mon)
        - HH: 24-hour hour (e.g., 14)
        - hh: 12-hour hour (e.g., 02)
        - mm: Minutes (e.g., 30)
        - ss: Seconds (e.g., 45)
        - a: AM/PM marker

    Examples:
        >>> process_date_variables("%date:yyyy-MM-dd%")  # doctest: +SKIP
        '2024-01-15'
        >>> process_date_variables("%date:yyyyMMdd_HHmmss%")  # doctest: +SKIP
        '20240115_143045'
        >>> process_date_variables("file_%date:yyyy%_test")  # doctest: +SKIP
        'file_2024_test'
    """
    if not text or "%date:" not in text:
        return text

    if now is None:
        now = datetime.now()

    # Pattern to match %date:FORMAT%
    pattern = r"%date:([^%]+)%"

    def replace_date(match: re.Match) -> str:
        java_format = match.group(1)
        return _convert_java_date_format(java_format, now)

    return re.sub(pattern, replace_date, text)


def _convert_java_date_format(java_format: str, dt: datetime) -> str:
    """
    Convert a Java-style date format string to a formatted date.

    Args:
        java_format: Java-style date format (e.g., 'yyyy-MM-dd')
        dt: datetime object to format

    Returns:
        Formatted date string
    """
    # Mapping from Java date patterns to Python strftime (order matters - longer patterns first)
    # We need to handle patterns carefully to avoid partial replacements
    replacements = [
        ("yyyy", dt.strftime("%Y")),
        ("yy", dt.strftime("%y")),
        ("MMMM", dt.strftime("%B")),
        ("MMM", dt.strftime("%b")),
        ("MM", dt.strftime("%m")),
        ("M", str(dt.month)),
        ("dd", dt.strftime("%d")),
        ("d", str(dt.day)),
        ("EEEE", dt.strftime("%A")),
        ("EEE", dt.strftime("%a")),
        ("HH", dt.strftime("%H")),
        ("hh", dt.strftime("%I")),
        ("mm", dt.strftime("%M")),
        ("ss", dt.strftime("%S")),
        ("a", dt.strftime("%p")),
    ]

    result = java_format

    # Use a placeholder approach to prevent double replacement
    # First pass: replace patterns with unique placeholders
    placeholders = {}
    for i, (java_pattern, _) in enumerate(replacements):
        placeholder = f"\x00{i}\x00"
        if java_pattern in result:
            result = result.replace(java_pattern, placeholder, 1)
            placeholders[placeholder] = replacements[i][1]
            # Continue replacing remaining occurrences
            while java_pattern in result:
                result = result.replace(java_pattern, placeholder, 1)

    # Second pass: replace placeholders with actual values
    for placeholder, value in placeholders.items():
        result = result.replace(placeholder, value)

    return result


def process_node_field_tokens(text: str, prompt: dict | None) -> str:
    """
    Process node field tokens in text.

    Replaces patterns like %NodeName.fieldname% with the actual field value
    from the workflow prompt data.

    Args:
        text: The input text containing node field patterns
        prompt: The workflow prompt dictionary containing node data.
                Structure: {node_id: {"class_type": "NodeName", "inputs": {...}}}

    Returns:
        Text with node field patterns replaced with actual values.
        Unmatched patterns are left unchanged.

    Examples:
        >>> prompt = {"1": {"class_type": "Empty Latent Image", "inputs": {"width": 512, "height": 768}}}
        >>> process_node_field_tokens("%Empty Latent Image.width%", prompt)
        '512'
        >>> process_node_field_tokens("size_%Empty Latent Image.width%x%Empty Latent Image.height%", prompt)
        'size_512x768'
    """
    if not text or not prompt or "%" not in text:
        return text

    # Pattern to match %NodeName.fieldname% where NodeName can contain spaces
    # but cannot contain % or .
    # The pattern is: %<anything except % and .>.<anything except %>%
    pattern = r"%([^%.]+)\.([^%]+)%"

    def replace_token(match: re.Match) -> str:
        node_name = match.group(1)
        field_name = match.group(2)

        # Search for a node with matching class_type
        for node_id, node_data in prompt.items():
            if not isinstance(node_data, dict):
                continue

            class_type = node_data.get("class_type", "")
            if class_type == node_name:
                inputs = node_data.get("inputs", {})
                if field_name in inputs:
                    value = inputs[field_name]
                    # Convert value to string, handling various types
                    if isinstance(value, (list, tuple)):
                        # For list/tuple inputs (like linked connections),
                        # return the original token as we can't resolve it
                        return match.group(0)
                    return str(value)

        # Node or field not found - return original token unchanged
        return match.group(0)

    return re.sub(pattern, replace_token, text)


# Environment variable name for cloud API key
CLOUD_API_KEY_ENV_VAR = "COMFYUI_CLOUD_API_KEY"


def get_cloud_api_key(provided_key: str, provider: str | None = None) -> str:
    """
    Get the cloud API key, with environment variable fallback.

    Priority order:
    1. Provided key (if non-empty)
    2. Provider-specific env var: COMFYUI_CLOUD_API_KEY_{PROVIDER}
       (e.g., COMFYUI_CLOUD_API_KEY_AWS_S3, COMFYUI_CLOUD_API_KEY_GOOGLE_DRIVE)
    3. General env var: COMFYUI_CLOUD_API_KEY

    Args:
        provided_key: The key provided by the user in the node input
        provider: Optional cloud provider name for provider-specific env var lookup

    Returns:
        The API key to use (may be empty string if none found)

    Examples:
        >>> import os
        >>> os.environ["COMFYUI_CLOUD_API_KEY"] = "env_key"
        >>> get_cloud_api_key("")  # Returns env var value
        'env_key'
        >>> get_cloud_api_key("user_key")  # User key takes priority
        'user_key'
    """
    # If user provided a non-empty key, use it
    if provided_key and provided_key.strip():
        return provided_key

    # Try provider-specific env var first
    if provider:
        # Normalize provider name for env var (e.g., "AWS S3" -> "AWS_S3")
        provider_normalized = provider.upper().replace(" ", "_").replace("-", "_")
        provider_env_var = f"COMFYUI_CLOUD_API_KEY_{provider_normalized}"
        provider_key = os.environ.get(provider_env_var, "")
        if provider_key.strip():
            return provider_key

    # Fall back to general env var
    return os.environ.get(CLOUD_API_KEY_ENV_VAR, "")

