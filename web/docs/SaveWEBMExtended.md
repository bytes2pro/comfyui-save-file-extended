## SaveWEBMExtended

Save an animation from a batch of images as WEBM (VP9 or AV1), locally and/or to a cloud provider. Uses UUID file names and emits real-time progress events compatible with the floating status panel and toasts.

### Inputs

-   **images (IMAGE)**: Tensor batch to encode.
-   **filename_prefix (STRING)**: File prefix; supports tokens (e.g., `%date:yyyy-MM-dd%`).
-   **codec (CHOICE)**: `vp9 | av1`.
-   **fps (FLOAT)**: Frames per second.
-   **crf (FLOAT)**: Quality factor; higher = smaller (lower quality).
-   **save_to_cloud (BOOLEAN)**: Enable uploads.
-   **cloud_provider (CHOICE)**: AWS S3, S3-Compatible, GCS, Azure Blob, Backblaze B2, Google Drive, Dropbox, OneDrive, FTP, Supabase, UploadThing.
-   **bucket_link (STRING)**: Provider destination.
-   **cloud_folder_path (STRING)**: Folder/key prefix.
-   **cloud_api_key (STRING)**: Credentials; JSON or token depending on provider.
-   **save_to_local (BOOLEAN)**: Write a local copy.
-   **local_folder_path (STRING)**: Subfolder under the output directory.

### Behavior

-   Encodes the frames to `.webm` in the output directory (when local is enabled) using a UUID-based filename.
-   When cloud is enabled, the saved file is uploaded with byte-level and per-item progress.
-   Metadata includes prompt and `extra_pnginfo` when enabled in ComfyUI.

### UI and events

-   Status events are emitted on `comfyui.savevideoextended.status` (`start`, `progress`, `complete`, `error`).
-   The floating status panel and toasts show progress for local and cloud operations.

### Returns

-   `ui.images`: Single entry for the saved video with `animated: (True,)`.
-   `cloud`: Provider upload results.

### Notes

-   Marked EXPERIMENTAL; parameters and behavior may change.


