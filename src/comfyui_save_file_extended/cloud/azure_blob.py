from __future__ import annotations

import base64
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from azure.storage.blob import BlobServiceClient, ContentSettings


def _parse_container_and_blob(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str, str]:
    """
    Accept:
      - Connection string (will be handled by SDK): use container from cloud_folder_path/bucket_link? Not available -> require container in URL form
      - URL: https://<account>.blob.core.windows.net/<container>[/prefix]
    Returns (account_url, container, blob_name)
    """
    parsed = urlparse(bucket_link)
    if parsed.scheme.startswith("http"):
        account_url = f"{parsed.scheme}://{parsed.netloc}"
        path_parts = parsed.path.lstrip("/").split("/", 1)
        container = path_parts[0]
        base_prefix = path_parts[1] if len(path_parts) > 1 else ""
    else:
        # Treat bucket_link as container name
        account_url = ""
        container = bucket_link.strip().split("/")[0]
        base_prefix = "/".join(bucket_link.strip().split("/")[1:])

    parts = [p for p in [base_prefix, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p.strip("/")])
    blob_name = f"{prefix + '/' if prefix else ''}{filename}"
    return account_url, container, blob_name


class Uploader:
    @staticmethod
    def _create_service_client(bucket_link: str, api_key: str, account_url: str) -> Any:
        if "DefaultEndpointsProtocol=" in bucket_link:
            return BlobServiceClient.from_connection_string(bucket_link)
        elif api_key and api_key.strip().startswith("DefaultEndpointsProtocol="):
            return BlobServiceClient.from_connection_string(api_key.strip())
        else:
            if not account_url:
                raise ValueError("Azure Blob requires an account URL or connection string")
            return BlobServiceClient(account_url=account_url, credential=api_key if api_key else None)
    
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        account_url, container, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, filename)

        service_client = Uploader._create_service_client(bucket_link, api_key, account_url)

        container_client = service_client.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass

        blob_client = container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type="image/png")
        blob_client.upload_blob(image_bytes, overwrite=True, content_settings=content_settings)

        url = f"{service_client.url}/{container}/{blob_name}"
        return {
            "provider": "Azure Blob Storage",
            "bucket": container,
            "path": blob_name,
            "url": url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]:
        account_url, container, _ = _parse_container_and_blob(bucket_link, cloud_folder_path, "dummy")

        service_client = Uploader._create_service_client(bucket_link, api_key, account_url)

        container_client = service_client.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass

        results: list[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            filename = item["filename"]
            body = item["content"]
            _, _, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, filename)
            blob_client = container_client.get_blob_client(blob_name)
            content_settings = ContentSettings(content_type="image/png")
            if byte_callback and len(body) > 8 * 1024 * 1024:
                # staged blocks
                block_ids = []
                chunk_size = 8 * 1024 * 1024
                for bi in range(0, len(body), chunk_size):
                    chunk = body[bi:bi+chunk_size]
                    block_id = base64.b64encode(f"block-{idx}-{bi}".encode()).decode()
                    blob_client.stage_block(block_id=block_id, data=chunk)
                    block_ids.append(block_id)
                    try:
                        byte_callback({"delta": len(chunk), "sent": bi + len(chunk), "total": len(body), "index": idx, "filename": filename, "path": blob_name})
                    except Exception:
                        pass
                blob_client.commit_block_list(block_ids, content_settings=content_settings)
            else:
                blob_client.upload_blob(body, overwrite=True, content_settings=content_settings)
            url = f"{service_client.url}/{container}/{blob_name}"
            results.append({"provider": "Azure Blob Storage", "bucket": container, "path": blob_name, "url": url})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": filename, "path": blob_name})
                except Exception:
                    pass

        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        account_url, container, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, key_or_filename)

        service_client = Uploader._create_service_client(bucket_link, api_key, account_url)

        blob_client = service_client.get_blob_client(container=container, blob=blob_name)
        downloader = blob_client.download_blob()
        return downloader.readall()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str, progress_callback=None, byte_callback=None) -> list[Dict[str, Any]]: # type: ignore
        account_url, container, _ = _parse_container_and_blob(bucket_link, cloud_folder_path, "dummy")

        if "DefaultEndpointsProtocol=" in bucket_link:
            service_client = BlobServiceClient.from_connection_string(bucket_link)
        elif api_key and api_key.strip().startswith("DefaultEndpointsProtocol="):
            service_client = BlobServiceClient.from_connection_string(api_key.strip())
        else:
            if not account_url:
                raise ValueError("Azure Blob requires an account URL or connection string")
            service_client = BlobServiceClient(account_url=account_url, credential=api_key if api_key else None)

        results: list[Dict[str, Any]] = []
        for idx, name in enumerate(keys):
            _, _, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, name)
            blob_client = service_client.get_blob_client(container=container, blob=blob_name)
            downloader = blob_client.download_blob()
            if byte_callback:
                parts = []
                sent = 0
                for data in downloader.chunks():
                    parts.append(data)
                    sent += len(data)
                    try:
                        byte_callback({"delta": len(data), "sent": sent, "total": downloader.size, "index": idx, "filename": name, "path": blob_name})
                    except Exception:
                        pass
                content = b"".join(parts)
            else:
                content = downloader.readall()
            results.append({"filename": name, "content": content})
            if progress_callback:
                try:
                    progress_callback({"index": idx, "filename": name, "path": blob_name})
                except Exception:
                    pass
        return results