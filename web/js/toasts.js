export async function setupToasts(app) {
    const toast = (severity, summary, detail, life = 3200) => {
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

    // Slightly friendlier copy for common events
    const startEmoji = {
        save: "💾",
        load: "📥",
        audio: "🎧",
        video: "🎬",
        ok: "✅",
        error: "⚠️",
    };

    const handleSaveStatus = (d) => {
        const provider = d?.provider ? ` via ${d.provider}` : "";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.save} Saving images`,
                    `Starting save${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Save failed`,
                    d?.message || "Unknown error",
                    5000
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
                toast("success", `${startEmoji.ok} Images saved`, detail, 3600);
                break;
            }
            default:
                break;
        }
    };

    const handleLoadStatus = (d) => {
        const provider = d?.provider ? ` from ${d.provider}` : " from local";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.load} Loading images`,
                    `Starting load${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Load failed`,
                    d?.message || "Unknown error",
                    5000
                );
                break;
            case "complete":
                toast(
                    "success",
                    `${startEmoji.ok} Images loaded`,
                    `Loaded ${d?.count ?? "?"} image(s)${provider}.`,
                    3600
                );
                break;
            default:
                break;
        }
    };

    // Subscribe using the documented API that bridges websocket → DOM events
    app.api.addEventListener("comfyui.saveimageextended.status", (ev) =>
        handleSaveStatus(ev.detail || {})
    );
    app.api.addEventListener("comfyui.loadimageextended.status", (ev) =>
        handleLoadStatus(ev.detail || {})
    );

    // Audio toasts
    app.api.addEventListener("comfyui.saveaudioextended.status", (ev) => {
        const d = ev.detail || {};
        const provider = d?.provider ? ` via ${d.provider}` : "";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.save} Saving audio`,
                    `Starting save${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Save failed`,
                    d?.message || "Unknown error",
                    5000
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
                toast("success", `${startEmoji.ok} Audio saved`, detail, 3600);
                break;
            }
            default:
                break;
        }
    });
    app.api.addEventListener("comfyui.loadaudioextended.status", (ev) => {
        const d = ev.detail || {};
        const provider = d?.provider ? ` from ${d.provider}` : " from local";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.load} Loading audio`,
                    `Starting load${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Load failed`,
                    d?.message || "Unknown error",
                    5000
                );
                break;
            case "complete":
                toast(
                    "success",
                    `${startEmoji.ok} Audio loaded`,
                    `Loaded ${d?.count ?? "?"} item(s)${provider}.`,
                    3600
                );
                break;
            default:
                break;
        }
    });

    // Video toasts
    app.api.addEventListener("comfyui.savevideoextended.status", (ev) => {
        const d = ev.detail || {};
        const provider = d?.provider ? ` via ${d.provider}` : "";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.save} Saving video`,
                    `Starting save${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Save failed`,
                    d?.message || "Unknown error",
                    5000
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
                toast("success", `${startEmoji.ok} Video saved`, detail, 3600);
                break;
            }
            default:
                break;
        }
    });
    app.api.addEventListener("comfyui.loadvideoextended.status", (ev) => {
        const d = ev.detail || {};
        const provider = d?.provider ? ` from ${d.provider}` : " from local";
        switch (d?.phase) {
            case "start":
                toast(
                    "info",
                    `${startEmoji.load} Loading video`,
                    `Starting load${provider}...`,
                    2200
                );
                break;
            case "error":
                toast(
                    "error",
                    `${startEmoji.error} Load failed`,
                    d?.message || "Unknown error",
                    5000
                );
                break;
            case "complete":
                toast(
                    "success",
                    `${startEmoji.ok} Video loaded`,
                    `Completed${provider}.`,
                    3600
                );
                break;
            default:
                break;
        }
    });

    // Map generic server notifications to ComfyUI Toasts
    // Reference: https://docs.comfy.org/custom-nodes/walkthrough#send-a-message-from-server
    app.api.addEventListener("display_notification", (ev) => {
        const d = ev.detail || {};
        const severity = d.kind || d.severity || "info";
        const summary = d.title || "Notification";
        const detail = d.message || d.detail || "";
        toast(severity, summary, detail, 3200);
    });
    app.api.addEventListener("notification", (ev) => {
        const d = ev.detail || {};
        const severity = d.kind || d.severity || "info";
        const summary = d.title || "Notification";
        const detail = d.message || d.detail || "";
        toast(severity, summary, detail, 3200);
    });
    app.api.addEventListener("display_component", (ev) => {
        const d = ev.detail || {};
        if ((d.component || "").toLowerCase() === "toast") {
            const p = d.props || {};
            const severity = p.kind || p.severity || "info";
            const summary = p.title || p.summary || "";
            const detail = p.message || p.detail || "";
            const life = p.life || 3000;
            toast(severity, summary, detail, life);
        }
    });
}
