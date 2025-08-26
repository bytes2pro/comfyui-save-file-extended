from __future__ import annotations

import json
from typing import Any, Dict, Tuple
from urllib.parse import parse_qs, urlparse

import requests
import mimetypes

from ._logging import log_exceptions


@log_exceptions
def _resolve_parent_id_from_path(api_token: str, path: str, base_parent_id: str = "root") -> str:
    """
    Resolve or create folders by path under My Drive and return the parent folder ID.
    This requires that api_token is a valid OAuth2 access token with drive scope.
    """

    headers = {"Authorization": f"Bearer {api_token}"}
    parent_id = base_parent_id or "root"
    parts = [p for p in path.strip("/").split("/") if p]
    for part in parts:
        q = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        search = requests.get("https://www.googleapis.com/drive/v3/files", params={"q": q, "fields": "files(id,name)"}, headers=headers)
        search.raise_for_status()
        files = search.json().get("files", [])
        if files:
            parent_id = files[0]["id"]
        else:
            # create folder
            meta = {"name": part, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
            created = requests.post("https://www.googleapis.com/drive/v3/files", headers={**headers, "Content-Type": "application/json"}, data=json.dumps(meta))
            created.raise_for_status()
            parent_id = created.json()["id"]
    return parent_id


@log_exceptions
def _get_access_token(api_key: str) -> str:
    """
    Accepts either a raw access token string or a JSON with fields:
      {"access_token": str, "refresh_token": str, "client_id": str, "client_secret": str}
    If a refresh_token is provided, exchanges it for a fresh access_token via Google's token endpoint.
    """
    key = api_key.strip()
    if key.startswith("{"):
        data = json.loads(key)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        if refresh_token and client_id and client_secret:
            resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=30,
            )
            resp.raise_for_status()
            token_json = resp.json()
            return token_json.get("access_token")
        if access_token:
            return access_token
        # Fallthrough to treat as raw token
    return key


@log_exceptions
def _get_headers(api_key: str) -> Dict[str, str]:
    access_token = _get_access_token(api_key)
    if not access_token:
        raise ValueError("[SaveFileExtended:gdrive] Missing access token after parsing cloud_api_key")
    return {"Authorization": f"Bearer {access_token}"}


def _extract_drive_folder_id_and_path(bucket_link: str) -> Tuple[str | None, str]:
    """
    Accepts:
      - drive://<folderId>/<optional/subpath>
      - https://drive.google.com/drive/folders/<folderId>[/<optional/subpath>]
      - https://drive.google.com/drive/u/0/folders/<folderId>
      - https://drive.google.com/open?id=<folderId>
      - plain path like /My/Folder/Sub (returns (None, "/My/Folder/Sub"))
    Returns: (folder_id_or_none, base_path)
    """
    parsed = urlparse(bucket_link)
    # drive:// scheme
    if parsed.scheme == "drive":
        segs = parsed.netloc.split("/") if parsed.netloc else []
        folder_id = segs[0] if segs else None
        base_path = parsed.path or ""
        return folder_id, base_path
    # google drive URL
    if parsed.netloc and "drive.google.com" in parsed.netloc:
        path_parts = [p for p in parsed.path.split("/") if p]
        folder_id = None
        base_path = ""
        if "folders" in path_parts:
            try:
                idx = path_parts.index("folders")
                folder_id = path_parts[idx + 1]
                # anything after folderId we treat as base_path
                remainder = path_parts[idx + 2:]
                base_path = "/" + "/".join(remainder) if remainder else ""
            except (ValueError, IndexError):
                folder_id = None
        if not folder_id:
            qs = parse_qs(parsed.query or "")
            vals = qs.get("id")
            folder_id = vals[0] if vals else None
        return folder_id, base_path
    # default: treat as plain path
    return None, parsed.path or bucket_link


