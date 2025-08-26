from __future__ import annotations

import io
import json
import os

import av
import folder_paths
import torchaudio
from comfy.cli_args import args
from comfy.comfy_types import FileLocator


def save_audio(self, audio, filename_prefix="ComfyUI", format="flac", prompt=None, extra_pnginfo=None, quality="128k"):
    filename_prefix += self.prefix_append
    full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
    results: list[FileLocator] = []

    # Prepare metadata dictionary
    metadata = {}
    if not args.disable_metadata:
        if prompt is not None:
            metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata[x] = json.dumps(extra_pnginfo[x])

    # Opus supported sample rates
    OPUS_RATES = [8000, 12000, 16000, 24000, 48000]

    for (batch_number, waveform) in enumerate(audio["waveform"].cpu()):
        filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
        file = f"{filename_with_batch_num}_{counter:05}_.{format}"
        output_path = os.path.join(full_output_folder, file)

        # Use original sample rate initially
        sample_rate = audio["sample_rate"]

        # Handle Opus sample rate requirements
        if format == "opus":
            if sample_rate > 48000:
                sample_rate = 48000
            elif sample_rate not in OPUS_RATES:
                # Find the next highest supported rate
                for rate in sorted(OPUS_RATES):
                    if rate > sample_rate:
                        sample_rate = rate
                        break
                if sample_rate not in OPUS_RATES:  # Fallback if still not supported
                    sample_rate = 48000

            # Resample if necessary
            if sample_rate != audio["sample_rate"]:
                waveform = torchaudio.functional.resample(waveform, audio["sample_rate"], sample_rate)

        # Create output with specified format
        output_buffer = io.BytesIO()
        output_container = av.open(output_buffer, mode='w', format=format)

        # Set metadata on the container
        for key, value in metadata.items():
            output_container.metadata[key] = value

        # Set up the output stream with appropriate properties
        if format == "opus":
            out_stream = output_container.add_stream("libopus", rate=sample_rate)
            if quality == "64k":
                out_stream.bit_rate = 64000
            elif quality == "96k":
                out_stream.bit_rate = 96000
            elif quality == "128k":
                out_stream.bit_rate = 128000
            elif quality == "192k":
                out_stream.bit_rate = 192000
            elif quality == "320k":
                out_stream.bit_rate = 320000
        elif format == "mp3":
            out_stream = output_container.add_stream("libmp3lame", rate=sample_rate)
            if quality == "V0":
                #TODO i would really love to support V3 and V5 but there doesn't seem to be a way to set the qscale level, the property below is a bool
                out_stream.codec_context.qscale = 1
            elif quality == "128k":
                out_stream.bit_rate = 128000
            elif quality == "320k":
                out_stream.bit_rate = 320000
        else: #format == "flac":
            out_stream = output_container.add_stream("flac", rate=sample_rate)

        frame = av.AudioFrame.from_ndarray(waveform.movedim(0, 1).reshape(1, -1).float().numpy(), format='flt', layout='mono' if waveform.shape[0] == 1 else 'stereo')
        frame.sample_rate = sample_rate
        frame.pts = 0
        output_container.mux(out_stream.encode(frame))

        # Flush encoder
        output_container.mux(out_stream.encode(None))

        # Close containers
        output_container.close()

        # Write the output to file
        output_buffer.seek(0)
        with open(output_path, 'wb') as f:
            f.write(output_buffer.getbuffer())

        results.append({
            "filename": file,
            "subfolder": subfolder,
            "type": self.type
        })
        counter += 1

    return { "ui": { "audio": results } }


class SaveAudioFlacExtended:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "audio": ("AUDIO", ),
                            "filename_prefix": ("STRING", {"default": "audio/ComfyUI"}),
                            },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_flac"

    OUTPUT_NODE = True

    CATEGORY = "audio"

    def save_flac(self, audio, filename_prefix="ComfyUI", format="flac", prompt=None, extra_pnginfo=None):
        return save_audio(self, audio, filename_prefix, format, prompt, extra_pnginfo)

class SaveAudioMP3Extended:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "audio": ("AUDIO", ),
                            "filename_prefix": ("STRING", {"default": "audio/ComfyUI"}),
                            "quality": (["V0", "128k", "320k"], {"default": "V0"}),
                            },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_mp3"

    OUTPUT_NODE = True

    CATEGORY = "audio"

    def save_mp3(self, audio, filename_prefix="ComfyUI", format="mp3", prompt=None, extra_pnginfo=None, quality="128k"):
        return save_audio(self, audio, filename_prefix, format, prompt, extra_pnginfo, quality)

class SaveAudioOpusExtended:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "audio": ("AUDIO", ),
                            "filename_prefix": ("STRING", {"default": "audio/ComfyUI"}),
                            "quality": (["64k", "96k", "128k", "192k", "320k"], {"default": "128k"}),
                            },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_opus"

    OUTPUT_NODE = True

    CATEGORY = "audio"

    def save_opus(self, audio, filename_prefix="ComfyUI", format="opus", prompt=None, extra_pnginfo=None, quality="V3"):
        return save_audio(self, audio, filename_prefix, format, prompt, extra_pnginfo, quality)