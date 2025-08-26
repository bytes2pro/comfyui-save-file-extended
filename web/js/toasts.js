import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "comfyui.savefileextended.toasts",
    async setup(app) {
        const toast = (severity, summary, detail, life = 3000) => {
            try {
                app.extensionManager.toast.add({
                    severity,
                    summary,
                    detail,
                    life,
                });
            } catch (e) {
                // ignore
            }
        };

        const handleSaveStatus = (d) => {
            const provider = d?.provider ? ` via ${d.provider}` : "";
            switch (d?.phase) {
                case "start":
                    toast(
                        "info",
                        "Saving images",
                        `Starting save${provider}...`,
                        2000
                    );
                    break;
                case "error":
                    toast(
                        "error",
                        "Save failed",
                        d?.message || "Unknown error"
                    );
                    break;
                case "complete": {
                    const parts = [];
                    if (typeof d?.count_local === "number")
                        parts.push(`${d.count_local} local`);
                    if (typeof d?.count_cloud === "number")
                        parts.push(`${d.count_cloud} cloud`);
                    const detail = parts.length
                        ? `Saved ${parts.join(" and ")}${provider}.`
                        : `Completed${provider}.`;
                    toast("success", "Images saved", detail);
                    break;
                }
                default:
                    break;
            }
        };

        const handleLoadStatus = (d) => {
            const provider = d?.provider
                ? ` from ${d.provider}`
                : " from local";
            switch (d?.phase) {
                case "start":
                    toast(
                        "info",
                        "Loading images",
                        `Starting load${provider}...`,
                        2000
                    );
                    break;
                case "error":
                    toast(
                        "error",
                        "Load failed",
                        d?.message || "Unknown error"
                    );
                    break;
                case "complete":
                    toast(
                        "success",
                        "Images loaded",
                        `Loaded ${d?.count ?? "?"} image(s)${provider}.`
                    );
                    break;
                default:
                    break;
            }
        };

        // Subscribe using the documented API that bridges websocket → DOM events
        app.api.addEventListener("comfyui.savefileextended.status", (ev) =>
            handleSaveStatus(ev.detail || {})
        );
        app.api.addEventListener("comfyui.loadimageextended.status", (ev) =>
            handleLoadStatus(ev.detail || {})
        );
    },
});
