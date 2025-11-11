from __future__ import annotations

import io
import json
import mimetypes
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from google.cloud import storage
from google.oauth2 import service_account

from ._logging import log_exceptions


@log_exceptions
def _parse_bucket_and_key(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str]:
    parsed = urlparse(bucket_link)
    if parsed.scheme == "gs":
        bucket = parsed.netloc
        base_prefix = parsed.path.lstrip("/")
    else:
        bucket = bucket_link.strip().split("/")[0]
        base_prefix = "/".join(bucket_link.strip().split("/")[1:])

    parts = [p for p in [base_prefix, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p.strip("/")])
    key = f"{prefix + '/' if prefix else ''}{filename}"
    return bucket, key


class Uploader:
    @staticmethod
    @log_exceptions
    def _create_client(api_key: str):
        if api_key and api_key.strip().startswith("{"):
            info = json.loads(api_key)
            creds = service_account.Credentials.from_service_account_info(info)
            return storage.Client(credentials=creds, project=info.get("project_id"))
        elif api_key and api_key.strip().endswith(".json"):
            creds = service_account.Credentials.from_service_account_file(api_key.strip())
            return storage.Client(credentials=creds)
        else:
            return storage.Client()

    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        client = Uploader._create_client(api_key)

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        blob.upload_from_string(image_bytes, content_type=content_type)

        url = blob.public_url
        return {
            "provider": "Google Cloud Storage",
            "bucket": bucket_name,
            "path": key,
            "url": url,
        }

    @staticmethod
    @log_exceptions
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        client = Uploader._create_client(api_key)

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        bucket = client.bucket(bucket_name)
        results: list[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
            blob = bucket.blob(key)
            if byte_callback:
                blob.chunk_size = 8 * 1024 * 1024
                with blob.open("wb") as f:
                    bio = io.BytesIO(body)
                    sent = 0
                    while True:
                        chunk = bio.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        sent += len(chunk)
                        try:
                            byte_callback({"delta": len(chunk), "sent": sent, "total": len(body), "index": idx, "filename": filename, "path": key})
                        except Exception:
                            pass
            else:
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                blob.upload_from_string(body, content_type=content_type)
            results.append({"provider": "Google Cloud Storage", "bucket": bucket_name, "path": key, "url": blob.public_url})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": key})
                except Exception:
                    pass
        return results

    @staticmethod
    @log_exceptions
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        client = Uploader._create_client(api_key)

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, key_or_filename)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        return blob.download_as_bytes()

    @staticmethod
    @log_exceptions
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        client = Uploader._create_client(api_key)

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        bucket = client.bucket(bucket_name)
        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, name)
            blob = bucket.blob(key)
            if byte_callback:
                content_parts = []
                with blob.open("rb") as f:
                    sent = 0
                    while True:
                        data = f.read(8 * 1024 * 1024)
                        if not data:
                            break
                        content_parts.append(data)
                        sent += len(data)
                        try:
                            byte_callback({"delta": len(data), "sent": sent, "total": blob.size, "index": idx, "filename": name, "path": key})
                        except Exception:
                            pass
                content = b"".join(content_parts)
            else:
                content = blob.download_as_bytes()
            results.append({"filename": name, "content": content})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": key})
                except Exception:
                    pass
        return results
