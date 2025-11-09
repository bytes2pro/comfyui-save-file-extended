from __future__ import annotations

import base64
import json
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from supabase import create_client
import mimetypes

from ._logging import log_exceptions

try:
    from storage3.exceptions import StorageApiError
except Exception:  # pragma: no cover
    StorageApiError = Exception  # type: ignore


@log_exceptions
def _parse_supabase_creds(api_key: str) -> Tuple[str, str]:
    api_key = api_key.strip()
    # Accept JSON {"url": "...", "key": "..."} or "url|key"
    if api_key.startswith("{"):
        data = json.loads(api_key)
        url = data["url"]
        key = data["key"]
        # Basic sanity check: Supabase anon/service role keys are JWTs with two dots
        if not isinstance(key, str) or key.count(".") != 2:
            raise ValueError("[SaveFileExtended:supabase_storage:_parse_supabase_creds] Supabase key must be a valid anon/service_role JWT (see Project Settings → API → Project API keys)")
        return url, key
    if "|" in api_key:
        url, key = api_key.split("|", 1)
        url = url.strip()
        key = key.strip()
        if key.count(".") != 2:
            raise ValueError("[SaveFileExtended:supabase_storage:_parse_supabase_creds] Supabase key must be a valid anon/service_role JWT (use 'https://PROJECT.supabase.co|<JWT>')")
        return url, key
    raise ValueError("[SaveFileExtended:supabase_storage:_parse_supabase_creds] Supabase api_key must be JSON with url/key or 'url|key'")


def _jwt_role(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        padding = '=' * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode((payload_b64 + padding).encode()).decode()
        data = json.loads(payload)
        return data.get("role")
    except Exception:
        return None


@log_exceptions
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
    @log_exceptions
    def _get_client(api_key: str):
        url, key = _parse_supabase_creds(api_key)
        return create_client(url, key)

    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        client = Uploader._get_client(api_key)
        bucket, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, filename)
        role = _jwt_role(_parse_supabase_creds(api_key)[1])
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            client.storage.from_(bucket).upload(path, image_bytes, file_options={"content-type": content_type, "upsert": "true"})
        except StorageApiError as e:  # type: ignore
            msg = str(e)
            if "row-level security" in msg.lower() and role != "service_role":
                raise PermissionError(
                    "Supabase Storage upload blocked by RLS. Use a service_role key, or add a storage.objects INSERT policy for your bucket (e.g., allow anon insert when bucket_id='{}').".format(bucket)
                ) from e
            raise
        public_url = client.storage.from_(bucket).get_public_url(path)

        return {
            "provider": "Supabase Storage",
            "bucket": bucket,
            "path": path,
            "url": public_url,
        }

    @staticmethod
    @log_exceptions
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        client = Uploader._get_client(api_key)
        bucket, _ = _parse_bucket_and_path(bucket_link, cloud_folder_path, "dummy")
        role = _jwt_role(_parse_supabase_creds(api_key)[1])
        results: list[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            _, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, filename)
            try:
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                client.storage.from_(bucket).upload(path, body, file_options={"content-type": content_type, "upsert": "true"})
            except StorageApiError as e:  # type: ignore
                msg = str(e)
                if "row-level security" in msg.lower() and role != "service_role":
                    raise PermissionError(
                        "Supabase Storage upload blocked by RLS. Use a service_role key, or add an INSERT policy on storage.objects for bucket_id='{}'.".format(bucket)
                    ) from e
                raise
            if byte_callback:
                try:
                    byte_callback({"delta": len(body), "sent": len(body), "total": len(body), "index": idx, "filename": filename, "path": path})
                except Exception:
                    pass
            public_url = client.storage.from_(bucket).get_public_url(path)
            results.append({"provider": "Supabase Storage", "bucket": bucket, "path": path, "url": public_url})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": path})
                except Exception:
                    pass
        return results

    @staticmethod
    @log_exceptions
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        client = Uploader._get_client(api_key)
        bucket, _ = _parse_bucket_and_path(bucket_link, cloud_folder_path, "dummy")
        _, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, key_or_filename)
        role = _jwt_role(_parse_supabase_creds(api_key)[1])
        try:
            data = client.storage.from_(bucket).download(path)
        except StorageApiError as e:  # type: ignore
            msg = str(e)
            if "row-level security" in msg.lower() and role != "service_role":
                raise PermissionError(
                    "Supabase Storage download blocked by RLS. Mark the bucket public or add a SELECT policy on storage.objects for bucket_id='{}'.".format(bucket)
                ) from e
            raise
        return data

    @staticmethod
    @log_exceptions
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        client = Uploader._get_client(api_key)
        bucket, _ = _parse_bucket_and_path(bucket_link, cloud_folder_path, "dummy")
        role = _jwt_role(_parse_supabase_creds(api_key)[1])
        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            _, path = _parse_bucket_and_path(bucket_link, cloud_folder_path, name)
            try:
                data = client.storage.from_(bucket).download(path)
            except StorageApiError as e:  # type: ignore
                msg = str(e)
                if "row-level security" in msg.lower() and role != "service_role":
                    raise PermissionError(
                        "Supabase Storage download blocked by RLS. Mark the bucket public or add a SELECT policy on storage.objects for bucket_id='{}'.".format(bucket)
                    ) from e
                raise
            if byte_callback:
                try:
                    byte_callback({"delta": len(data), "sent": len(data), "total": len(data), "index": idx, "filename": name, "path": path})
                except Exception:
                    pass
            results.append({"filename": name, "content": data})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": path})
                except Exception:
                    pass
        return results
