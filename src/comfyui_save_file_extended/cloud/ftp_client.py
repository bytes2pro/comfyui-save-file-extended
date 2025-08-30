from __future__ import annotations

import io
from ftplib import FTP
from typing import Any, Dict
from urllib.parse import urlparse

from ._logging import log_exceptions


@log_exceptions
def _parse_ftp(bucket_link: str, cloud_folder_path: str):
    bucket_link = bucket_link.strip() if bucket_link else ""
    cf = (cloud_folder_path or "").strip()
    parsed = urlparse(bucket_link)
    if parsed.scheme != "ftp":
        raise ValueError("[SaveFileExtended:ftp_client:_parse_ftp] FTP bucket_link must start with ftp://user:pass@host[:port]/basepath")
    host = parsed.hostname
    port = parsed.port or 21
    user = parsed.username or "anonymous"
    password = parsed.password or "anonymous@"
    base_path = parsed.path or "/"
    parts = [p for p in [base_path, cf] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    return host, port, user, password, prefix


def _ensure_and_cd(ftp: FTP, path: str) -> None:
    """Ensure the given path exists on the FTP server, then cwd into it.

    The function starts from the FTP root to avoid issues with servers that
    set a non-root default directory. Each path segment is created if missing
    and then entered.
    """
    if not path:
        return
    try:
        ftp.cwd("/")
    except Exception:
        # Some FTP servers disallow changing to root; start from current dir
        pass
    for segment in [p for p in path.strip("/").split("/") if p]:
        try:
            ftp.mkd(segment)
        except Exception:
            # Directory may already exist or creation not needed; continue
            pass
        ftp.cwd(segment)


def _cd_only(ftp: FTP, path: str) -> None:
    """Change directory to the given path starting from root without creating it."""
    if not path:
        return
    try:
        ftp.cwd("/")
    except Exception:
        # Some FTP servers disallow changing to root; start from current dir
        pass
    for segment in [p for p in path.strip("/").split("/") if p]:
        ftp.cwd(segment)


def _retr_with_fallbacks(ftp: FTP, filename: str, prefix: str | None, callback) -> None:
    """Attempt RETR using multiple path variants to handle server quirks."""
    name = (filename or "").strip().lstrip("/")
    pfx = (prefix or "").strip("/")
    candidates = []
    # Current directory
    candidates.append(name)
    # Relative with prefix
    if pfx:
        candidates.append(f"{pfx}/{name}")
    # Absolute variants
    candidates.append(f"/{name}")
    if pfx:
        candidates.append(f"/{pfx}/{name}")

    last_err = None
    for remote in candidates:
        try:
            ftp.retrbinary(f"RETR {remote}", callback)
            return
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err


class Uploader:
    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)
        remote_path = f"/{prefix + '/' if prefix else ''}{filename}"

        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Ensure directories and move into them, starting from root
            _ensure_and_cd(ftp, prefix)
            # Upload
            ftp.storbinary(f"STOR {filename}", io.BytesIO(image_bytes))

        return {
            "provider": "FTP",
            "bucket": host or "",
            "path": remote_path,
            "url": None,
        }

    @staticmethod
    @log_exceptions
    def upload_many(
        items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None
    ) -> list[Dict[str, Any]]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)

        results: list[Dict[str, Any]] = []
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Ensure directories once, starting from root
            _ensure_and_cd(ftp, prefix)
            for idx, item in enumerate(items):
                filename = item["filename"]
                body = item["content"]
                if byte_callback:
                    bio = io.BytesIO(body)
                    sent = {"n": 0}

                    def _cb(chunk):
                        sent["n"] += len(chunk)
                        try:
                            byte_callback(
                                {
                                    "delta": len(chunk),
                                    "sent": sent["n"],
                                    "total": len(body),
                                    "index": idx,
                                    "filename": filename,
                                    "path": f"/{prefix}/{filename}" if prefix else f"/{filename}",
                                }
                            )
                        except Exception:
                            pass

                    ftp.storbinary(f"STOR {filename}", bio, callback=_cb)
                else:
                    ftp.storbinary(f"STOR {filename}", io.BytesIO(body))
                path = f"/{prefix}/{filename}" if prefix else f"/{filename}"
                results.append({"provider": "FTP", "bucket": host or "", "path": path, "url": None})
                if progress_callback:
                    try:
                        progress_callback({"index": idx, "filename": filename, "path": path})
                    except Exception:
                        pass

        return results

    @staticmethod
    @log_exceptions
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)

        bio = io.BytesIO()
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Change to target directory (without creating)
            _cd_only(ftp, prefix)
            _retr_with_fallbacks(ftp, key_or_filename, prefix, bio.write)
        return bio.getvalue()

    @staticmethod
    @log_exceptions
    def download_many(
        keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None
    ) -> list[Dict[str, Any]]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)

        results: list[Dict[str, Any]] = []
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            _cd_only(ftp, prefix)
            for idx, name in enumerate(keys):
                bio = io.BytesIO()
                if byte_callback:
                    sent = {"n": 0}

                    def _cb(chunk):
                        bio.write(chunk)
                        sent["n"] += len(chunk)
                        try:
                            byte_callback(
                                {
                                    "delta": len(chunk),
                                    "sent": sent["n"],
                                    "total": None,
                                    "index": idx,
                                    "filename": name,
                                    "path": f"/{prefix}/{name}" if prefix else f"/{name}",
                                }
                            )
                        except Exception:
                            pass

                    _retr_with_fallbacks(ftp, name, prefix, _cb)
                else:
                    _retr_with_fallbacks(ftp, name, prefix, bio.write)
                results.append({"filename": name, "content": bio.getvalue()})
                if progress_callback:
                    try:
                        progress_callback({"index": idx, "filename": name, "path": f"/{prefix}/{name}" if prefix else f"/{name}"})
                    except Exception:
                        pass
        return results
