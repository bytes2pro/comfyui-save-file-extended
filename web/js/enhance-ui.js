export async function beforeRegisterNodeDef(nodeType, nodeData, app) {
    const enhance = (nodeName, groups) => {
        if (nodeData?.name !== nodeName) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            orig?.apply(this, arguments);
            const get = (name) =>
                (this.widgets || []).find((w) => w.name === name);
            const setHidden = (names, hidden) => {
                names.forEach((n) => {
                    const w = get(n);
                    if (w) w.hidden = !!hidden;
                });
            };
            const indexOf = (name) =>
                (this.widgets || []).findIndex((w) => w.name === name);
            const refresh = () => {
                if (nodeName === "SaveImageExtended" || nodeName === "SaveAudioExtended" || nodeName === "SaveVideoExtended" || nodeName === "SaveWEBMExtended") {
                    const saveToCloud = !!get("save_to_cloud")?.value;
                    const saveToLocal = !!get("save_to_local")?.value;
                    setHidden(groups.cloud, !saveToCloud);
                    setHidden(groups.local, !saveToLocal);
                    this._cse_ui = this._cse_ui || {};
                    this._cse_ui.cloudVisible = saveToCloud;
                    this._cse_ui.localVisible = saveToLocal;
                    this._cse_ui.cloudStartIdx = indexOf("cloud_provider");
                    this._cse_ui.localStartIdx = indexOf("local_folder_path");
                } else if (nodeName === "LoadImageExtended" || nodeName === "LoadAudioExtended" || nodeName === "LoadVideoExtended") {
                    const fromCloud = !!get("load_from_cloud")?.value;
                    setHidden(groups.cloud, !fromCloud);
                    this._cse_ui = this._cse_ui || {};
                    this._cse_ui.cloudVisible = fromCloud;
                    this._cse_ui.cloudStartIdx = indexOf("cloud_provider");
                }
                this.onResize?.(this.size);
                app.graph.setDirtyCanvas(true, true);
            };

            // Attach callbacks to toggles
            const attach = (n) => {
                const w = get(n);
                if (!w) return;
                const prev = w.callback;
                w.callback = (v) => {
                    prev?.(v);
                    refresh();
                };
            };

            if (nodeName === "SaveImageExtended" || nodeName === "SaveAudioExtended" || nodeName === "SaveVideoExtended" || nodeName === "SaveWEBMExtended") {
                attach("save_to_cloud");
                attach("save_to_local");
            } else if (nodeName === "LoadImageExtended" || nodeName === "LoadAudioExtended" || nodeName === "LoadVideoExtended") {
                attach("load_from_cloud");
            }

            // Initial state
            refresh();

            // Optional: subtle color cue
            this.color = this.color || "#2b2b2b";
            this.bgcolor = this.bgcolor || "#191919";
        };
    };

    // Define field groups for toggling visibility
    enhance("SaveImageExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
        local: ["local_folder_path"],
    });
    enhance("SaveAudioExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
        local: ["local_folder_path"],
    });
    enhance("SaveVideoExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
        local: ["local_folder_path"],
    });
    enhance("SaveWEBMExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
        local: ["local_folder_path"],
    });
    enhance("LoadImageExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
    });
    enhance("LoadAudioExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
    });
    enhance("LoadVideoExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
    });
}
