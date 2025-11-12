# Save Workflow Extended

Save workflow JSON files locally and/or upload them to a cloud provider. Shows real-time progress in the UI.

## How it works

-   Local: Writes workflow JSON files under the ComfyUI output directory when "Save to Local" is enabled.
-   Cloud: Uploads workflow JSON files to your selected provider when "Save to Cloud" is enabled.
-   Output: The node returns the saved filename and a `cloud` array with upload info.

The workflow JSON includes:
-   The prompt (workflow structure with nodes and connections)
-   Extra data (UI positions, metadata, etc.)

## UI tips

-   The node UI separates "Cloud" and "Local" sections with headers and dividers.
-   Each section only appears when its toggle is enabled.
-   A floating "Save/Load Status" panel displays progress.

## Inputs

-   filename_prefix (STRING): The file prefix; supports tokens like `%date:yyyy-MM-dd%` and node field tokens.
-   filename (STRING, optional): Exact filename to use. If provided, this will be used directly. If empty, falls back to `custom_filename` or UUID-based generation. Include file extension (.json).
-   custom_filename (STRING, optional): Custom filename prefix (without extension). If provided and `filename` is empty, uses this with `.json` extension. If both are empty, uses UUID-based filename generation.
-   append_timestamp (BOOLEAN): Append timestamp to filename to prevent overwriting. Default: Enabled. If disabled and filename is provided, will overwrite existing files.
-   save_to_cloud (BOOLEAN): Enable the cloud section and uploads.
-   cloud_provider (CHOICE): One of AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase, UploadThing.
-   bucket_link (STRING): Provider-specific destination identifier (see examples).
-   cloud_folder_path (STRING): Folder/key prefix under the destination; created when applicable. Default: "workflows".
-   cloud_api_key (STRING): Credentials; supports tokens and JSON; see token refresh below.
-   save_to_local (BOOLEAN): Enable local output writes.
-   local_folder_path (STRING): Subfolder under the ComfyUI output directory; created if missing.

## Provider examples

-   AWS S3 → bucket_link: `s3://my-bucket/prefix` | cloud_api_key: JSON `{access_key, secret_key, region}` or `ACCESS:SECRET[:REGION]`.
-   S3-Compatible → bucket_link: `https://endpoint.example.com/my-bucket/prefix` | cloud_api_key: same as S3.
-   Google Cloud Storage → bucket_link: `gs://bucket/prefix` or `bucket/prefix` | cloud_api_key: service-account JSON string or file path (empty uses ADC).
-   Azure Blob → bucket_link: connection string OR `https://account.blob.core.windows.net/container/prefix` | cloud_api_key: connection string or account key/SAS when using URL.
-   Backblaze B2 → bucket_link: `b2://bucket/prefix` or `bucket/prefix` | cloud_api_key: `KEY_ID:APP_KEY`.
-   Google Drive → bucket_link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>` OR a folder URL like `https://drive.google.com/drive/folders/<folderId>` | cloud_api_key: OAuth2 token or refresh JSON.
-   Dropbox → bucket_link: `/base/path` | cloud_api_key: access token.
-   OneDrive → bucket_link: `/base/path` | cloud_api_key: OAuth2 token or refresh JSON.
-   FTP → bucket_link: `ftp://user:pass@host[:port]/basepath` | cloud_api_key: not used.
-   Supabase → bucket_link: `<bucket_name>` | cloud_api_key: JSON `{url, key}` or `url|key`.
-   UploadThing → bucket_link: your project name | cloud_api_key: your UploadThing secret key (`sk_...`). Returns public utfs.io URLs.

## Getting provider values (URLs, bucket links, keys)

### AWS S3

-   Bucket link: `s3://<bucket>[/prefix]`
-   API key (cloud_api_key): either JSON `{"access_key":"...","secret_key":"...","region":"us-east-1"}` or `ACCESS:SECRET[:REGION]`
-   Where to find: AWS Console → IAM (create access key) and S3 (bucket name)

### S3-Compatible (MinIO, Cloudflare R2, etc.)

-   Bucket link: `https://<endpoint>/<bucket>[/prefix]` (must be virtual-host or path-style URL supported by your provider)
-   API key: same as S3 (access/secret and optional region)
-   Where to find: your provider dashboard (endpoint URL, bucket name, access keys)

