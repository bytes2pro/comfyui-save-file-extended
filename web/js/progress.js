export async function setupProgress(app) {
    const panelId = "cse-status-panel";
    let panel = document.getElementById(panelId);
    if (!panel) {
        panel = document.createElement("div");
        panel.id = panelId;
        panel.style.position = "fixed";
        panel.style.bottom = "12px";
        panel.style.right = "12px";
        panel.style.maxWidth = "360px";
        panel.style.maxHeight = "40vh";
        panel.style.overflow = "auto";
        panel.style.padding = "8px";
        panel.style.background = "rgba(0,0,0,0.7)";
        panel.style.color = "#fff";
        panel.style.fontSize = "12px";
        panel.style.borderRadius = "6px";
        panel.style.zIndex = 9999;
        panel.style.pointerEvents = "auto";
        panel.style.boxShadow = "0 2px 10px rgba(0,0,0,.4)";
        const title = document.createElement("div");
        title.textContent = "Save/Load Status";
        title.style.fontWeight = "bold";
        title.style.marginBottom = "6px";
        panel.appendChild(title);
        const list = document.createElement("div");
        list.id = panelId + "-list";
        list.style.display = "flex";
        list.style.flexDirection = "column";
        list.style.gap = "4px";
        panel.appendChild(list);
        document.body.appendChild(panel);
    }
    const list = document.getElementById(panelId + "-list");

    function push(msg) {
        const item = document.createElement("div");
        item.innerHTML = msg;
        list.appendChild(item);
        // prune
        while (list.children.length > 200) list.removeChild(list.firstChild);
    }

    function fmtProgress(
        where,
        current,
        total,
        filename,
        provider,
        bytesDone,
        bytesTotal
    ) {
        const useBytes =
            bytesDone !== undefined && bytesTotal !== undefined && bytesTotal;
        const pct = useBytes
            ? Math.round((bytesDone / bytesTotal) * 100)
            : total
            ? Math.round((current / total) * 100)
            : 0;
        const whereTxt = where ? where : "";
        const prov = provider ? ` [${provider}]` : "";
        const base = useBytes
            ? `${bytesDone}/${bytesTotal} bytes`
            : `${current}/${total}`;
        return `${whereTxt} ${base} (${pct}%) ${
            filename ? `- ${filename}` : ""
        }${prov}`;
    }

    // Save events
    app.api.addEventListener("comfyui.saveimageextended.status", (ev) => {
        const d = ev.detail || {};
        if (d.phase === "start") {
            push(
                `Save: starting batch of ${d.total}${
                    d.provider ? ` to ${d.provider}` : ""
                }`
            );
        } else if (d.phase === "progress") {
            push(
                `Save: ${fmtProgress(
                    d.where,
                    d.current,
                    d.total,
                    d.filename,
                    d.provider,
                    d.bytes_done,
                    d.bytes_total
                )}`
            );
        } else if (d.phase === "complete") {
            push(
                `Save: completed (local: ${d.count_local || 0}, cloud: ${
                    d.count_cloud || 0
                }${d.provider ? ` to ${d.provider}` : ""})`
            );
        } else if (d.phase === "error") {
            push(`Save: error - ${d.message || "unknown"}`);
        }
    });

    // Load events
    app.api.addEventListener("comfyui.loadimageextended.status", (ev) => {
        const d = ev.detail || {};
        if (d.phase === "start") {
            push(
                `Load: starting batch of ${d.total}${
                    d.provider ? ` from ${d.provider}` : ""
                }`
            );
        } else if (d.phase === "progress") {
            push(
                `Load: ${fmtProgress(
                    d.where,
                    d.current,
                    d.total,
                    d.filename,
                    d.provider,
                    d.bytes_done,
                    d.bytes_total
                )}`
            );
        } else if (d.phase === "complete") {
            push(
                `Load: completed (${d.count || 0} items${
                    d.provider ? ` from ${d.provider}` : ""
                })`
            );
        } else if (d.phase === "error") {
            push(`Load: error - ${d.message || "unknown"}`);
        }
    });
}
