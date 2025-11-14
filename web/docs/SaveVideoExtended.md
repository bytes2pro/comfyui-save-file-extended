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
-   **filename (STRING, optional)**: Exact filename to use. If provided, this will be used directly (extension auto-appended if missing based on `format`). If empty, falls back to `custom_filename` or UUID-based generation. Include file extension.
-   **custom_filename (STRING, optional)**: Custom filename prefix (without extension). If provided and `filename` is empty, uses this with format-specific extension. If both are empty, uses UUID-based filename generation.
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
-   **Dropbox** → bucket_link: `/base/path` | cloud_api_key: JSON `{"app_key":"...","app_secret":"...","authorization_code":"..."}` (You can get the `app_key` and `app_secret` in the bucket settings. You can get authorization_code by going to `https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline`). Raw access tokens still work but expire after a few hours.
-   **OneDrive** → `/base/path` | API key: OAuth2 JSON or access token.
-   **FTP** → `ftp://user:pass@host[:port]/basepath` | API key: not used.
-   **Supabase Storage** → `<bucket_name>` | API key: `{"url":"https://...","key":"<JWT>"}` or `url|key`.
-   **UploadThing** → set `bucket_link` to UploadThing project name | API key: `sk_...`.

### Dropbox refresh-token setup

1. Create a Scoped App in the [Dropbox App Console](https://www.dropbox.com/developers/apps) and enable the scopes you need (e.g., `files.content.write` / `files.content.read`).
2. Enable offline access, then copy the **App key** and **App secret** from the app settings page.
3. Complete the one-time OAuth flow described in [FranklinThaker/Dropbox-API-Uninterrupted-Access](https://github.com/FranklinThaker/Dropbox-API-Uninterrupted-Access) with `token_access_type=offline`, then either paste the resulting `"authorization_code"` directly into your JSON or exchange it manually for a long-lived **refresh_token**.
4. On the first successful run with an `authorization_code`, the node requests Dropbox tokens on your behalf, prints the generated refresh/access tokens to the ComfyUI console, and continues the upload. Copy the refresh token into your JSON (optionally alongside `"access_token":"..."`) so subsequent runs no longer rely on the single-use code. The credentials are also cached at `~/.cache/comfyui-save-file-extended/dropbox_tokens.json` (fallback: within the module directory) for reuse when you only provide the app credentials.

### Token refresh (optional)

-   Dropbox: `{"app_key","app_secret","refresh_token","access_token"?, "authorization_code"?}` (authorization code is optional and only needed for the initial exchange).
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
