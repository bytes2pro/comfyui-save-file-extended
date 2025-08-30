from __future__ import annotations

import asyncio
import io
import json
import threading
from typing import Any, Dict, List, Tuple
from urllib.request import Request, urlopen

from ._logging import log_exceptions
import mimetypes

import requests

try:  # Unofficial Python SDK for UploadThing
    # https://pypi.org/project/uploadthing.py/
    from uploadthing_py import UTApi  # type: ignore
except Exception:  # pragma: no cover
    UTApi = None  # type: ignore


class NamedBytesIO(io.BytesIO):
    """
    A BytesIO subclass that supports a "name" attribute. Some SDKs expect
    file-like objects to expose a filename via a .name attribute.
    """

    def __init__(self, initial_bytes: bytes, name: str) -> None:
        super().__init__(initial_bytes)
        self.name = name


@log_exceptions
def _parse_secret(api_key: str) -> str:
    """
    Accept either a raw UploadThing secret (sk_...) or a JSON string like
    {"secret": "sk_..."} / {"api_key": "sk_..."} / {"key": "sk_..."}.
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("[SaveFileExtended:uploadthing:_parse_secret] cloud_api_key is required (UploadThing secret key, e.g. 'sk_...')")
    if key.startswith("{"):
        data = json.loads(key)
        for k in ("secret", "api_key", "key"):
            if data.get(k):
                return str(data[k])
        raise ValueError("[SaveFileExtended:uploadthing:_parse_secret] JSON must include one of 'secret'|'api_key'|'key'")
    return key


@log_exceptions
def _name_with_prefix(filename: str, cloud_folder_path: str) -> str:
    prefix = (cloud_folder_path or "").strip().strip("/")
    return f"{prefix}/{filename}" if prefix else filename


@log_exceptions
def _run_async(coro):
    """
    Run an async coroutine from sync context. If an event loop is already
    running (e.g., inside certain environments), execute it in a worker thread.
    """
    # If there is no running loop, use asyncio.run directly
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Otherwise, execute the coroutine in a dedicated event loop on a worker thread
    result: Dict[str, Any] = {}

    def _target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["value"] = loop.run_until_complete(coro)
        finally:
            loop.close()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    return result.get("value")


@log_exceptions
def _http_download(url: str, byte_callback=None) -> bytes:
    req = Request(url, headers={"User-Agent": "ComfyUI-SaveFileExtended/UploadThing"})
    with urlopen(req) as resp:  # nosec - user supplied URL expected for utfs.io
        total = resp.length
        chunks: List[bytes] = []
        sent = 0
        while True:
            data = resp.read(8 * 1024 * 1024)
            if not data:
                break
            chunks.append(data)
            sent += len(data)
            if byte_callback:
                try:
                    byte_callback({"delta": len(data), "sent": sent, "total": total})
                except Exception:
                    pass
        return b"".join(chunks)


_UT_API_BASE = "https://api.uploadthing.com"


def _ut_headers(api_key: str) -> Dict[str, str]:
    secret = _parse_secret(api_key)
    return {
        "X-Uploadthing-Api-Key": secret,
        "Content-Type": "application/json",
        "User-Agent": "ComfyUI-SaveFileExtended/UploadThing",
    }


def _ut_presign(files: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
    """
    Request presigned upload targets for one or more files.
    Each file dict must include: name, size, content_type.
    Tries v7 then v6 per UploadThing REST API.
    See: https://docs.uploadthing.com/api-reference/openapi-spec
    """
    payload = {
        "files": [
            {
                "name": f["name"],
                "contentType": f["content_type"],  # v7
                "type": f["content_type"],  # compatibility
                "size": f["size"],
            }
            for f in files
        ]
    }
    headers = _ut_headers(api_key)
    timeout = (10, 60)

    # Try v7 first
    url = f"{_UT_API_BASE}/v7/uploadFiles"
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code == 404:
        # Fallback to v6
        url = f"{_UT_API_BASE}/v6/uploadFiles"
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    res_list = data.get("data", data)
    if not isinstance(res_list, list):
        raise RuntimeError("[SaveFileExtended:uploadthing] Unexpected response from presign endpoint")
    return res_list


def _ut_put(upload_url: str, body: bytes, headers: Dict[str, Any]) -> None:
    req_headers = {str(k): str(v) for k, v in (headers or {}).items()}
    if "Content-Length" not in {k.title(): v for k, v in req_headers.items()}:
        req_headers["Content-Length"] = str(len(body))
    timeout = (10, max(60, len(body) // (256 * 1024)))
    r = requests.put(upload_url, data=body, headers=req_headers, timeout=timeout)
    r.raise_for_status()


def _ut_post_multipart(post_url: str, fields: Dict[str, Any], file_tuple: Tuple[str, bytes, str]) -> None:
    files = {"file": file_tuple}
    r = requests.post(post_url, data=fields or {}, files=files, timeout=(10, 120))
    r.raise_for_status()


def _ut_resolve_urls(keys: List[str], api_key: str) -> Dict[str, str]:
    if not keys:
        return {}
    headers = _ut_headers(api_key)
    payload = {"fileKeys": keys}
    for ver in ("v7", "v6"):
        try:
            url = f"{_UT_API_BASE}/{ver}/getFileUrls"
            resp = requests.post(url, json=payload, headers=headers, timeout=(10, 30))
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json().get("data")
            out: Dict[str, str] = {}
            if isinstance(data, list):
                for i, key in enumerate(keys):
                    item = data[i] if i < len(data) else None
                    if isinstance(item, dict) and item.get("url"):
                        out[key] = str(item["url"])  # type: ignore[index]
            return out
        except Exception:
            continue
    return {}


class Uploader:
    @staticmethod
    @log_exceptions
    def _get_client(api_key: str):
        if UTApi is None:
            raise ImportError("uploadthing.py is required for UploadThing provider. Install with: pip install uploadthing.py")
        secret = _parse_secret(api_key)
        return UTApi(secret)

    @staticmethod
    @log_exceptions
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        name = _name_with_prefix(filename, cloud_folder_path)
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        presigned = _ut_presign([{"name": name, "size": len(image_bytes), "content_type": content_type}], api_key)
        item = presigned[0] if presigned and isinstance(presigned[0], dict) else {}

        key = item.get("key") or item.get("fileKey")
        url = item.get("fileUrl") or item.get("url")

        # Two possible flows: PUT or POST multipart depending on response shape
        if item.get("uploadUrl"):
            headers = item.get("headers") or {}
            if "Content-Type" not in headers:
                headers["Content-Type"] = content_type
            _ut_put(str(item["uploadUrl"]), image_bytes, headers)
        elif item.get("url") and item.get("fields"):
            _ut_post_multipart(str(item["url"]), item.get("fields") or {}, (name, image_bytes, content_type))

        if not url and key:
            url = f"https://utfs.io/f/{key}"

        return {"provider": "UploadThing", "path": key or name, "url": url}

    @staticmethod
    @log_exceptions
    def upload_many(
        items: List[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None
    ) -> List[Dict[str, Any]]:
        # Prepare metadata for presign
        meta: List[Dict[str, Any]] = []
        for it in items:
            name = _name_with_prefix(it["filename"], cloud_folder_path)
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            meta.append({"name": name, "size": len(it["content"]), "content_type": content_type})

        presigned = _ut_presign(meta, api_key)
        results: List[Dict[str, Any]] = []

        for idx, it in enumerate(items):
            name = meta[idx]["name"] if idx < len(meta) else _name_with_prefix(it["filename"], cloud_folder_path)
            content_type = meta[idx]["content_type"] if idx < len(meta) else (mimetypes.guess_type(name)[0] or "application/octet-stream")
            body = it["content"]

            item = presigned[idx] if idx < len(presigned) and isinstance(presigned[idx], dict) else {}
            key = item.get("key") or item.get("fileKey")
            url = item.get("fileUrl") or item.get("url")

            if item.get("uploadUrl"):
                headers = item.get("headers") or {}
                if "Content-Type" not in headers:
                    headers["Content-Type"] = content_type
                _ut_put(str(item["uploadUrl"]), body, headers)
            elif item.get("url") and item.get("fields"):
                _ut_post_multipart(str(item["url"]), item.get("fields") or {}, (name, body, content_type))

            if not url and key:
                url = f"https://utfs.io/f/{key}"

            results.append({"provider": "UploadThing", "path": key or it["filename"], "url": url})

            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": it["filename"], "path": key or it["filename"]})
                except Exception:
                    pass
            if byte_callback:
                try:
                    byte_callback(
                        {
                            "delta": len(body),
                            "sent": len(body),
                            "total": len(body),
                            "index": idx,
                            "filename": it["filename"],
                            "path": key or it["filename"],
                        }
                    )
                except Exception:
                    pass

        return results

    @staticmethod
    @log_exceptions
    def download(key_or_url: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        key_or_url = (key_or_url or "").strip()
        # If a full URL is provided, just fetch it
        if key_or_url.startswith("http://") or key_or_url.startswith("https://"):
            return _http_download(key_or_url)

        # Otherwise treat it as an UploadThing file key and resolve to URL
        url = None
        if api_key:
            resolved = _ut_resolve_urls([key_or_url], api_key)
            url = resolved.get(key_or_url)

        # Fallback to public CDN pattern
        if not url:
            url = f"https://utfs.io/f/{key_or_url}"

        return _http_download(url)

    @staticmethod
    @log_exceptions
    def download_many(
        keys: List[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # Attempt to resolve URLs in one go if keys are not URLs already
        to_resolve: List[str] = [k for k in keys if not (k.startswith("http://") or k.startswith("https://"))]
        resolved: Dict[str, str] = _ut_resolve_urls(to_resolve, api_key) if to_resolve and api_key else {}

        for idx, name in enumerate(keys):
            url = name
            if not (name.startswith("http://") or name.startswith("https://")):
                url = resolved.get(name) or f"https://utfs.io/f/{name}"
            data = _http_download(url, (lambda info: byte_callback({**info, "index": idx, "filename": name}) if byte_callback else None))
            results.append({"filename": name, "content": data})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": name})
                except Exception:
                    pass
        return results
