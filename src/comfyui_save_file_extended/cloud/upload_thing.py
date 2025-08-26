from __future__ import annotations

import asyncio
import io
import json
import threading
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ._logging import log_exceptions

try:  # Unofficial Python SDK for UploadThing
    # https://pypi.org/project/uploadthing.py/
    from uploadthing_py import UTApi  # type: ignore
except Exception:  # pragma: no cover
    UTApi = None  # type: ignore


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
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "already running" not in str(e):
            raise
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
        client = Uploader._get_client(api_key)
        name = _name_with_prefix(filename, cloud_folder_path)

        async def _do() -> Dict[str, Any]:
            # Many Python HTTP clients accept file-like objects with a name attribute
            f = io.BytesIO(image_bytes)
            f.name = name  # type: ignore[attr-defined]
            try:
                res = await client.upload_files([f])  # type: ignore[attr-defined]
            except TypeError:
                # Fallback to bytes payload if the SDK expects dicts
                res = await client.upload_files([{"name": name, "data": image_bytes, "content_type": "image/png"}])  # type: ignore[list-item]
            item = res[0] if isinstance(res, list) else res
            # Expected shape from SDK: { key: str, url: str, ... }
            key = item.get("key") if isinstance(item, dict) else None
            url = item.get("url") if isinstance(item, dict) else None
            if not url and key:
                # Public CDN shortcut used by UploadThing
                url = f"https://utfs.io/f/{key}"
            return {"provider": "UploadThing", "path": key or name, "url": url}

        return _run_async(_do())

    @staticmethod
    @log_exceptions
    def upload_many(items: List[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> List[Dict[str, Any]]:
        client = Uploader._get_client(api_key)

        async def _do() -> List[Dict[str, Any]]:
            files: List[Any] = []
            for item in items:
                name = _name_with_prefix(item["filename"], cloud_folder_path)
                f = io.BytesIO(item["content"])
                f.name = name  # type: ignore[attr-defined]
                files.append(f)
            results: List[Dict[str, Any]] = []
            try:
                resp = await client.upload_files(files)  # type: ignore[attr-defined]
                # Normalize to list of dicts
                if not isinstance(resp, list):
                    resp = [resp]
                for idx, item in enumerate(resp):
                    key = item.get("key") if isinstance(item, dict) else None
                    url = item.get("url") if isinstance(item, dict) else None
                    if not url and key:
                        url = f"https://utfs.io/f/{key}"
                    results.append({"provider": "UploadThing", "path": key or items[idx]["filename"], "url": url})
                    if progress_callback:
                        try:
                            progress_callback({"index": idx, "filename": items[idx]["filename"], "path": key or items[idx]["filename"]})
                        except Exception:
                            pass
                    if byte_callback:
                        try:
                            body = items[idx]["content"]
                            byte_callback({"delta": len(body), "sent": len(body), "total": len(body), "index": idx, "filename": items[idx]["filename"], "path": key or items[idx]["filename"]})
                        except Exception:
                            pass
            except TypeError:
                # Fallback to one-by-one
                for idx, it in enumerate(items):
                    single = await client.upload_files([{"name": _name_with_prefix(it["filename"], cloud_folder_path), "data": it["content"], "content_type": "image/png"}])  # type: ignore[list-item]
                    item = single[0] if isinstance(single, list) else single
                    key = item.get("key") if isinstance(item, dict) else None
                    url = item.get("url") if isinstance(item, dict) else None
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
                            byte_callback({"delta": len(it["content"]), "sent": len(it["content"]), "total": len(it["content"]), "index": idx, "filename": it["filename"], "path": key or it["filename"]})
                        except Exception:
                            pass
            return results

        return _run_async(_do())

    @staticmethod
    @log_exceptions
    def download(key_or_url: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        key_or_url = (key_or_url or "").strip()
        # If a full URL is provided, just fetch it
        if key_or_url.startswith("http://") or key_or_url.startswith("https://"):
            return _http_download(key_or_url)

        # Otherwise treat it as an UploadThing file key and resolve to URL
        url = None
        if UTApi is not None and api_key:
            client = Uploader._get_client(api_key)

            async def _do_one() -> str | None:
                try:
                    # Prefer explicit lookup if available
                    if hasattr(client, "get_file_urls"):
                        res = await client.get_file_urls([key_or_url])  # type: ignore[attr-defined]
                        if isinstance(res, list) and res and isinstance(res[0], dict):
                            return res[0].get("url")
                except Exception:
                    return None
                return None

            url = _run_async(_do_one())

        # Fallback to public CDN pattern
        if not url:
            url = f"https://utfs.io/f/{key_or_url}"

        return _http_download(url)

    @staticmethod
    @log_exceptions
    def download_many(keys: List[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # Attempt to resolve URLs in one go if SDK supports it and keys are not URLs already
        to_resolve: List[str] = [k for k in keys if not (k.startswith("http://") or k.startswith("https://"))]
        resolved: Dict[str, str] = {}

        if UTApi is not None and to_resolve and api_key:
            client = Uploader._get_client(api_key)

            async def _do_many() -> Dict[str, str]:
                out: Dict[str, str] = {}
                try:
                    if hasattr(client, "get_file_urls"):
                        res = await client.get_file_urls(to_resolve)  # type: ignore[attr-defined]
                        if isinstance(res, list):
                            for i, key in enumerate(to_resolve):
                                item = res[i] if i < len(res) else None
                                if isinstance(item, dict) and item.get("url"):
                                    out[key] = str(item["url"])  # type: ignore[index]
                except Exception:
                    return out
                return out

            resolved = _run_async(_do_many()) or {}

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


