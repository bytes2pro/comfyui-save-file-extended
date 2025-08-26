from __future__ import annotations

from typing import Dict


def get_uploader(provider_name: str):
    """
    Return an uploader class for the given provider name.

    Each uploader implements:
        upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]
    and returns a dict with at least {"provider": str, "path": str, "url": Optional[str]}.
    """
    providers: Dict[str, str] = {
        "AWS S3": ".s3:Uploader",
        "S3-Compatible": ".s3_compatible:Uploader",
        "Google Cloud Storage": ".gcs:Uploader",
        "Azure Blob Storage": ".azure_blob:Uploader",
        "Backblaze B2": ".b2:Uploader",
        "Dropbox": ".dropbox_client:Uploader",
        "Google Drive": ".gdrive:Uploader",
        "OneDrive": ".onedrive:Uploader",
        "FTP": ".ftp_client:Uploader",
        "Supabase Storage": ".supabase_storage:Uploader",
    }

    dotted = providers.get(provider_name)
    if not dotted:
        raise ValueError(f"Unsupported cloud provider: {provider_name}")

    module_path, class_name = dotted.split(":")
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)