class Uploader:
    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        if not api_key:
            raise ValueError("[SaveFileExtended:gdrive:upload] Google Drive api_key must be an OAuth2 access token with drive scope")

        # bucket_link can be a folder path, a Google Drive folder URL, or a folder id prefixed with drive://
        folder_id, base_path = _extract_drive_folder_id_and_path(bucket_link)

        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])

        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id="root")
        else:
            # Resolve any extra path under the provided folder id
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id=folder_id) if path_prefix else folder_id

        metadata = {"name": filename, "parents": [parent_id]}
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        files = {
            'metadata': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
            'file': ('file', image_bytes, content_type)
        }
        resp = requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', headers=headers, files=files)
        resp.raise_for_status()
        data = resp.json()

        return {
            "provider": "Google Drive",
            "bucket": parent_id,
            "path": f"{path_prefix}/{filename}" if path_prefix else filename,
            "url": f"https://drive.google.com/file/d/{data.get('id')}/view",
        }


    @staticmethod
    @log_exceptions
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        if not api_key:
            raise ValueError("[SaveFileExtended:gdrive:upload_many] Google Drive api_key must be an OAuth2 access token with drive scope")

        folder_id, base_path = _extract_drive_folder_id_and_path(bucket_link)

        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])
        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id="root")
        else:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id=folder_id) if path_prefix else folder_id

        results: list[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            if byte_callback and len(body) > 5 * 1024 * 1024:
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                init = requests.post(
                    'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                    headers={**headers, 'X-Upload-Content-Type': content_type, 'Content-Type': 'application/json; charset=UTF-8'},
                    data=json.dumps({"name": filename, "parents": [parent_id]})
                )
                init.raise_for_status()
                session_uri = init.headers.get('Location')
                sent = 0
                CHUNK = 8 * 1024 * 1024
                last_resp = None
                while sent < len(body):
                    chunk = body[sent:sent+CHUNK]
                    end = sent + len(chunk) - 1
                    put = requests.put(session_uri, headers={**headers, 'Content-Type': content_type, 'Content-Length': str(len(chunk)), 'Content-Range': f'bytes {sent}-{end}/{len(body)}'}, data=chunk)
                    if put.status_code not in (200, 201, 308):
                        put.raise_for_status()
                    sent += len(chunk)
                    last_resp = put
                    try:
                        byte_callback({"delta": len(chunk), "sent": sent, "total": len(body), "index": idx, "filename": filename, "path": f"{path_prefix}/{filename}" if path_prefix else filename})
                    except Exception:
                        pass
                data = last_resp.json() if (last_resp is not None and last_resp.content) else {"id": None}
            else:
                metadata = {"name": filename, "parents": [parent_id]}
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                files = {
                    'metadata': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
                    'file': ('file', body, content_type)
                }
                resp = requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', headers=headers, files=files)
                resp.raise_for_status()
                data = resp.json()
            results.append({"provider": "Google Drive", "bucket": parent_id, "path": f"{path_prefix}/{filename}" if path_prefix else filename, "url": f"https://drive.google.com/file/d/{data.get('id')}/view"})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": f"{path_prefix}/{filename}" if path_prefix else filename})
                except Exception:
                    pass

        return results

    @staticmethod
    @log_exceptions
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        access_token = _get_access_token(api_key)
        folder_id, base_path = _extract_drive_folder_id_and_path(bucket_link)
        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id="root")
        else:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id=folder_id) if path_prefix else folder_id

        headers = _get_headers(api_key)
        q = f"name='{key_or_filename}' and '{parent_id}' in parents and trashed=false"
        search = requests.get("https://www.googleapis.com/drive/v3/files", params={"q": q, "fields": "files(id,name)"}, headers=headers)
        search.raise_for_status()
        files = search.json().get("files", [])
        if not files:
            raise FileNotFoundError(key_or_filename)
        file_id = files[0]["id"]
        resp = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    @log_exceptions
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        access_token = _get_access_token(api_key)
        folder_id, base_path = _extract_drive_folder_id_and_path(bucket_link)
        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])
        parent_id = (
            _resolve_parent_id_from_path(access_token, path_prefix, base_parent_id="root") if folder_id is None
            else (_resolve_parent_id_from_path(access_token, path_prefix, base_parent_id=folder_id) if path_prefix else folder_id)
        )

        headers = _get_headers(api_key)
        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            q = f"name='{name}' and '{parent_id}' in parents and trashed=false"
            search = requests.get("https://www.googleapis.com/drive/v3/files", params={"q": q, "fields": "files(id,name)"}, headers=headers)
            search.raise_for_status()
            files = search.json().get("files", [])
            if not files:
                raise FileNotFoundError(name)
            file_id = files[0]["id"]
            resp = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers, stream=True)
            resp.raise_for_status()
            if byte_callback:
                parts = []
                sent = 0
                total = resp.headers.get('Content-Length') and int(resp.headers.get('Content-Length'))
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                    if not chunk:
                        break
                    parts.append(chunk)
                    sent += len(chunk)
                    try:
                        byte_callback({"delta": len(chunk), "sent": sent, "total": total, "index": idx, "filename": name, "path": f"{path_prefix}/{name}" if path_prefix else name})
                    except Exception:
                        pass
                content = b"".join(parts)
            else:
                content = resp.content
            results.append({"filename": name, "content": content})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": f"{path_prefix}/{name}" if path_prefix else name})
                except Exception:
                    pass
        return results
