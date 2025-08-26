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

            // Draw section headers/dividers and subtle group backgrounds
            const prevDraw = this.onDrawForeground;
            this.onDrawForeground = function (ctx) {
                prevDraw?.call(this, ctx);
                const meta = this._cse_ui || {};
                const W = this.size?.[0] || 220;
                const widgets = this.widgets || [];
                // Estimate per-widget height
                const H = 22; // approx row height
                const M = 6; // margin between groups
                ctx.save();
                ctx.font = "bold 12px sans-serif";
                ctx.fillStyle = "#cfcfcf";
                ctx.strokeStyle = "#4a4a4a";
                ctx.lineWidth = 1;

                const bgFor = (label) =>
                    label === "Cloud" ? "rgba(70, 120, 210, 0.08)" : "rgba(90, 210, 140, 0.08)";

                const groupBounds = (names) => {
                    if (!Array.isArray(names) || names.length === 0) return null;
                    const indices = (widgets || [])
                        .map((w, i) => ({ w, i }))
                        .filter(({ w }) => names.includes(w.name) && !w.hidden)
                        .map(({ i }) => i);
                    if (indices.length === 0) return null;
                    return { min: Math.min(...indices), max: Math.max(...indices) };
                };

                const drawHeader = (label, idx) => {
                    if (idx == null || idx < 0) return;
                    const y = this.widgets_start_y
                        ? this.widgets_start_y + idx * H
                        : 28 + idx * H;
                    // Divider line
                    ctx.beginPath();
                    ctx.moveTo(8, y - M);
                    ctx.lineTo(W - 8, y - M);
                    ctx.stroke();
                    // Label background pill
                    const text = ` ${label} `;
                    const tw = ctx.measureText(text).width + 8;
                    ctx.fillStyle = "#242424";
                    ctx.fillRect(10, y - M - 12, tw, 14);
                    ctx.fillStyle = "#e0e0e0";
                    ctx.fillText(text, 12, y - M - 1);
                };

                const drawGroupBg = (label, names) => {
                    const bounds = groupBounds(names);
                    if (!bounds) return;
                    const startIdx = bounds.min;
                    const endIdx = bounds.max;
                    const y1 = (this.widgets_start_y ? this.widgets_start_y : 28) + startIdx * H + 2;
                    const y2 = (this.widgets_start_y ? this.widgets_start_y : 28) + (endIdx + 1) * H + 2;
                    ctx.save();
                    ctx.fillStyle = bgFor(label);
                    ctx.beginPath();
                    const radius = 6;
                    const x = 8, w = W - 16, h = Math.max(14, y2 - y1 - 4);
                    // simple rounded rect
                    ctx.moveTo(x + radius, y1);
                    ctx.arcTo(x + w, y1, x + w, y1 + h, radius);
                    ctx.arcTo(x + w, y1 + h, x, y1 + h, radius);
                    ctx.arcTo(x, y1 + h, x, y1, radius);
                    ctx.arcTo(x, y1, x + w, y1, radius);
                    ctx.closePath();
                    ctx.fill();
                    ctx.restore();
                };

                if (nodeName === "SaveImageExtended" || nodeName === "SaveAudioExtended" || nodeName === "SaveVideoExtended" || nodeName === "SaveWEBMExtended") {
                    if (meta.cloudVisible) {
                        drawGroupBg("Cloud", [
                            "cloud_provider",
                            "bucket_link",
                            "cloud_folder_path",
                            "cloud_api_key",
                        ]);
                        drawHeader("Cloud", meta.cloudStartIdx);
                    }
                    if (meta.localVisible) {
                        drawGroupBg("Local", [
                            "local_folder_path",
                        ]);
                        drawHeader("Local", meta.localStartIdx);
                    }
                } else if (nodeName === "LoadImageExtended" || nodeName === "LoadAudioExtended" || nodeName === "LoadVideoExtended") {
                    if (meta.cloudVisible) {
                        drawGroupBg("Cloud", [
                            "cloud_provider",
                            "bucket_link",
                            "cloud_folder_path",
                            "cloud_api_key",
                        ]);
                        drawHeader("Cloud", meta.cloudStartIdx);
                    }
                }
                ctx.restore();
            };
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
