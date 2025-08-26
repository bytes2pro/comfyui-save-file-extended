from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

from . import (azure_blob, b2, dropbox_client, ftp_client, gcs, gdrive,
               onedrive, s3, s3_compatible, supabase_storage, upload_thing)


def get_uploader(provider_name: str):
    """
    Return an uploader class for the given provider name.

    Each uploader implements:
        upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]
    and returns a dict with at least {"provider": str, "path": str, "url": Optional[str]}.
    """
    providers: Dict[str, Any] = {
        "AWS S3": s3.Uploader,
        "S3-Compatible": s3_compatible.Uploader,
        "Google Cloud Storage": gcs.Uploader,
        "Azure Blob Storage": azure_blob.Uploader,
        "Backblaze B2": b2.Uploader,
        "Dropbox": dropbox_client.Uploader,
        "Google Drive": gdrive.Uploader,
        "OneDrive": onedrive.Uploader,
        "FTP": ftp_client.Uploader,
        "Supabase Storage": supabase_storage.Uploader,
        "UploadThing": upload_thing.Uploader,
    }

    uploader = providers.get(provider_name)
    if not uploader:
        raise ValueError(f"[SaveFileExtended:get_uploader] Unsupported cloud provider: {provider_name}")

    return uploader
