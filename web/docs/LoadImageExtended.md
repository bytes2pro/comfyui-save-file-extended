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
-   Dropbox → bucket_link: `/base/path`.
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

-   Bucket link: `/base/path`
-   API key: Dropbox access token

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

-   Google Drive cloud_api_key JSON: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive cloud_api_key JSON: `{client_id, client_secret, refresh_token, tenant='common'|'consumers'|'organizations', redirect_uri?}`.

When provided, the node automatically exchanges the refresh token for a fresh access token before downloading.

## Returns

-   IMAGE (Tensor): Loaded image batch.
-   MASK (Tensor): Associated alpha or inferred mask batch.

## Notes

-   Downloads stream in chunks when supported; the UI shows cumulative bytes and item progress.
-   If shape differs across images, only the first image/mask is returned as a single batch entry.
