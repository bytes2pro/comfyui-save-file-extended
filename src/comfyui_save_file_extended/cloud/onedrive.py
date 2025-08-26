from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlparse


def _build_path(bucket_link: str, cloud_folder_path: str, filename: str) -> str:
    base_path = urlparse(bucket_link).path or bucket_link
    parts = [p for p in [base_path, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    path = f"/{prefix + '/' if prefix else ''}{filename}"
    return path


def _ensure_onedrive_parent_id(access_token: str, path_prefix: str) -> str:
    import requests
    headers = {"Authorization": f"Bearer {access_token}"}

    # Get root id
    root_resp = requests.get("https://graph.microsoft.com/v1.0/me/drive/root", headers=headers)
    root_resp.raise_for_status()
    parent_id = root_resp.json().get("id")

    segments = [p for p in path_prefix.strip("/").split("/") if p]
    for seg in segments:
        # List children and search for seg
        list_resp = requests.get(f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children?$select=id,name", headers=headers)
        list_resp.raise_for_status()
        children = list_resp.json().get("value", [])
        match = next((c for c in children if c.get("name") == seg), None)
        if match:
            parent_id = match.get("id")
            continue
        # Create folder
        create_resp = requests.post(
            f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps({"name": seg, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"})
        )
        create_resp.raise_for_status()
        parent_id = create_resp.json().get("id")

    return parent_id


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        import requests

        if not api_key:
            raise ValueError("OneDrive api_key must be a valid OAuth 2.0 access token")

        path = _build_path(bucket_link, cloud_folder_path, filename)
        path_prefix = "/".join(path.strip("/").split("/")[:-1])

        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        # Ensure parent folder chain exists and get its id
        parent_id = _ensure_onedrive_parent_id(api_key.strip(), path_prefix)

        # Upload to parent id with the final filename
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}:/{filename}:/content"
        resp = requests.put(url, headers=headers, data=image_bytes)
        resp.raise_for_status()
        data = resp.json()
        web_url = data.get("webUrl")

        return {
            "provider": "OneDrive",
            "bucket": "",
            "path": path,
            "url": web_url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import requests

        if not api_key:
            raise ValueError("OneDrive api_key must be a valid OAuth 2.0 access token")

        # Build path prefix from inputs
        example_path = _build_path(bucket_link, cloud_folder_path, "dummy")
        path_prefix = "/".join(example_path.strip("/").split("/")[:-1])

        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        parent_id = _ensure_onedrive_parent_id(api_key.strip(), path_prefix)

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}:/{filename}:/content"
            resp = requests.put(url, headers=headers, data=body)
            resp.raise_for_status()
            data = resp.json()
            results.append({"provider": "OneDrive", "bucket": "", "path": f"/{path_prefix}/{filename}" if path_prefix else f"/{filename}", "url": data.get("webUrl")})
        return results


