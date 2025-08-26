# Load Image Extended

Load images from your local input directory or directly from supported cloud providers. Shows real-time per-item and byte-level progress in the UI where available.

## How it works

-   Local: Reads files from the ComfyUI input directory; supports subfolders.
-   Cloud: Downloads keys/filenames under the configured bucket/container/folder.

## UI tips

-   The node UI shows a "Cloud" section only when the cloud toggle is enabled.
-   A floating "Save/Load Status" panel displays progress during downloads.

## Inputs

-   load_from_cloud (BOOLEAN): Toggle between local and cloud sources.
-   file_paths (STRING, multiline): One path per line. For local, paths are relative to the input directory; for cloud, keys are resolved under the configured prefix.
-   cloud_provider (CHOICE): One of AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase.
-   bucket_link (STRING): Provider-specific origin identifier (see examples below).
-   cloud_folder_path (STRING): Optional folder/key prefix. Keys in `file_paths` will be resolved under this prefix.
-   cloud_api_key (STRING): Credentials; supports tokens and JSON; see token refresh below.

## Provider examples

-   AWS S3 → bucket_link: `s3://my-bucket/prefix`.
-   S3-Compatible → bucket_link: `https://endpoint.example.com/my-bucket/prefix`.
-   Google Cloud Storage → bucket_link: `gs://bucket/prefix` or `bucket/prefix`.
-   Azure Blob → bucket_link: connection string OR `https://account.blob.core.windows.net/container/prefix`.
-   Backblaze B2 → bucket_link: `b2://bucket/prefix` or `bucket/prefix`.
-   Google Drive → bucket_link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>`.
-   Dropbox → bucket_link: `/base/path`.
-   OneDrive → bucket_link: `/base/path`.
-   FTP → bucket_link: `ftp://user:pass@host[:port]/basepath`.
-   Supabase → bucket_link: `<bucket_name>`.

## Token refresh (optional)

-   Google Drive cloud_api_key JSON: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive cloud_api_key JSON: `{client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}`.

When provided, the node automatically exchanges the refresh token for a fresh access token before downloading.

## Returns

-   IMAGE (Tensor): Loaded image batch.
-   MASK (Tensor): Associated alpha or inferred mask batch.

## Notes

-   Downloads stream in chunks when supported; the UI shows cumulative bytes and item progress.
-   If shape differs across images, only the first image/mask is returned as a single batch entry.
