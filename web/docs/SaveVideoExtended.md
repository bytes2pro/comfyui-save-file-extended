## SaveVideoExtended

Save a video locally and/or upload it to a cloud provider in one step. Shows real-time progress in a floating status panel and emits events for toasts.

### How it works

-   **Local**: Renders the video to your ComfyUI output directory when "Save to Local" is enabled (optionally under `local_folder_path`).
-   **Cloud**: Uploads the rendered file to your selected provider when "Save to Cloud" is enabled.
-   **Output**: Returns standard UI image entry for the video plus a `cloud` array with provider upload info.

### Inputs

-   **video (VIDEO)**: The video to save.
-   **filename_prefix (STRING)**: Supports tokens like `%date:yyyy-MM-dd%` and node field tokens (e.g., `%Empty Latent Image.width%`).
-   **format (CHOICE)**: Container format (e.g., auto/mp4/webm/mkv).
-   **codec (CHOICE)**: Video codec (e.g., auto/h264/vp9/av1).
-   **save_to_cloud (BOOLEAN)**: Enable uploads to a provider.
-   **cloud_provider (CHOICE)**: AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase, UploadThing.
-   **bucket_link (STRING)**: Provider-specific destination identifier (examples below).
-   **cloud_folder_path (STRING)**: Destination folder/key prefix.
-   **cloud_api_key (STRING)**: Credentials; JSON or token depending on provider.
-   **save_to_local (BOOLEAN)**: Write a local copy.
-   **local_folder_path (STRING)**: Subfolder under the output directory; created if missing.

### Cloud providers and examples

-   **AWS S3** → `s3://bucket/prefix` | API key: JSON `{access_key, secret_key, region}` or `ACCESS:SECRET[:REGION]`.
-   **S3-Compatible** → `https://endpoint/bucket/prefix` | API key same as S3.
-   **Google Cloud Storage** → `gs://bucket/prefix` or `bucket/prefix` | API key: service-account JSON string or file path.
-   **Azure Blob** → connection string OR `https://account.blob.core.windows.net/container/prefix` | API key: connection string or account key/SAS.
-   **Backblaze B2** → `b2://bucket/prefix` or `bucket/prefix` | API key: `KEY_ID:APP_KEY`.
-   **Google Drive** → `/MyFolder/Sub` OR `drive://<folderId>/<sub>` OR a folder URL | API key: OAuth2 JSON or access token.
-   **Dropbox** → `/base/path` | API key: Dropbox access token.
-   **OneDrive** → `/base/path` | API key: OAuth2 JSON or access token.
-   **FTP** → `ftp://user:pass@host[:port]/basepath` | API key: not used.
-   **Supabase Storage** → `<bucket_name>` | API key: `{"url":"https://...","key":"<JWT>"}` or `url|key`.
-   **UploadThing** → set `bucket_link` to UploadThing project name | API key: `sk_...`.

### Token refresh (optional)

-   Google Drive: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive: `{client_id, client_secret, refresh_token, tenant, redirect_uri?}`.

When provided, the node refreshes the access token before uploading.

### Metadata

If ComfyUI metadata is enabled, prompt and `extra_pnginfo` are embedded when supported by the container.

### UI and events

-   Progress panel listens to `comfyui.savevideoextended.status` for start/progress/complete/error.
-   Toast notifications are shown for start/error/complete.

### Returns

-   `ui.images`: The saved file for gallery preview (with `animated: (True,)`).
-   `cloud`: Provider upload results.
