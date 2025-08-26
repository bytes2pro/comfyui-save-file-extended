## SaveVideoExtended

Save a Video input to disk and optionally upload it to a cloud provider.

### Inputs

-   **video**: Video object.
-   **filename_prefix**: Prefix for the output file; supports tokens.
-   **format**: Container (auto/mp4/webm/mkv/...).
-   **codec**: Codec to use (auto/h264/vp9/av1/...).

### Local saving

-   `save_to_local` controls whether to keep a local copy under the ComfyUI output directory (optionally inside `local_folder_path`).

### Cloud upload

-   `save_to_cloud` uploads the rendered file to the selected provider.
-   Configure `bucket_link`, `cloud_folder_path`, `cloud_api_key`.
-   Emits progress events on `comfyui.savevideoextended.status`.

### Metadata

When enabled in ComfyUI, the node writes prompt/extra metadata into the container if supported.

### Output

-   UI entry for the local file (when enabled) and `cloud` array with provider responses.
