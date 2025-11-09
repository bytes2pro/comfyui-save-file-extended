## SaveAudioOpusExtended

Convenience variant of SaveAudioExtended locked to Opus.

### Inputs

-   Same as SaveAudioExtended, except:
    -   **format** is fixed to `opus`.
    -   **quality**: `64k | 96k | 128k | 192k | 320k` (matches core Opus node).
-   **filename (STRING, optional)**: Exact filename to use. If provided, this will be used directly (extension auto-appended if missing). If empty, falls back to `custom_filename` or UUID-based generation. Include file extension.
-   **custom_filename (STRING, optional)**: Custom filename prefix (without extension). If provided and `filename` is empty, uses this with `.opus` extension. If both are empty, uses UUID-based filename generation.

### Notes

-   Local/cloud behavior, metadata embedding, progress events, and returns are identical to SaveAudioExtended.


