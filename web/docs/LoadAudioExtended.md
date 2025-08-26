## LoadAudioExtended

Load audio from the local input directory or from a cloud provider.

### Inputs
- **load_from_cloud**: When enabled, download from a provider; otherwise read local files.
- **file_paths**: One filename/key per line. For local, paths are relative to the input directory; for cloud, they are keys/paths under `cloud_folder_path`.
- **local_file**: Convenience picker when loading locally.
- Cloud config: `cloud_provider`, `bucket_link`, `cloud_folder_path`, `cloud_api_key`.

### Behavior
- Supports audio files and video files (audio stream extracted).
- Emits progress events on `comfyui.loadaudioextended.status`.

### UI and events

-   A floating status panel displays real-time per-item and byte-level progress.
-   Status events: `start`, `progress` (items and/or bytes), `complete`, `error` on `comfyui.loadaudioextended.status`.

### Output
An AUDIO dict: `{ waveform: [B,C,T], sample_rate: int }`. Multiple inputs are batched when compatible.

If multiple inputs are provided and they have matching channel counts, they are concatenated into a batch; otherwise, only the first item is returned.

