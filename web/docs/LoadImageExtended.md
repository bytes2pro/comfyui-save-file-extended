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
-   local_file (DROPDOWN): When Cloud is OFF, you can pick a local image (with upload support) just like the core LoadImage node.
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
-   Google Drive → bucket_link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>` OR a folder URL like `https://drive.google.com/drive/folders/<folderId>`.
-   Dropbox → bucket_link: `/base/path` | cloud_api_key: JSON `{"app_key":"...","app_secret":"...","authorization_code":"..."}` (You can get the `app_key` and `app_secret` in the bucket settings. You can get authorization_code by going to `https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code&token_access_type=offline`). Legacy access tokens still work but expire after ~4 hours.
-   OneDrive → bucket_link: `/base/path`.
-   FTP → bucket_link: `ftp://user:pass@host[:port]/basepath`.
-   Supabase → bucket_link: `<bucket_name>`.
-   UploadThing → bucket_link: Project Name. Use UploadThing file keys or full utfs.io URLs.

## Getting provider values (URLs, bucket links, keys)

### Local (when Cloud is OFF)

-   Use the Local File dropdown to pick from the ComfyUI input directory, or upload directly. You can also type multiple names in file_paths.

### AWS S3

-   Bucket link: `s3://<bucket>[/prefix]`
-   API key: JSON `{"access_key","secret_key","region"}` or `ACCESS:SECRET[:REGION]`

### S3-Compatible (MinIO, Cloudflare R2, etc.)

-   Bucket link: `https://<endpoint>/<bucket>[/prefix]`
-   API key: same as S3

### Google Cloud Storage (GCS)

-   Bucket link: `gs://<bucket>[/prefix]` or `<bucket>[/prefix]`
-   API key: service-account JSON string or path to the JSON file

### Azure Blob Storage

-   Bucket link: connection string OR `https://<account>.blob.core.windows.net/<container>[/prefix]`
-   API key: connection string or account key/SAS when using URL

### Backblaze B2

-   Bucket link: `b2://<bucket>[/prefix]` or `<bucket>[/prefix]`
-   API key: `KEY_ID:APP_KEY`

### Google Drive

-   Bucket link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>` OR `https://drive.google.com/drive/folders/<folderId>`
-   Behavior: When using `drive://<folderId>` (or a Drive folder URL), any `cloud_folder_path` and any extra subpath in the bucket link are resolved relative to that folder ID (not root).
-   API key: OAuth2 JSON `{"client_id","client_secret","refresh_token"}` (optional `access_token`) or a raw OAuth2 access token string

### Dropbox

-   Bucket link: `/base/path` (include subfolders as needed, e.g., `/MyApp/Inputs`).
-   API key: JSON string `{"app_key":"APP_KEY","app_secret":"APP_SECRET","refresh_token":"REFRESH_TOKEN","access_token":"OPTIONAL"}`. For your first run you can supply an `"authorization_code"` instead of `"refresh_token"` and the node will exchange it automatically. Paste the entire JSON into `cloud_api_key`.
-   Setup steps:
    1. Create a Scoped App in the [Dropbox App Console](https://www.dropbox.com/developers/apps) with the scopes you need to read files.
    2. Enable offline access and copy your **App key** and **App secret**.
    3. Complete the one-time authorization flow described in [FranklinThaker/Dropbox-API-Uninterrupted-Access](https://github.com/FranklinThaker/Dropbox-API-Uninterrupted-Access) using `token_access_type=offline`, then either paste that `"authorization_code"` directly into your JSON or exchange it manually for a long-lived **refresh_token**.
    4. On the first successful run with an `authorization_code`, the node calls Dropbox's token endpoint, prints the generated refresh/access tokens to the ComfyUI console, and continues the download. Copy the refresh token into your JSON so future runs no longer require the single-use code. The credentials are also cached at `~/.cache/comfyui-save-file-extended/dropbox_tokens.json` (fallback: within the module directory) so later runs can reuse them when only app credentials are provided.
-   Legacy option: Paste a raw access token. Dropbox now expires them after roughly 4 hours, so plan to renew it frequently if you choose this path.

### OneDrive

-   Bucket link: `/base/path`
-   API key: OAuth2 JSON `{"client_id","client_secret","refresh_token","tenant":"common|consumers|organizations","redirect_uri"?}` or an access token

### FTP

-   Bucket link: `ftp://user:pass@host[:port]/basepath`
-   API key: not used

### Supabase Storage

-   Bucket link: `<bucket_name>`
-   API key: `{"url":"https://<project>.supabase.co","key":"<JWT>"}` or `https://<project>.supabase.co|<JWT>`
-   For writes (in SaveImageExtended) anon keys require RLS policies; downloads may require a SELECT policy or a public bucket.

### UploadThing

-   Bucket link: Project Name
-   Keys vs URLs: Paste UploadThing file keys (e.g., `abc123-file.png`) or full URLs like `https://utfs.io/f/abc123-file.png`.
-   API key: Provide your UploadThing secret key (`sk_...`) when using keys so the node can resolve the public URL. If you supply full URLs, the secret is not needed.

## Token refresh (optional)

-   Dropbox cloud_api_key JSON: `{"app_key","app_secret","refresh_token","access_token"?, "authorization_code"?}` (authorization code optional; only needed for the initial exchange).
-   Google Drive cloud_api_key JSON: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive cloud_api_key JSON: `{client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}`.

When provided, the node automatically exchanges the refresh token for a fresh access token before downloading.

## Returns

-   IMAGE (Tensor): Loaded image batch.
-   MASK (Tensor): Associated alpha or inferred mask batch.

## Notes

-   Downloads stream in chunks when supported; the UI shows cumulative bytes and item progress.
-   If shape differs across images, only the first image/mask is returned as a single batch entry.
