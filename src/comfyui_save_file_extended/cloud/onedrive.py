from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlparse

import requests


def _build_path(bucket_link: str, cloud_folder_path: str, filename: str) -> str:
    base_path = urlparse(bucket_link).path or bucket_link
    parts = [p for p in [base_path, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p and p.strip("/")])
    path = f"/{prefix + '/' if prefix else ''}{filename}"
    return path


def _ensure_onedrive_parent_id(access_token: str, path_prefix: str) -> str:
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


def _get_access_token(api_key: str) -> str:
    """
    Accepts either a raw access token string or a JSON with fields:
      {"access_token": str, "refresh_token": str, "client_id": str, "client_secret": str, "tenant": "common|consumers|organizations", "redirect_uri": str}
    If a refresh_token is provided, exchanges it for a fresh access_token via Microsoft identity platform.
    """
    key = api_key.strip()
    if key.startswith("{"):
        data = json.loads(key)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        tenant = data.get("tenant") or "common"
        redirect_uri = data.get("redirect_uri")
        if refresh_token and client_id and (client_secret or True):
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            form = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            }
            if client_secret:
                form["client_secret"] = client_secret
            if redirect_uri:
                form["redirect_uri"] = redirect_uri
            # Scope is typically not required for refresh, omit to avoid mismatch
            resp = requests.post(token_url, data=form, timeout=30)
            resp.raise_for_status()
            token_json = resp.json()
            return token_json.get("access_token")
        if access_token:
            return access_token
    return key


def _get_headers(api_key: str) -> Dict[str, str]:
    token = _get_access_token(api_key)
    return {"Authorization": f"Bearer {token}"}


class Uploader:
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        if not api_key:
            raise ValueError("OneDrive api_key must be a valid OAuth 2.0 access token")

        path = _build_path(bucket_link, cloud_folder_path, filename)
        path_prefix = "/".join(path.strip("/").split("/")[:-1])

        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)
        # Ensure parent folder chain exists and get its id
        parent_id = _ensure_onedrive_parent_id(access_token, path_prefix)

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
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        if not api_key:
            raise ValueError("OneDrive api_key must be a valid OAuth 2.0 access token")

        # Build path prefix from inputs
        example_path = _build_path(bucket_link, cloud_folder_path, "dummy")
        path_prefix = "/".join(example_path.strip("/").split("/")[:-1])

        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)
        parent_id = _ensure_onedrive_parent_id(access_token, path_prefix)

        results: list[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            if byte_callback and len(body) > 4 * 1024 * 1024:
                session = requests.post(
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}:/{filename}:/createUploadSession",
                    headers=headers,
                    json={"item": {"@microsoft.graph.conflictBehavior": "replace"}}
                )
                session.raise_for_status()
                upload_url = session.json().get('uploadUrl')
                CHUNK = 8 * 1024 * 1024
                sent = 0
                last_resp = None
                while sent < len(body):
                    chunk = body[sent:sent+CHUNK]
                    end = sent + len(chunk) - 1
                    r = requests.put(upload_url, headers={'Content-Length': str(len(chunk)), 'Content-Range': f'bytes {sent}-{end}/{len(body)}'}, data=chunk)
                    if r.status_code not in (200, 201, 202):
                        r.raise_for_status()
                    sent += len(chunk)
                    last_resp = r
                    try:
                        byte_callback({"delta": len(chunk), "sent": sent, "total": len(body), "index": idx, "filename": filename, "path": f"/{path_prefix}/{filename}" if path_prefix else f"/{filename}"})
                    except Exception:
                        pass
                data = last_resp.json() if (last_resp is not None and last_resp.content) else {}
            else:
                url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}:/{filename}:/content"
                resp = requests.put(url, headers=headers, data=body)
                resp.raise_for_status()
                data = resp.json()
            results.append({"provider": "OneDrive", "bucket": "", "path": f"/{path_prefix}/{filename}" if path_prefix else f"/{filename}", "url": data.get("webUrl")})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": f"/{path_prefix}/{filename}" if path_prefix else f"/{filename}"})
                except Exception:
                    pass
        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        access_token = _get_access_token(api_key)
        path = _build_path(bucket_link, cloud_folder_path, key_or_filename)
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/content"
        headers = _get_headers(api_key)
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        access_token = _get_access_token(api_key)
        headers = _get_headers(api_key)
        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            path = _build_path(bucket_link, cloud_folder_path, name)
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/content"
            resp = requests.get(url, headers=headers, stream=True)
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
                        byte_callback({"delta": len(chunk), "sent": sent, "total": total, "index": idx, "filename": name, "path": path})
                    except Exception:
                        pass
                content = b"".join(parts)
            else:
                content = resp.content
            results.append({"filename": name, "content": content})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": path})
                except Exception:
                    pass
        return results


