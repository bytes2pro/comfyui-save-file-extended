from __future__ import annotations

import io
from ftplib import FTP
from typing import Any, Dict
from urllib.parse import urlparse


def _parse_ftp(bucket_link: str, cloud_folder_path: str):
    parsed = urlparse(bucket_link)
    if parsed.scheme != "ftp":
        raise ValueError("FTP bucket_link must start with ftp://user:pass@host[:port]/basepath")
    host = parsed.hostname
    port = parsed.port or 21
    user = parsed.username or "anonymous"
    password = parsed.password or "anonymous@"
    base_path = parsed.path or "/"
    parts = [p for p in [base_path, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    return host, port, user, password, prefix


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)
        remote_path = f"/{prefix + '/' if prefix else ''}{filename}"

        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Ensure directories
            dirs = remote_path.strip("/").split("/")[:-1]
            cwd = "/"
            for d in dirs:
                try:
                    ftp.mkd(d)
                except Exception:
                    pass
                ftp.cwd(d)
            # Upload
            ftp.storbinary(f"STOR {filename}", io.BytesIO(image_bytes))

        return {
            "provider": "FTP",
            "bucket": host or "",
            "path": remote_path,
            "url": None,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None) -> list[Dict[str, Any]]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)

        results: list[Dict[str, Any]] = []
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Ensure directories once
            if prefix:
                dirs = prefix.strip("/").split("/")
                for d in dirs:
                    try:
                        ftp.mkd(d)
                    except Exception:
                        pass
                    ftp.cwd(d)
            for idx, item in enumerate(items):
                filename = item["filename"]
                body = item["content"]
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
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)
        remote_path = f"/{prefix + '/' if prefix else ''}{key_or_filename}"

        bio = io.BytesIO()
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            # Change to directory
            dirs = remote_path.strip("/").split("/")[:-1]
            for d in dirs:
                ftp.cwd(d)
            ftp.retrbinary(f"RETR {key_or_filename}", bio.write)
        return bio.getvalue()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None) -> list[Dict[str, Any]]:
        host, port, user, password, prefix = _parse_ftp(bucket_link, cloud_folder_path)

        results: list[Dict[str, Any]] = []
        with FTP() as ftp:
            ftp.connect(host, port)
            ftp.login(user=user, passwd=password)
            if prefix:
                for d in prefix.strip("/").split("/"):
                    ftp.cwd(d)
            for idx, name in enumerate(keys):
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {name}", bio.write)
                results.append({"filename": name, "content": bio.getvalue()})
                if progress_callback:
                    try:
                        progress_callback({"index": idx, "filename": name, "path": f"/{prefix}/{name}" if prefix else f"/{name}"})
                    except Exception:
                        pass
        return results


