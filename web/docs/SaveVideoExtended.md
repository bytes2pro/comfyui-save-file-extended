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
-   **Dropbox** → bucket_link: `/base/path` | cloud_api_key: JSON `{"app_key":"...","app_secret":"...","authorization_code":"..."}`. Get `app_key` and `app_secret` from app settings. Get authorization_code from `https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline`.
-   **OneDrive** → `/base/path` | API key: OAuth2 JSON or access token.
-   **FTP** → `ftp://user:pass@host[:port]/basepath` | API key: not used.
-   **Supabase Storage** → `<bucket_name>` | API key: `{"url":"https://...","key":"<JWT>"}` or `url|key`.
-   **UploadThing** → set `bucket_link` to UploadThing project name | API key: `sk_...`.

### Dropbox setup

1. Create a Scoped App in the [Dropbox App Console](https://www.dropbox.com/developers/apps):
   - Click "Create app"
   - Choose "Scoped access" → "Full Dropbox" or "App folder"
   - Name your app and click "Create app"
2. Get your **App key** and **App secret**:
   - In your app's dashboard, go to the **Settings** tab
   - Scroll to "OAuth 2" section
   - You'll see **App key** (also called "App ID") - copy this value
   - Click "Show" next to **App secret** - copy this value
   - Ensure "Allow offline access" is enabled (this is required for refresh tokens)
3. Get the authorization code:
   - Visit `https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline` (replace `{APP_KEY}` with your app key)
   - Authorize the app and copy the authorization code from the redirect URL
4. Paste the JSON with `app_key`, `app_secret`, and `authorization_code` into `cloud_api_key`

### Token refresh (optional)

-   Dropbox: `{"app_key","app_secret","authorization_code"}`
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
