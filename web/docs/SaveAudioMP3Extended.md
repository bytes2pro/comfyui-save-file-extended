## SaveAudioMP3Extended

Convenience variant of SaveAudioExtended locked to MP3.

### Inputs

-   Same as SaveAudioExtended, except:
    -   **format** is fixed to `mp3`.
    -   **quality**: `V0 | 128k | 320k` (matches core MP3 node).
-   **filename (STRING, optional)**: Exact filename to use. If provided, this will be used directly (extension auto-appended if missing). If empty, falls back to `custom_filename` or UUID-based generation. Include file extension.
-   **custom_filename (STRING, optional)**: Custom filename prefix (without extension). If provided and `filename` is empty, uses this with `.mp3` extension. If both are empty, uses UUID-based filename generation.

### Notes

-   Local/cloud behavior, metadata embedding, progress events, and returns are identical to SaveAudioExtended.


