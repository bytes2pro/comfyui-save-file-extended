from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlparse


def _resolve_parent_id_from_path(api_token: str, path: str) -> str:
    """
    Resolve or create folders by path under My Drive and return the parent folder ID.
    This requires that api_token is a valid OAuth2 access token with drive scope.
    """
    import requests

    headers = {"Authorization": f"Bearer {api_token}"}
    parent_id = "root"
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


def _get_access_token(api_key: str) -> str:
    """
    Accepts either a raw access token string or a JSON with fields:
      {"access_token": str, "refresh_token": str, "client_id": str, "client_secret": str}
    If a refresh_token is provided, exchanges it for a fresh access_token via Google's token endpoint.
    """
    import requests

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


def _get_headers(api_key: str) -> Dict[str, str]:
    access_token = _get_access_token(api_key)
    return {"Authorization": f"Bearer {access_token}"}


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        import requests  # type: ignore

        if not api_key:
            raise ValueError("Google Drive api_key must be an OAuth2 access token with drive scope")

        # bucket_link can be a folder path or a folder id prefixed with drive://id/<optional-subpath>
        parsed = urlparse(bucket_link)
        base_path = parsed.path if parsed.scheme != "drive" else ""
        folder_id = None
        if parsed.scheme == "drive":
            # drive://<folderId>/<optional-subpath>
            segs = parsed.netloc.split("/") if parsed.netloc else []
            folder_id = segs[0] if segs else None
            if parsed.path:
                base_path = parsed.path

        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])

        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix)
        else:
            # If extra path under folder id
            if path_prefix:
                parent_id = _resolve_parent_id_from_path(access_token, path_prefix)
            else:
                parent_id = folder_id

        metadata = {"name": filename, "parents": [parent_id]}
        files = {
            'metadata': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
            'file': ('file', image_bytes, 'image/png')
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
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import requests

        if not api_key:
            raise ValueError("Google Drive api_key must be an OAuth2 access token with drive scope")

        parsed = urlparse(bucket_link)
        base_path = parsed.path if parsed.scheme != "drive" else ""
        folder_id = None
        if parsed.scheme == "drive":
            segs = parsed.netloc.split("/") if parsed.netloc else []
            folder_id = segs[0] if segs else None
            if parsed.path:
                base_path = parsed.path

        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])
        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix)
        else:
            if path_prefix:
                parent_id = _resolve_parent_id_from_path(access_token, path_prefix)
            else:
                parent_id = folder_id

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            metadata = {"name": filename, "parents": [parent_id]}
            files = {
                'metadata': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
                'file': ('file', body, 'image/png')
            }
            resp = requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', headers=headers, files=files)
            resp.raise_for_status()
            data = resp.json()
            results.append({"provider": "Google Drive", "bucket": parent_id, "path": f"{path_prefix}/{filename}" if path_prefix else filename, "url": f"https://drive.google.com/file/d/{data.get('id')}/view"})

        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        import requests

        access_token = _get_access_token(api_key)
        parsed = urlparse(bucket_link)
        base_path = parsed.path if parsed.scheme != "drive" else ""
        folder_id = None
        if parsed.scheme == "drive":
            segs = parsed.netloc.split("/") if parsed.netloc else []
            folder_id = segs[0] if segs else None
            if parsed.path:
                base_path = parsed.path
        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix)
        else:
            parent_id = _resolve_parent_id_from_path(access_token, path_prefix) if path_prefix else folder_id

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
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import requests

        access_token = _get_access_token(api_key)
        parsed = urlparse(bucket_link)
        base_path = parsed.path if parsed.scheme != "drive" else ""
        folder_id = None
        if parsed.scheme == "drive":
            segs = parsed.netloc.split("/") if parsed.netloc else []
            folder_id = segs[0] if segs else None
            if parsed.path:
                base_path = parsed.path
        path_prefix = "/".join([p.strip("/") for p in [base_path, cloud_folder_path] if p and p.strip("/")])
        parent_id = _resolve_parent_id_from_path(access_token, path_prefix) if folder_id is None or path_prefix else folder_id

        headers = _get_headers(api_key)
        results: list[Dict[str, Any]] = []
        for name in keys:
            q = f"name='{name}' and '{parent_id}' in parents and trashed=false"
            search = requests.get("https://www.googleapis.com/drive/v3/files", params={"q": q, "fields": "files(id,name)"}, headers=headers)
            search.raise_for_status()
            files = search.json().get("files", [])
            if not files:
                raise FileNotFoundError(name)
            file_id = files[0]["id"]
            resp = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers)
            resp.raise_for_status()
            results.append({"filename": name, "content": resp.content})
        return results