### Google Cloud Storage (GCS)

-   Bucket link: `gs://<bucket>[/prefix]` or `<bucket>[/prefix]`
-   API key: service-account JSON (paste as a JSON string) or a file path to the JSON
-   Where to find: Google Cloud Console → IAM & Admin → Service Accounts (create key), Storage → Buckets

### Azure Blob Storage

-   Bucket link: either a connection string OR `https://<account>.blob.core.windows.net/<container>[/prefix]`
-   API key: use a connection string, or account key/SAS when using URL form
-   Where to find: Azure Portal → Storage accounts → Access keys / Shared access signature; Containers under your account

### Backblaze B2

-   Bucket link: `b2://<bucket>[/prefix]` or `<bucket>[/prefix]`
-   API key: `KEY_ID:APP_KEY`
-   Where to find: Backblaze → App Keys and Buckets

### Google Drive

-   Bucket link: `/MyFolder/Sub` OR `drive://<folderId>/<optional/subpath>` OR `https://drive.google.com/drive/folders/<folderId>`
-   Behavior: When using `drive://<folderId>` (or a Drive folder URL), any `cloud_folder_path` and any extra subpath in the bucket link are resolved relative to that folder ID (not root).
-   API key: OAuth2 JSON `{"client_id","client_secret","refresh_token"}` (optional `access_token`), or a raw OAuth2 access token string
-   Where to find: Google Cloud Console → OAuth consent + OAuth credentials; Drive folder ID from the folder URL

### Dropbox

-   Bucket link: `/base/path`
-   API key: Dropbox access token
-   Where to find: Dropbox App Console → Scoped App → Generate access token

### OneDrive

-   Bucket link: `/base/path`
-   API key: OAuth2 JSON `{"client_id","client_secret","refresh_token","tenant":"common|consumers|organizations","redirect_uri"?}`; or an access token
-   Where to find: Azure App registrations (Microsoft identity platform); OneDrive path from web UI

### FTP

-   Bucket link: `ftp://user:pass@host[:port]/basepath`
-   API key: not used

### Supabase Storage

-   Bucket link: `<bucket_name>`
-   API key: `{"url":"https://<project>.supabase.co","key":"<JWT>"}` or `https://<project>.supabase.co|<JWT>`
-   Keys: Project Settings → API → Project URL and anon/service_role keys
-   Writes with anon require storage RLS policies. Easiest is to use the service_role key on a trusted server. Example policies to allow anon:

```sql
create policy "Allow anon insert"
on storage.objects for insert to anon
with check (bucket_id = '<bucket_name>');

create policy "Allow anon update"
on storage.objects for update to anon
using (bucket_id = '<bucket_name>')
with check (bucket_id = '<bucket_name>');

create policy "Allow anon select"
on storage.objects for select to anon
using (bucket_id = '<bucket_name>');
```

### UploadThing

-   Bucket link: your UploadThing Project Name
-   API key: your UploadThing secret key (`sk_...`). A JSON string like `{"secret":"sk_..."}` also works.
-   Behavior: Files are uploaded via the UploadThing API and served from the public CDN (`utfs.io`). The node returns the CDN URL and file key.

## Token refresh (optional)

-   Google Drive cloud_api_key JSON: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive cloud_api_key JSON: `{client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}`.

When provided, the node automatically exchanges the refresh token for a fresh access token before uploading.

## Returns

-   ui.text: The files saved locally (for display purposes).
-   result: The saved filename.
-   cloud: A list of objects (provider, path, url where available) for cloud uploads.

## Notes

-   Uploads stream in chunks when supported; the UI shows cumulative bytes and item progress.
-   If both Local and Cloud are enabled, files will be saved locally and uploaded.
-   The workflow JSON file contains the complete workflow structure including nodes, connections, and UI metadata.
-   **File overwriting behavior:**
    -   By default, `append_timestamp` is enabled, which appends a timestamp (e.g., `_20240101_123456`) to the filename to prevent overwriting.
    -   If you provide a fixed `filename` or `custom_filename` and disable `append_timestamp`, the file will be overwritten on each run.
    -   If you don't provide a filename (use default), a UUID is appended, so each run creates a new file.

