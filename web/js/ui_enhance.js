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
                if (nodeName === "SaveImageExtended") {
                    const saveToCloud = !!get("save_to_cloud")?.value;
                    const saveToLocal = !!get("save_to_local")?.value;
                    setHidden(groups.cloud, !saveToCloud);
                    setHidden(groups.local, !saveToLocal);
                    this._cse_ui = this._cse_ui || {};
                    this._cse_ui.cloudVisible = saveToCloud;
                    this._cse_ui.localVisible = saveToLocal;
                    this._cse_ui.cloudStartIdx = indexOf("cloud_provider");
                    this._cse_ui.localStartIdx = indexOf("local_folder_path");
                } else if (nodeName === "LoadImageExtended") {
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

            if (nodeName === "SaveImageExtended") {
                attach("save_to_cloud");
                attach("save_to_local");
            } else if (nodeName === "LoadImageExtended") {
                attach("load_from_cloud");
            }

            // Initial state
            refresh();

            // Optional: subtle color cue
            this.color = this.color || "#2d2d2d";
            this.bgcolor = this.bgcolor || "#1e1e1e";

            // Draw section headers/dividers
            const prevDraw = this.onDrawForeground;
            this.onDrawForeground = function (ctx) {
                prevDraw?.call(this, ctx);
                const meta = this._cse_ui || {};
                const W = this.size?.[0] || 220;
                const widgets = this.widgets || [];
                const startY =
                    (this.computeSize?.()[1] || this.size?.[1] || 0) -
                    (widgets.length > 0 ? widgets.length * 0 : 0); // noop but keeps compat
                // Estimate per-widget height
                const H = 22; // approx row height
                const M = 6; // margin between groups
                ctx.save();
                ctx.font = "bold 12px sans-serif";
                ctx.fillStyle = "#cfcfcf";
                ctx.strokeStyle = "#555";
                ctx.lineWidth = 1;

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
                    ctx.fillStyle = "#2a2a2a";
                    ctx.fillRect(10, y - M - 12, tw, 14);
                    ctx.fillStyle = "#ddd";
                    ctx.fillText(text, 12, y - M - 1);
                };

                if (nodeName === "SaveImageExtended") {
                    if (meta.cloudVisible)
                        drawHeader("Cloud", meta.cloudStartIdx);
                    if (meta.localVisible)
                        drawHeader("Local", meta.localStartIdx);
                } else if (nodeName === "LoadImageExtended") {
                    if (meta.cloudVisible)
                        drawHeader("Cloud", meta.cloudStartIdx);
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
    enhance("LoadImageExtended", {
        cloud: [
            "cloud_provider",
            "bucket_link",
            "cloud_folder_path",
            "cloud_api_key",
        ],
    });
}
