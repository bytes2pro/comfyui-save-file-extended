from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse


def _resolve_path(bucket_link: str, cloud_folder_path: str, filename: str) -> str:
    parsed = urlparse(bucket_link)
    base_path = parsed.path if parsed.scheme else bucket_link
    parts = [p for p in [base_path, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    path = f"/{prefix + '/' if prefix else ''}{filename}"
    return path


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        import dropbox

        if not api_key:
            raise ValueError("Dropbox api_key (access token) is required")

        dbx = dropbox.Dropbox(api_key.strip())
        # Ensure folder path exists
        parent_path = _resolve_path(bucket_link, cloud_folder_path, "").rstrip("/")
        if parent_path and parent_path != "/":
            # Create nested folders if missing
            segments = [p for p in parent_path.strip("/").split("/") if p]
            current = ""
            for seg in segments:
                current = f"{current}/{seg}"
                try:
                    dbx.files_create_folder_v2(current)
                except Exception:
                    # Ignore if already exists or any non-fatal errors
                    pass

        path = _resolve_path(bucket_link, cloud_folder_path, filename)
        dbx.files_upload(image_bytes, path, mode=dropbox.files.WriteMode.overwrite, mute=True)

        return {
            "provider": "Dropbox",
            "bucket": "",
            "path": path,
            "url": None,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import dropbox

        if not api_key:
            raise ValueError("Dropbox api_key (access token) is required")

        dbx = dropbox.Dropbox(api_key.strip())

        # Ensure folder path exists once
        parent_path = _resolve_path(bucket_link, cloud_folder_path, "").rstrip("/")
        if parent_path and parent_path != "/":
            segments = [p for p in parent_path.strip("/").split("/") if p]
            current = ""
            for seg in segments:
                current = f"{current}/{seg}"
                try:
                    dbx.files_create_folder_v2(current)
                except Exception:
                    pass

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            path = _resolve_path(bucket_link, cloud_folder_path, filename)
            dbx.files_upload(body, path, mode=dropbox.files.WriteMode.overwrite, mute=True)
            results.append({"provider": "Dropbox", "bucket": "", "path": path, "url": None})
        return results


