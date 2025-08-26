## SaveWEBMExtended

Experimental WEBM saver for image sequences. Writes a `.webm` using VP9 or AV1.

### Inputs

-   **images (IMAGE)**: Tensor batch to encode.
-   **filename_prefix (STRING)**: File prefix; supports tokens.
-   **codec (CHOICE)**: `vp9 | av1`.
-   **fps (FLOAT)**: Frames per second.
-   **crf (FLOAT)**: Quality factor; higher = smaller (lower quality).

### Behavior

-   Encodes the provided frames into a WEBM container and saves under the output directory.
-   Metadata includes prompt and `extra_pnginfo` when enabled in ComfyUI.

### Returns

-   `ui.images`: Single entry for the saved video with `animated: (True,)`.

### Notes

-   Marked EXPERIMENTAL; parameters and behavior may change.


