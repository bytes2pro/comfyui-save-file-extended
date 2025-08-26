# Save Image Extended

Save images locally and/or upload them to a cloud provider in one batch. Shows real-time per-file and byte-level progress in the UI.

## How it works
- Local: Writes PNG files under the ComfyUI output directory when "Save to Local" is enabled.
- Cloud: Uploads the batch to your selected provider when "Save to Cloud" is enabled.
- Output: The node returns standard UI image results for local saves and a `cloud` array with upload info.

## UI tips
- The node UI separates "Cloud" and "Local" sections with headers and dividers.
- Each section only appears when its toggle is enabled.
- A floating "Save/Load Status" panel displays progress.

## Inputs
- images (IMAGE): Image tensor batch to save.
- filename_prefix (STRING): The file prefix; supports tokens like `%date:yyyy-MM-dd%` and node field tokens (e.g. `%Empty Latent Image.width%`).
- save_to_cloud (BOOLEAN): Enable the cloud section and uploads.
- cloud_provider (CHOICE): One of AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase.
- bucket_link (STRING): Provider-specific destination identifier (see examples).
- cloud_folder_path (STRING): Folder/key prefix under the destination; created when applicable.
- cloud_api_key (STRING): Credentials; supports tokens and JSON; see token refresh below.
- save_to_local (BOOLEAN): Enable local output writes.
- local_folder_path (STRING): Subfolder under the ComfyUI output directory; created if missing.

## Provider examples
- AWS S3 → bucket_link: `s3://my-bucket/prefix` | cloud_api_key: JSON `{access_key, secret_key, region}` or `ACCESS:SECRET[:REGION]`.
- S3-Compatible → bucket_link: `https://endpoint.example.com/my-bucket/prefix` | cloud_api_key: same as S3.
- Google Cloud Storage → bucket_link: `gs://bucket/prefix` or `bucket/prefix` | cloud_api_key: service-account JSON string or file path (empty uses ADC).
- Azure Blob → bucket_link: connection string OR `https://account.blob.core.windows.net/container/prefix` | cloud_api_key: connection string or account key/SAS when using URL.
- Backblaze B2 → bucket_link: `b2://bucket/prefix` or `bucket/prefix` | cloud_api_key: `KEY_ID:APP_KEY`.
- Google Drive → bucket_link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>` | cloud_api_key: OAuth2 token or refresh JSON.
- Dropbox → bucket_link: `/base/path` | cloud_api_key: access token.
- OneDrive → bucket_link: `/base/path` | cloud_api_key: OAuth2 token or refresh JSON.
- FTP → bucket_link: `ftp://user:pass@host[:port]/basepath` | cloud_api_key: not used.
- Supabase → bucket_link: `<bucket_name>` | cloud_api_key: JSON `{url, key}` or `url|key`.

## Token refresh (optional)
- Google Drive cloud_api_key JSON: `{client_id, client_secret, refresh_token}` (optional `access_token`).
- OneDrive cloud_api_key JSON: `{client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}`.

When provided, the node automatically exchanges the refresh token for a fresh access token before uploading.

## Returns
- ui.images: The files saved locally, for standard gallery previews.
- cloud: A list of objects (provider, path, url where available) for cloud uploads.

## Notes
- Uploads and downloads stream in chunks when supported; the UI shows cumulative bytes and item progress.
- If both Local and Cloud are enabled, files will be saved locally and uploaded.
