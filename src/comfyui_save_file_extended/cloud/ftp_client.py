from __future__ import annotations

import io
from ftplib import FTP
from typing import Any, Dict
from urllib.parse import urlparse


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
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
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
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
            for item in items:
                filename = item["filename"]
                body = item["content"]
                ftp.storbinary(f"STOR {filename}", io.BytesIO(body))
                results.append({"provider": "FTP", "bucket": host or "", "path": f"/{prefix}/{filename}" if prefix else f"/{filename}", "url": None})

        return results


