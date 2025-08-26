from __future__ import annotations

import json
from typing import Any, Dict, Tuple
from urllib.parse import urlparse


def _parse_supabase_creds(api_key: str) -> Tuple[str, str]:
    api_key = api_key.strip()
    # Accept JSON {"url": "...", "key": "..."} or "url|key"
    if api_key.startswith("{"):
        data = json.loads(api_key)
        return data["url"], data["key"]
    if "|" in api_key:
        url, key = api_key.split("|", 1)
        return url.strip(), key.strip()
    raise ValueError("Supabase api_key must be JSON with url/key or 'url|key'")


def _parse_bucket_and_path(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str]:
    parsed = urlparse(bucket_link)
    if parsed.scheme:
        bucket = parsed.netloc or parsed.path.lstrip("/")
    else:
        bucket = bucket_link.strip().split("/")[0]
    prefix = "/".join([p.strip("/") for p in [cloud_folder_path] if p and p.strip("/")])
    path = f"{prefix + '/' if prefix else ''}{filename}"
    return bucket, path


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        from supabase import create_client

        url, key = _parse_supabase_creds(api_key)
        bucket, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, filename)

        client = create_client(url, key)
        client.storage.from_(bucket).upload(path, image_bytes, file_options={"content-type": "image/png", "upsert": True})
        public_url = client.storage.from_(bucket).get_public_url(path)

        return {
            "provider": "Supabase Storage",
            "bucket": bucket,
            "path": path,
            "url": public_url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        from supabase import create_client

        url, key = _parse_supabase_creds(api_key)
        bucket, _ = _parse_bucket_and_path(bucket_link, cloud_folder_path, "dummy")

        client = create_client(url, key)
        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            _, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, filename)
            client.storage.from_(bucket).upload(path, body, file_options={"content-type": "image/png", "upsert": True})
            public_url = client.storage.from_(bucket).get_public_url(path)
            results.append({"provider": "Supabase Storage", "bucket": bucket, "path": path, "url": public_url})
        return results


