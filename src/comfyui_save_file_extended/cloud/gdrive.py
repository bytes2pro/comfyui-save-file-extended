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

        headers = {"Authorization": f"Bearer {api_key}"}

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(api_key, path_prefix)
        else:
            # If extra path under folder id
            if path_prefix:
                parent_id = _resolve_parent_id_from_path(api_key, path_prefix)
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
        headers = {"Authorization": f"Bearer {api_key}"}

        if folder_id is None:
            parent_id = _resolve_parent_id_from_path(api_key, path_prefix)
        else:
            if path_prefix:
                parent_id = _resolve_parent_id_from_path(api_key, path_prefix)
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

