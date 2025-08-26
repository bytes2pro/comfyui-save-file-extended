## LoadVideoExtended

Load a video from the local input directory or from supported cloud providers. Shows real-time per-item progress in the UI.

### Inputs

-   **load_from_cloud (BOOLEAN)**: Toggle between local and cloud sources.
-   **file_paths (STRING, multiline)**: One filename/key per line. For local, paths are relative to the input directory; for cloud, keys are resolved under `cloud_folder_path`.
-   **local_file (DROPDOWN)**: When Cloud is OFF, pick a local video (with upload support) like the core LoadVideo node.
-   Cloud config when Cloud is ON:
    -   **cloud_provider (CHOICE)**: AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase, UploadThing
    -   **bucket_link (STRING)**: Provider-specific origin (see below)
    -   **cloud_folder_path (STRING)**: Optional folder/key prefix
    -   **cloud_api_key (STRING)**: Credentials; JSON or token depending on provider

### Behavior

-   Returns a single Video object. If multiple paths are provided, the first one is used.
-   Emits progress events on `comfyui.loadvideoextended.status`.

### UI and events

-   The floating status panel displays real-time progress during downloads.
-   Status events: `start`, `progress`, `complete`, `error` on `comfyui.loadvideoextended.status`.

### Cloud providers and examples

-   AWS S3 → `s3://bucket/prefix`
-   S3-Compatible → `https://endpoint/bucket/prefix`
-   Google Cloud Storage → `gs://bucket/prefix` or `bucket/prefix`
-   Azure Blob → connection string OR `https://account.blob.core.windows.net/container/prefix`
-   Backblaze B2 → `b2://bucket/prefix` or `bucket/prefix`
-   Google Drive → `/MyFolder/Sub` OR `drive://<folderId>/<sub>` OR a folder URL
-   Dropbox → `/base/path`
-   OneDrive → `/base/path`
-   FTP → `ftp://user:pass@host[:port]/basepath`
-   Supabase Storage → `<bucket_name>`
-   UploadThing → leave `bucket_link` blank; use file keys or full `utfs.io` URLs

### Token refresh (optional)

-   Google Drive: `{client_id, client_secret, refresh_token}` (optional `access_token`).
-   OneDrive: `{client_id, client_secret, refresh_token, tenant, redirect_uri?}`.

### Returns

-   `VIDEO`: The loaded video.

## LoadVideoExtended

Load video from the local input directory or from a cloud provider.

### Inputs
- **load_from_cloud**: When enabled, download via the chosen provider; otherwise read from the local input directory.
- **file_paths**: One filename/key per line.
- **local_file**: Convenience picker for local mode.
- Cloud config: `cloud_provider`, `bucket_link`, `cloud_folder_path`, `cloud_api_key`.

### Behavior
- Downloads the first entry and returns a single Video object.
- Emits progress events on `comfyui.loadvideoextended.status`.

### Output
- A `VIDEO` object suitable for downstream Save/Preview nodes.

