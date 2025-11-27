from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict
from urllib.parse import urlparse

import dropbox
import requests

from ._logging import log_exceptions

TOKEN_ENDPOINT = "https://api.dropbox.com/oauth2/token"


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
    def _parse_credentials(api_key: str) -> Dict[str, Any]:
        key = (api_key or "").strip()
        if not key:
            raise ValueError("[SaveFileExtended:dropbox_client:_parse_credentials] Dropbox cloud_api_key is required")

        if key.startswith("{"):
            data = json.loads(key)
            # Support both app_* and client_* naming
            app_key = data.get("app_key") or data.get("client_id")
            app_secret = data.get("app_secret") or data.get("client_secret")
            refresh_token = data.get("refresh_token")
            access_token = data.get("access_token") or data.get("token")
            authorization_code = (
                data.get("authorization_code")
                or data.get("auth_code")
                or data.get("code")
                or data.get("access_code")
            )

            cached = None
            if app_key and app_secret:
                cached = Uploader._read_cached_tokens(app_key, app_secret)
                if not refresh_token and cached and cached.get("refresh_token"):
                    refresh_token = cached.get("refresh_token")
                    if not access_token:
                        access_token = cached.get("access_token")
                    print(
                        f"[SaveFileExtended:Dropbox] Using cached refresh token for app '{app_key}'.",
                        flush=True,
                    )

            if refresh_token and app_key and app_secret:
                return {
                    "refresh_token": refresh_token,
                    "app_key": app_key,
                    "app_secret": app_secret,
                    "access_token": access_token,
                }
            if authorization_code and app_key and app_secret:
                token_data = Uploader._token_request(
                    app_key,
                    app_secret,
                    {
                        "grant_type": "authorization_code",
                        "code": authorization_code,
                    },
                )
                new_refresh = token_data.get("refresh_token")
                if not new_refresh:
                    raise ValueError(
                        "[SaveFileExtended:dropbox_client] Dropbox did not return a refresh_token. "
                        "Ensure 'Allow offline access' is enabled for your app and that the authorization "
                        "code is unused."
                    )
                new_access = token_data.get("access_token")
                print(
                    "[SaveFileExtended:Dropbox] Generated refresh token from authorization code. "
                    "The refresh token has been cached automatically. You can remove the authorization_code "
                    "from your JSON as it's single-use. Future runs will use the cached refresh token.\n"
                    f'Refresh token (for reference): "{new_refresh}"',
                    flush=True,
                )
                result = {
                    "refresh_token": new_refresh,
                    "app_key": app_key,
                    "app_secret": app_secret,
                    "access_token": new_access,
                    "_generated_refresh_token": new_refresh,
                }
                Uploader._write_cached_tokens(app_key, app_secret, new_refresh, new_access)
                return result
            if access_token:
                return {"access_token": access_token}
            raise ValueError(
                "[SaveFileExtended:dropbox_client:_parse_credentials] When providing JSON, include either "
                "`authorization_code` + `app_key` + `app_secret` (preferred, automatically fetches refresh token), "
                "`refresh_token` + `app_key` + `app_secret`, or an `access_token`."
            )

        return {"access_token": key}


    @staticmethod
    @log_exceptions
    def _token_request(app_key: str, app_secret: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data=payload,
            auth=(app_key, app_secret),
            timeout=30,
        )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            error_desc = data.get("error_description") or data.get("error") or data
            raise ValueError(f"[SaveFileExtended:dropbox_client] Token endpoint error: {error_desc}")
        return data

    @staticmethod
    @log_exceptions
    def _cache_file() -> str:
        try:
            home = os.path.expanduser("~")
            if home and home != "~":
                base = os.path.join(home, ".cache", "comfyui-save-file-extended")
            else:
                raise ValueError
        except Exception:
            base = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".cache")
        return os.path.join(base, "dropbox_tokens.json")

    @staticmethod
    @log_exceptions
    def _cache_key(app_key: str, app_secret: str) -> str:
        raw = f"{app_key}:{app_secret}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    @log_exceptions
    def _read_cached_tokens(app_key: str, app_secret: str) -> Dict[str, Any] | None:
        path = Uploader._cache_file()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            print(f"[SaveFileExtended:Dropbox] Failed to read token cache: {exc}", flush=True)
            return None
        entry = data.get(Uploader._cache_key(app_key, app_secret))
        if isinstance(entry, dict):
            return entry
        return None

    @staticmethod
    @log_exceptions
    def _write_cached_tokens(app_key: str, app_secret: str, refresh_token: str, access_token: str | None):
        if not refresh_token:
            return
        path = Uploader._cache_file()
        cache_dir = os.path.dirname(path)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as exc:
            print(f"[SaveFileExtended:Dropbox] Unable to prepare cache directory '{cache_dir}': {exc}", flush=True)
            return

        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            else:
                data = {}
        except Exception:
            data = {}
        data[Uploader._cache_key(app_key, app_secret)] = {
            "app_key": app_key,
            "refresh_token": refresh_token,
            "access_token": access_token,
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            print(
                f"[SaveFileExtended:Dropbox] Cached refresh token for app '{app_key}' at {path}. "
                "Store securely if you plan to migrate machines.",
                flush=True,
            )
        except Exception as exc:
            print(f"[SaveFileExtended:Dropbox] Failed to write token cache '{path}': {exc}", flush=True)

    @staticmethod
    @log_exceptions
    def _get_dbx(api_key: str):
        creds = Uploader._parse_credentials(api_key)

        if "refresh_token" in creds:
            if not creds.get("access_token"):
                # Ensure we have a live access token so that downstream SDK calls succeed immediately.
                try:
                    token_data = Uploader._token_request(
                        creds["app_key"],
                        creds["app_secret"],
                        {
                            "grant_type": "refresh_token",
                            "refresh_token": creds["refresh_token"],
                        },
                    )
                    creds["access_token"] = token_data.get("access_token")
                    Uploader._write_cached_tokens(
                        creds["app_key"],
                        creds["app_secret"],
                        creds["refresh_token"],
                        creds.get("access_token"),
                    )
                except Exception as exc:
                    print(f"[SaveFileExtended:Dropbox] Refresh token exchange failed: {exc}", flush=True)
                    raise RuntimeError(
                        "[SaveFileExtended:dropbox_client] Unable to exchange Dropbox refresh token for a new "
                        "access token. Verify that app key/secret and refresh token are valid."
                    ) from exc

            if not creds.get("access_token"):
                raise RuntimeError(
                    "[SaveFileExtended:dropbox_client] Dropbox access token is missing after refresh. "
                    "Token exchange may have failed; please re-authorize your credentials."
                )

            dbx = dropbox.Dropbox(
                oauth2_access_token=creds.get("access_token"),
                oauth2_refresh_token=creds["refresh_token"],
                app_key=creds["app_key"],
                app_secret=creds["app_secret"],
            )
            # Ensure we have a fresh short-lived token before performing operations when supported.
            try:
                dbx.check_and_refresh_access_token()
            except AttributeError:
                # Older SDKs may not expose this helper; ignore in that case.
                pass
            generated = creds.get("_generated_refresh_token")
            if generated:
                setattr(dbx, "_savefileextended_generated_refresh_token", generated)
                setattr(dbx, "_savefileextended_generated_access_token", creds.get("access_token"))
            return dbx

        access_token = creds["access_token"]
        if not access_token:
            raise ValueError("[SaveFileExtended:dropbox_client:_get_dbx] Dropbox access token is required")
        return dropbox.Dropbox(access_token.strip())

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
