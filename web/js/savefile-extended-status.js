export async function setupStatus(app) {
    if (!app || !app.socket) return;
    try {
        app.socket.addEventListener("message", (ev) => {
            try {
                const msg =
                    typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data;
                const t = msg && (msg.type || msg.event);
                if (!t) return;
                const interested = new Set([
                    "comfyui.saveimageextended.status",
                    "comfyui.loadimageextended.status",
                    "comfyui.saveaudioextended.status",
                    "comfyui.loadaudioextended.status",
                    "comfyui.savevideoextended.status",
                    "comfyui.loadvideoextended.status",
                ]);
                if (interested.has(t)) {
                    // eslint-disable-next-line no-console
                    console.log("[SaveFileExtended]", t, msg.data || msg);
                }
            } catch (e) {
                // ignore
            }
        });
    } catch (e) {
        // ignore
    }
}
