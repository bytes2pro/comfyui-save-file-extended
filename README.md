# comfyui-save-file-extended

Cloud-enabled save/load nodes for ComfyUI with clean UI, multi-provider support, and real-time progress.

This extension adds enhanced Save and Load nodes that can write to/read from local disk and popular cloud storage providers. It includes a polished client UI with separate Cloud and Local sections, and a floating status panel that shows per-item and byte-level progress during uploads/downloads.

> [!NOTE]
> This project was created with the official [cookiecutter](https://github.com/Comfy-Org/cookiecutter-comfy-extension) template.

## Nodes

-   **SaveImageExtended**: Save images locally and/or upload to a selected cloud provider in one batch.
-   **LoadImageExtended**: Load images from local input directory or directly from cloud.

Both nodes:

-   Separate Cloud/Local sections with headers and dividers (only visible when enabled)
-   Detailed tooltips and built-in help docs (Help icon in node header)
-   Real-time status panel showing per-item and byte-level progress

## Supported cloud providers

-   AWS S3, S3-Compatible endpoints
-   Google Cloud Storage
-   Azure Blob Storage
-   Backblaze B2
-   Google Drive
-   Dropbox
-   OneDrive
-   FTP
-   Supabase Storage
-   UploadThing

## Key features

-   Batch save/upload with per-file and byte-level progress
-   Conditional UI (only shows relevant options for Cloud/Local)
-   Token refresh for Drive/OneDrive (accepts JSON with refresh_token)
-   Provider-specific path handling with auto-folder creation where applicable
-   Rich help pages rendered in the ComfyUI client

## Future plans

-   Implement similar extensions for video and audio upload nodes.

## Quickstart

1. Install [ComfyUI](https://docs.comfy.org/get_started).
2. Install [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) (recommended).
3. Install this extension via ComfyUI-Manager, or clone this repo into `ComfyUI/custom_nodes`.
4. Restart ComfyUI.

### Using the nodes

1. Add "Save Image Extended" or "Load Image Extended".
2. Toggle Cloud and/or Local.
3. Configure provider, `bucket_link`, `cloud_folder_path`, and credentials (`cloud_api_key`).
4. Run the workflow. Watch progress in the "Save/Load Status" panel.

### Credentials (examples)

-   S3/S3-Compatible: JSON `{access_key, secret_key, region}` or `ACCESS:SECRET[:REGION]`
-   GCS: Service account JSON file path or JSON string; or rely on ADC
-   Azure Blob: Connection string (or account URL with key/SAS)
-   B2: `KEY_ID:APP_KEY`
-   Supabase: JSON `{url, key}` or `url|key`
-   Drive/OneDrive: OAuth2 token or JSON with `refresh_token` (+ client id/secret)

## Develop

To install the dev dependencies and pre-commit (will run the ruff hook), do:

```bash
cd comfyui_save_file_extended
pip install -e .[dev]
pre-commit install
```

The `-e` flag above will result in a "live" install, in the sense that any changes you make to your node extension will automatically be picked up the next time you run ComfyUI.

## Publish to Github

Install Github Desktop or follow these [instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) for ssh.

1. Create a Github repository that matches the directory name.
2. Push the files to Git

```
git add .
git commit -m "project scaffolding"
git push
```

## Writing custom nodes

An example custom node is located in [nodes.py](src/comfyui_save_file_extended/nodes.py). To learn more, read the [docs](https://docs.comfy.org/essentials/custom_node_overview).

## Tests

This repo contains unit tests written in Pytest in the `tests/` directory. It is recommended to unit test your custom node.

-   [build-pipeline.yml](.github/workflows/build-pipeline.yml) will run pytest and linter on any open PRs
-   [validate.yml](.github/workflows/validate.yml) will run [node-diff](https://github.com/Comfy-Org/node-diff) to check for breaking changes

## Publishing to Registry

If you wish to share this custom node with others in the community, you can publish it to the registry. We've already auto-populated some fields in `pyproject.toml` under `tool.comfy`, but please double-check that they are correct.

You need to make an account on https://registry.comfy.org and create an API key token.

-   [ ] Go to the [registry](https://registry.comfy.org). Login and create a publisher id (everything after the `@` sign on your registry profile).
-   [ ] Add the publisher id into the pyproject.toml file.
-   [ ] Create an api key on the Registry for publishing from Github. [Instructions](https://docs.comfy.org/registry/publishing#create-an-api-key-for-publishing).
-   [ ] Add it to your Github Repository Secrets as `REGISTRY_ACCESS_TOKEN`.

A Github action will run on every git push. You can also run the Github action manually. Full instructions [here](https://docs.comfy.org/registry/publishing). Join our [discord](https://discord.com/invite/comfyorg) if you have any questions!

## Roadmap

-   Video and audio equivalents of these nodes (save/load with cloud support and progress UI)
-   Additional providers and authentication helpers

