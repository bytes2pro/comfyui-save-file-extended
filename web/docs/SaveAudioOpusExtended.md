## SaveAudioOpusExtended

Convenience variant of SaveAudioExtended locked to Opus.

### Inputs

-   Same as SaveAudioExtended, except:
    -   **format** is fixed to `opus`.
    -   **quality**: `64k | 96k | 128k | 192k | 320k` (matches core Opus node).

### Notes

-   Local/cloud behavior, metadata embedding, progress events, and returns are identical to SaveAudioExtended.


