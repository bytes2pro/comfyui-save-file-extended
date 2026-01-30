export async function beforeRegisterNodeDef(nodeType, nodeData, app) {
    const enhance = (nodeName, groups) => {
        if (nodeData?.name !== nodeName) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            orig?.apply(this, arguments);

            // Remove any stale header widgets carried over from a clone
            if (this.widgets) {
                this.widgets = this.widgets.filter((w) => !w.__cse_header);
            }

            // Always create fresh UI state (never reuse from clone)
            this._cse_ui = { widgets: {} };

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

            const persistKey = (section) =>
                `${nodeName}:cse:${section}:collapsed`;

            const ensureHeaderAt = (section, displayName, startIdx) => {
                if (startIdx < 0) return;
                const ui = this._cse_ui;
                ui.widgets = ui.widgets || {};
                if (!ui.widgets[section]) {
                    // Create header button once
                    const header = this.addWidget(
                        "button",
                        `${displayName} ▾`,
                        null,
                        () => {
                            const key = section + "Collapsed";
                            ui[key] = !ui[key];
                            try {
                                localStorage.setItem(
                                    persistKey(section),
                                    ui[key] ? "1" : "0"
                                );
                            } catch {}
                            // Update arrow
                            header.name = `${displayName} ${
                                ui[key] ? "▸" : "▾"
                            }`;
                            refresh();
                        }
                    );
                    // Do not serialize client-only header
                    // Must set in options so LiteGraph's serialize/configure
                    // actually skips this widget in widgets_values.
                    header.options = header.options || {};
                    header.options.serialize = false;
                    header.serialize = false;
                    header.__cse_header = true;
                    ui.widgets[section] = header;
                    // Move header to desired index (above the group's first field)
                    const currentIdx = this.widgets.indexOf(header);
                    if (currentIdx > -1) {
                        this.widgets.splice(currentIdx, 1);
                        this.widgets.splice(startIdx, 0, header);
                    }
                } else {
                    // Ensure header sits at the right location if widgets moved
                    const header = ui.widgets[section];
                    const currentIdx = this.widgets.indexOf(header);
                    if (
                        currentIdx !== startIdx &&
                        currentIdx > -1 &&
                        startIdx > -1
                    ) {
                        this.widgets.splice(currentIdx, 1);
                        this.widgets.splice(startIdx, 0, header);
                    }
                }
            };

            const refresh = () => {
                if (
                    nodeName === "SaveImageExtended" ||
                    nodeName === "SaveAudioExtended" ||
                    nodeName === "SaveVideoExtended" ||
                    nodeName === "SaveWEBMExtended" ||
                    nodeName === "SaveWorkflowExtended"
                ) {
                    const saveToCloud = !!get("save_to_cloud")?.value;
                    const saveToLocal = !!get("save_to_local")?.value;
                    this._cse_ui.cloudVisible = saveToCloud;
                    this._cse_ui.localVisible = saveToLocal;
                    this._cse_ui.cloudStartIdx = indexOf("cloud_provider");
                    this._cse_ui.localStartIdx = indexOf("local_folder_path");

                    // Restore persisted collapsed state
                    if (this._cse_ui.cloudCollapsed === undefined) {
                        try {
                            this._cse_ui.cloudCollapsed =
                                localStorage.getItem(persistKey("cloud")) ===
                                "1";
                        } catch {}
                    }
                    if (this._cse_ui.localCollapsed === undefined) {
                        try {
                            this._cse_ui.localCollapsed =
                                localStorage.getItem(persistKey("local")) ===
                                "1";
                        } catch {}
                    }

                    // Ensure headers exist and are positioned
                    ensureHeaderAt(
                        "cloud",
                        "Cloud",
                        this._cse_ui.cloudStartIdx
                    );
                    ensureHeaderAt(
                        "local",
                        "Local",
                        this._cse_ui.localStartIdx
                    );

                    // Apply collapsed/visibility
                    const cloudHidden =
                        !saveToCloud || !!this._cse_ui.cloudCollapsed;
                    const localHidden =
                        !saveToLocal || !!this._cse_ui.localCollapsed;
                    setHidden(groups.cloud, cloudHidden);
                    setHidden(groups.local, localHidden);
                    if (this._cse_ui.widgets.cloud) {
                        this._cse_ui.widgets.cloud.hidden = !saveToCloud;
                        this._cse_ui.widgets.cloud.name = `Cloud ${
                            this._cse_ui.cloudCollapsed ? "▸" : "▾"
                        }`;
                    }
                    if (this._cse_ui.widgets.local) {
                        this._cse_ui.widgets.local.hidden = !saveToLocal;
                        this._cse_ui.widgets.local.name = `Local ${
                            this._cse_ui.localCollapsed ? "▸" : "▾"
                        }`;
                    }
                } else if (
                    nodeName === "LoadImageExtended" ||
                    nodeName === "LoadAudioExtended" ||
                    nodeName === "LoadVideoExtended"
                ) {
                    const fromCloud = !!get("load_from_cloud")?.value;
                    this._cse_ui.cloudVisible = fromCloud;
                    this._cse_ui.cloudStartIdx = indexOf("cloud_provider");

                    // Restore persisted collapsed state
                    if (this._cse_ui.cloudCollapsed === undefined) {
                        try {
                            this._cse_ui.cloudCollapsed =
                                localStorage.getItem(persistKey("cloud")) ===
                                "1";
                        } catch {}
                    }

                    // Ensure header exists
                    ensureHeaderAt(
                        "cloud",
                        "Cloud",
                        this._cse_ui.cloudStartIdx
                    );

                    // Apply collapsed/visibility
                    const cloudHidden =
                        !fromCloud || !!this._cse_ui.cloudCollapsed;
                    setHidden(groups.cloud, cloudHidden);
                    if (this._cse_ui.widgets.cloud) {
                        this._cse_ui.widgets.cloud.hidden = !fromCloud;
                        this._cse_ui.widgets.cloud.name = `Cloud ${
                            this._cse_ui.cloudCollapsed ? "▸" : "▾"
                        }`;
                    }
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

            if (
                nodeName === "SaveImageExtended" ||
                nodeName === "SaveAudioExtended" ||
                nodeName === "SaveVideoExtended" ||
                nodeName === "SaveWEBMExtended" ||
                nodeName === "SaveWorkflowExtended"
            ) {
                attach("save_to_cloud");
                attach("save_to_local");
            } else if (
                nodeName === "LoadImageExtended" ||
                nodeName === "LoadAudioExtended" ||
                nodeName === "LoadVideoExtended"
            ) {
                attach("load_from_cloud");
            }

            // Safety net: actively strip header entries from serialised
            // widgets_values so stale saves can never include them.
            const origOnSerialize = this.onSerialize;
            this.onSerialize = function (o) {
                origOnSerialize?.apply(this, arguments);
                if (o.widgets_values && this.widgets) {
                    // Rebuild widgets_values excluding header widgets
                    const clean = [];
                    let vi = 0;
                    for (const w of this.widgets) {
                        if (vi >= o.widgets_values.length) break;
                        if (w.__cse_header) {
                            vi++; // skip this entry
                            continue;
                        }
                        clean.push(o.widgets_values[vi++]);
                    }
                    o.widgets_values = clean;
                }
            };

            // Hook onConfigure so that after ComfyUI restores serialised
            // widget values (clone / paste / workflow-load) we re-insert
            // headers at the correct positions with the right visibility.
            const origOnConfigure = this.onConfigure;
            this.onConfigure = function (data) {
                origOnConfigure?.apply(this, arguments);

                // Backwards-compat: old saves may include null entries
                // for header widgets that were accidentally serialised.
                // configure() already applied the (shifted) values, so
                // we must detect and re-apply the corrected values.
                const saved = data?.widgets_values;
                const realWidgets = (this.widgets || []).filter(
                    (w) => !w.__cse_header
                );
                if (
                    saved &&
                    saved.length > realWidgets.length
                ) {
                    const stripped = saved.filter((v) => v !== null);
                    if (stripped.length === realWidgets.length) {
                        let j = 0;
                        for (const w of this.widgets) {
                            if (w.__cse_header) continue;
                            if (j < stripped.length) {
                                w.value = stripped[j++];
                            }
                        }
                    }
                }

                refresh();
            };

            // For a brand-new node (no configure() call) we still need to
            // set up the initial state.  Use queueMicrotask so that if
            // configure() IS called synchronously right after onNodeCreated
            // (the clone / paste path) it runs first, and our deferred
            // refresh() sees the already-restored values.
            queueMicrotask(() => refresh());

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
    enhance("SaveWorkflowExtended", {
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
