from __future__ import annotations

from typing import Any, Dict, Tuple
from urllib.parse import urlparse


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
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        account_url, container, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, filename)

        if "DefaultEndpointsProtocol=" in bucket_link:
            # Connection string provided as bucket_link
            service_client = BlobServiceClient.from_connection_string(bucket_link)
        elif api_key and api_key.strip().startswith("DefaultEndpointsProtocol="):
            # Connection string provided in api_key
            service_client = BlobServiceClient.from_connection_string(api_key.strip())
        else:
            if not account_url:
                raise ValueError("Azure Blob requires an account URL or connection string")
            service_client = BlobServiceClient(account_url=account_url, credential=api_key if api_key else None)

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
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        account_url, container, _ = _parse_container_and_blob(bucket_link, cloud_folder_path, "dummy")

        if "DefaultEndpointsProtocol=" in bucket_link:
            service_client = BlobServiceClient.from_connection_string(bucket_link)
        elif api_key and api_key.strip().startswith("DefaultEndpointsProtocol="):
            service_client = BlobServiceClient.from_connection_string(api_key.strip())
        else:
            if not account_url:
                raise ValueError("Azure Blob requires an account URL or connection string")
            service_client = BlobServiceClient(account_url=account_url, credential=api_key if api_key else None)

        container_client = service_client.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            _, _, blob_name = _parse_container_and_blob(bucket_link, cloud_folder_path, filename)
            blob_client = container_client.get_blob_client(blob_name)
            content_settings = ContentSettings(content_type="image/png")
            blob_client.upload_blob(body, overwrite=True, content_settings=content_settings)
            url = f"{service_client.url}/{container}/{blob_name}"
            results.append({"provider": "Azure Blob Storage", "bucket": container, "path": blob_name, "url": url})

        return results


