from __future__ import annotations

from typing import Any, Dict, Tuple
from urllib.parse import urlparse


def _parse_creds(api_key: str) -> Tuple[str, str]:
    # Expect "APPLICATION_KEY_ID:APPLICATION_KEY"
    if ":" not in api_key:
        raise ValueError("Backblaze B2 api_key must be 'keyId:key'")
    key_id, app_key = api_key.split(":", 1)
    return key_id.strip(), app_key.strip()


def _parse_bucket_and_key(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str]:
    parsed = urlparse(bucket_link)
    if parsed.scheme == "b2":
        bucket = parsed.netloc
        base_prefix = parsed.path.lstrip("/")
    else:
        bucket = bucket_link.strip().split("/")[0]
        base_prefix = "/".join(bucket_link.strip().split("/")[1:])

    prefix_parts = [p for p in [base_prefix, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in prefix_parts if p.strip("/")])
    key = f"{prefix + '/' if prefix else ''}{filename}"
    return bucket, key


class Uploader:
    @staticmethod
    def _create_api(api_key: str):
        from b2sdk.v2 import B2Api, InMemoryAccountInfo
        key_id, app_key = _parse_creds(api_key)
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        return b2_api
    
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        from b2sdk.v2 import B2Api, InMemoryAccountInfo

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
        b2_api = Uploader._create_api(api_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        file_info = bucket.upload_bytes(image_bytes, key, content_type="image/png")

        download_url = f"https://f002.backblazeb2.com/file/{bucket_name}/{key}"
        return {
            "provider": "Backblaze B2",
            "bucket": bucket_name,
            "path": key,
            "url": download_url,
            "file_id": file_info.id_,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        from b2sdk.v2 import B2Api, InMemoryAccountInfo

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        b2_api = Uploader._create_api(api_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
            file_info = bucket.upload_bytes(body, key, content_type="image/png")
            download_url = f"https://f002.backblazeb2.com/file/{bucket_name}/{key}"
            results.append({"provider": "Backblaze B2", "bucket": bucket_name, "path": key, "url": download_url, "file_id": file_info.id_})

        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        import io

        from b2sdk.v2 import B2Api, InMemoryAccountInfo

        bucket_name, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, key_or_filename)
        b2_api = Uploader._create_api(api_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        bio = io.BytesIO()
        bucket.download_file_by_name(key).save(bio)
        return bio.getvalue()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import io

        from b2sdk.v2 import B2Api, InMemoryAccountInfo

        bucket_name, _ = _parse_bucket_and_key(bucket_link, cloud_folder_path, "dummy")
        b2_api = Uploader._create_api(api_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)

        results: list[Dict[str, Any]] = []
        for name in keys:
            _, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, name)
            bio = io.BytesIO()
            bucket.download_file_by_name(key).save(bio)
            results.append({"filename": name, "content": bio.getvalue()})
        return results


