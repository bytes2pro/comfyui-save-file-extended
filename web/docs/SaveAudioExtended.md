## SaveAudioExtended

Save audio locally and/or upload to a cloud provider. Supports wav, flac, mp3, opus.

### Inputs
- **audio**: AUDIO dict with `waveform` [B,C,T] and `sample_rate`.
- **filename_prefix**: Prefix for output files; supports tokens like `%date:yyyy-MM-dd%`.
- **format**: `wav | flac | mp3 | opus`.
- **quality**: For mp3/opus; selects bitrate or VBR (ignored for wav/flac).

### Local saving
- Toggle with `save_to_local`. Files are written under the ComfyUI output directory, optionally inside `local_folder_path`.

### Cloud upload
- Toggle with `save_to_cloud` and choose a provider.
- Configure `bucket_link`, `cloud_folder_path`, and `cloud_api_key`.
- Batch uploads with progress events: `comfyui.saveaudioextended.status`.

### Metadata
If ComfyUI metadata is enabled, prompt and extra_pnginfo (as JSON) are embedded in supported formats.

### Output
Returns UI entries for local files and a `cloud` array with provider upload info.

