from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

import dropbox

from ._logging import log_exceptions


@log_exceptions
def _resolve_path(bucket_link: str, cloud_folder_path: str, filename: str) -> str:
    parsed = urlparse(bucket_link)
    base_path = parsed.path if parsed.scheme else bucket_link
    parts = [p for p in [base_path, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    path = f"/{prefix + '/' if prefix else ''}{filename}"
    return path


class Uploader:
    @staticmethod
    @log_exceptions
    def _get_dbx(api_key: str):
        if not api_key:
            raise ValueError("[SaveFileExtended:dropbox_client:_get_dbx] Dropbox api_key (access token) is required")
        return dropbox.Dropbox(api_key.strip())
    
    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        dbx = Uploader._get_dbx(api_key)
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
    @log_exceptions
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        dbx = Uploader._get_dbx(api_key)

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
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            path = _resolve_path(bucket_link, cloud_folder_path, filename)
            if byte_callback and len(body) > 4 * 1024 * 1024:
                CHUNK = 4 * 1024 * 1024
                session_start = dbx.files_upload_session_start(body[:CHUNK])
                sent = CHUNK
                try:
                    byte_callback({"delta": CHUNK, "sent": sent, "total": len(body), "index": idx, "filename": filename, "path": path})
                except Exception:
                    pass
                cursor = dropbox.files.UploadSessionCursor(session_id=session_start.session_id, offset=sent)
                commit = dropbox.files.CommitInfo(path, mode=dropbox.files.WriteMode.overwrite)
                while sent < len(body):
                    chunk = body[sent:sent+CHUNK]
                    if (len(body) - sent) <= CHUNK:
                        dbx.files_upload_session_finish(chunk, cursor, commit)
                        sent += len(chunk)
                    else:
                        dbx.files_upload_session_append_v2(chunk, cursor)
                        sent += len(chunk)
                        cursor.offset = sent
                    try:
                        byte_callback({"delta": len(chunk), "sent": sent, "total": len(body), "index": idx, "filename": filename, "path": path})
                    except Exception:
                        pass
            else:
                dbx.files_upload(body, path, mode=dropbox.files.WriteMode.overwrite, mute=True)
            results.append({"provider": "Dropbox", "bucket": "", "path": path, "url": None})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": path})
                except Exception:
                    pass
        return results

    @staticmethod
    @log_exceptions
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        dbx = Uploader._get_dbx(api_key)
        path = _resolve_path(bucket_link, cloud_folder_path, key_or_filename)
        metadata, resp = dbx.files_download(path)
        return resp.content

    @staticmethod
    @log_exceptions
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        dbx = Uploader._get_dbx(api_key)
        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            path = _resolve_path(bucket_link, cloud_folder_path, name)
            metadata, resp = dbx.files_download(path)
            if byte_callback:
                content_parts = []
                sent = 0
                for chunk in resp.iter_content(chunk_size=4 * 1024 * 1024):
                    if not chunk:
                        break
                    content_parts.append(chunk)
                    sent += len(chunk)
                    try:
                        byte_callback({"delta": len(chunk), "sent": sent, "total": resp.headers.get('Content-Length') and int(resp.headers.get('Content-Length')), "index": idx, "filename": name, "path": path})
                    except Exception:
                        pass
                content = b"".join(content_parts)
            else:
                content = resp.content
            results.append({"filename": name, "content": content})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": path})
                except Exception:
                    pass
        return results
