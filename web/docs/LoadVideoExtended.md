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

