from __future__ import annotations

import json
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from google.cloud import storage
from google.oauth2 import service_account


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
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        client = Uploader._create_client(api_key)

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        blob.upload_from_string(image_bytes, content_type="image/png")

        url = blob.public_url
        return {
            "provider": "Google Cloud Storage",
            "bucket": bucket_name,
            "path": key,
            "url": url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        client = Uploader._create_client(api_key)

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        bucket = client.bucket(bucket_name)
        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
            blob = bucket.blob(key)
            blob.upload_from_string(body, content_type="image/png")
            results.append({"provider": "Google Cloud Storage", "bucket": bucket_name, "path": key, "url": blob.public_url})
        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        client = Uploader._create_client(api_key)

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, key_or_filename)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        return blob.download_as_bytes()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        client: storage.Client
        if api_key and api_key.strip().startswith("{"):
            info = json.loads(api_key)
            creds = service_account.Credentials.from_service_account_info(info)
            client = storage.Client(credentials=creds, project=info.get("project_id"))
        elif api_key and api_key.strip().endswith(".json"):
            creds = service_account.Credentials.from_service_account_file(api_key.strip())
            client = storage.Client(credentials=creds)
        else:
            client = storage.Client()

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        bucket = client.bucket(bucket_name)
        results: list[Dict[str, Any]] = []
        for name in keys:
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, name)
            blob = bucket.blob(key)
            results.append({"filename": name, "content": blob.download_as_bytes()})
        return results
