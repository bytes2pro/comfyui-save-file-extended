export async function setupProgress(app) {
    const panelId = "cse-status-panel";
    let panel = document.getElementById(panelId);
    if (!panel) {
        panel = document.createElement("div");
        panel.id = panelId;
        panel.style.position = "fixed";
        // position restored later from localStorage (bottom-right default)
        panel.style.bottom = "12px";
        panel.style.right = "12px";
        panel.style.maxWidth = "360px";
        panel.style.maxHeight = "40vh";
        panel.style.overflow = "auto";
        panel.style.padding = "10px";
        panel.style.background = "rgba(20,20,20,0.9)";
        panel.style.color = "#fff";
        panel.style.fontSize = "12px";
        panel.style.borderRadius = "8px";
        panel.style.zIndex = 9999;
        panel.style.pointerEvents = "auto";
        panel.style.boxShadow = "0 8px 30px rgba(0,0,0,.5)";
        panel.style.backdropFilter = "blur(2px)";
        panel.style.opacity = "0";
        panel.style.transform = "translateY(6px)";
        panel.style.transition = "opacity .25s ease, transform .25s ease";

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.justifyContent = "space-between";
        header.style.marginBottom = "6px";
        header.style.cursor = "move";

        const title = document.createElement("div");
        title.textContent = "Save/Load Status";
        title.style.fontWeight = "bold";
        title.style.letterSpacing = ".2px";
        header.appendChild(title);

        const buttonsWrap = document.createElement("div");
        buttonsWrap.style.display = "flex";
        buttonsWrap.style.gap = "4px";

        const pinBtn = document.createElement("button");
        pinBtn.textContent = "📌";
        pinBtn.setAttribute("aria-label", "Pin");
        pinBtn.style.cursor = "pointer";
        pinBtn.style.border = "none";
        pinBtn.style.background = "transparent";
        pinBtn.style.color = "#bbb";
        pinBtn.style.fontSize = "14px";

        const closeBtn = document.createElement("button");
        closeBtn.textContent = "×";
        closeBtn.setAttribute("aria-label", "Close");
        closeBtn.style.cursor = "pointer";
        closeBtn.style.border = "none";
        closeBtn.style.background = "transparent";
        closeBtn.style.color = "#bbb";
        closeBtn.style.fontSize = "14px";
        closeBtn.onclick = () => hidePanel(true);

        buttonsWrap.appendChild(pinBtn);
        buttonsWrap.appendChild(closeBtn);
        header.appendChild(buttonsWrap);

        panel.appendChild(header);

        const list = document.createElement("div");
        list.id = panelId + "-list";
        list.style.display = "flex";
        list.style.flexDirection = "column";
        list.style.gap = "8px";
        panel.appendChild(list);
        document.body.appendChild(panel);
    }
    const list = document.getElementById(panelId + "-list");

    const items = new Map();
    let lastActivityTs = 0;
    let idleTimer = null;
    const idleMs = 8000; // hide after 8s of no updates
    const retainDoneMs = 5000; // keep completed/error items briefly

    // Pinning and position persistence
    const PIN_KEY = "cse:status:panel:pinned";
    const POS_KEY = "cse:status:panel:pos";
    let pinned = false;
    try {
        pinned = localStorage.getItem(PIN_KEY) === "1";
    } catch {}

    function setPinned(next) {
        pinned = !!next;
        try {
            localStorage.setItem(PIN_KEY, pinned ? "1" : "0");
        } catch {}
        const btn = panel.querySelector("button[aria-label='Pin']");
        if (btn) btn.style.color = pinned ? "#ffd66b" : "#bbb";
    }

    // Restore position if saved
    try {
        const raw = localStorage.getItem(POS_KEY);
        if (raw) {
            const p = JSON.parse(raw);
            panel.style.top = p.top ?? "";
            panel.style.left = p.left ?? "";
            panel.style.bottom = p.bottom ?? "12px";
            panel.style.right = p.right ?? "12px";
        }
    } catch {}

    function now() {
        return Date.now();
    }

    function showPanel() {
        panel.style.display = "block";
        requestAnimationFrame(() => {
            panel.style.opacity = "1";
            panel.style.transform = "translateY(0)";
        });
    }

    function hidePanel(force = false) {
        if (pinned && !force) return; // don't auto-hide when pinned
        if (force || now() - lastActivityTs >= idleMs) {
            panel.style.opacity = "0";
            panel.style.transform = "translateY(6px)";
            // delay display:none to allow fade
            setTimeout(() => {
                if (panel.style.opacity === "0") panel.style.display = "none";
            }, 260);
        }
    }

    function bumpActivity() {
        lastActivityTs = now();
        showPanel();
        if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(() => hidePanel(false), idleMs);
    }

    function truncate(text, max = 42) {
        if (!text) return "";
        return text.length > max ? text.slice(0, max - 1) + "…" : text;
    }

    function createItem(key, label, accent) {
        const container = document.createElement("div");
        container.dataset.key = key;
        container.style.background = "#121212";
        container.style.border = "1px solid #2a2a2a";
        container.style.borderLeft = `3px solid ${accent}`;
        container.style.borderRadius = "6px";
        container.style.padding = "8px";

        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.justifyContent = "space-between";
        row.style.alignItems = "center";
        row.style.marginBottom = "6px";

        const title = document.createElement("div");
        title.textContent = label;
        title.style.fontWeight = "600";
        title.style.color = "#e6e6e6";
        row.appendChild(title);

        const meta = document.createElement("div");
        meta.style.color = "#aaa";
        meta.style.fontSize = "11px";
        meta.textContent = "0%";
        row.appendChild(meta);

        const barWrap = document.createElement("div");
        barWrap.style.position = "relative";
        barWrap.style.height = "8px";
        barWrap.style.background = "#2f2f2f";
        barWrap.style.borderRadius = "999px";
        barWrap.style.overflow = "hidden";

        const bar = document.createElement("div");
        bar.style.position = "absolute";
        bar.style.left = "0";
        bar.style.top = "0";
        bar.style.bottom = "0";
        bar.style.width = "0%";
        bar.style.background = accent;
        bar.style.transition = "width .2s ease";
        barWrap.appendChild(bar);

        const detail = document.createElement("div");
        detail.style.marginTop = "6px";
        detail.style.color = "#bbb";
        detail.style.fontSize = "11px";
        detail.textContent = "";

        container.appendChild(row);
        container.appendChild(barWrap);
        container.appendChild(detail);

        list.appendChild(container);
        items.set(key, {
            container,
            title,
            meta,
            bar,
            detail,
            createdAt: now(),
        });
        return items.get(key);
    }

    function updateItem(key, pct, detailText) {
        const it = items.get(key);
        if (!it) return;
        const clamped = Math.max(0, Math.min(100, Math.round(pct || 0)));
        it.bar.style.width = clamped + "%";
        it.meta.textContent = clamped + "%";
        if (detailText) it.detail.textContent = detailText;
    }

    function completeItem(key, kind) {
        const it = items.get(key);
        if (!it) return;
        const doneColor = kind === "error" ? "#c94949" : "#49c96b";
        it.bar.style.background = doneColor;
        it.meta.textContent = kind === "error" ? "Error" : "Done";
        // remove after a short delay
        setTimeout(() => {
            if (it.container && it.container.parentNode) {
                it.container.parentNode.removeChild(it.container);
                items.delete(key);
            }
            if (list.children.length === 0) hidePanel(false);
        }, retainDoneMs);
    }

    function calcPct(d) {
        const useBytes =
            d?.bytes_done !== undefined &&
            d?.bytes_total !== undefined &&
            d?.bytes_total;
        if (useBytes) return (d.bytes_done / Math.max(1, d.bytes_total)) * 100;
        if (d?.total) return (d.current / Math.max(1, d.total)) * 100;
        return 0;
    }

    function detailText(prefix, d) {
        const base = d?.bytes_total
            ? `${d.bytes_done}/${d.bytes_total} bytes`
            : d?.total
            ? `${d.current}/${d.total}`
            : "";
        const file = d?.filename ? ` - ${truncate(d.filename, 48)}` : "";
        const provider = d?.provider ? ` (${d.provider})` : "";
        return `${prefix} ${base}${file}${provider}`.trim();
    }

    function keyFor(kind, d) {
        const provider =
            d?.provider ||
            (kind === "load" ? d?.where || "local" : d?.where || "local");
        return `${kind}:${provider}`;
    }

    function ensureItem(kind, d, resourceLabel = "images") {
        const accent = kind === "save" ? "#4aa3ff" : "#b78cff";
        const provider = d?.provider
            ? ` ${kind === "save" ? "to" : "from"} ${d.provider}`
            : "";
        const label = `${
            kind === "save" ? "Saving" : "Loading"
        } ${resourceLabel}${provider}`;
        const key = keyFor(kind, d);
        return items.get(key) || createItem(key, label, accent);
    }

    // Save events
    app.api.addEventListener("comfyui.saveimageextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("save", d);
        if (d.phase === "start") {
            const it = ensureItem("save", d, "images");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("save", d, "images");
            updateItem(key, calcPct(d), detailText("Saving", d));
        } else if (d.phase === "complete") {
            ensureItem("save", d, "images");
            const parts = [];
            if (typeof d.count_local === "number")
                parts.push(`${d.count_local} local`);
            if (typeof d.count_cloud === "number")
                parts.push(`${d.count_cloud} cloud`);
            updateItem(
                key,
                100,
                `Completed ${parts.join(" and ") || ""}`.trim()
            );
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("save", d, "images");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Load events
    app.api.addEventListener("comfyui.loadimageextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("load", d);
        if (d.phase === "start") {
            const it = ensureItem("load", d, "images");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("load", d, "images");
            updateItem(key, calcPct(d), detailText("Loading", d));
        } else if (d.phase === "complete") {
            ensureItem("load", d, "images");
            updateItem(key, 100, `Completed ${d.count || 0} item(s)`);
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("load", d, "images");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Audio save events
    app.api.addEventListener("comfyui.saveaudioextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("save", d);
        if (d.phase === "start") {
            ensureItem("save", d, "audio");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("save", d, "audio");
            updateItem(key, calcPct(d), detailText("Saving", d));
        } else if (d.phase === "complete") {
            ensureItem("save", d, "audio");
            const parts = [];
            if (typeof d.count_local === "number")
                parts.push(`${d.count_local} local`);
            if (typeof d.count_cloud === "number")
                parts.push(`${d.count_cloud} cloud`);
            updateItem(
                key,
                100,
                `Completed ${parts.join(" and ") || ""}`.trim()
            );
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("save", d, "audio");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Audio load events
    app.api.addEventListener("comfyui.loadaudioextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("load", d);
        if (d.phase === "start") {
            ensureItem("load", d, "audio");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("load", d, "audio");
            updateItem(key, calcPct(d), detailText("Loading", d));
        } else if (d.phase === "complete") {
            ensureItem("load", d, "audio");
            updateItem(key, 100, `Completed ${d.count || 0} item(s)`);
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("load", d, "audio");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Video save events
    app.api.addEventListener("comfyui.savevideoextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("save", d);
        if (d.phase === "start") {
            ensureItem("save", d, "video");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("save", d, "video");
            updateItem(key, calcPct(d), detailText("Saving", d));
        } else if (d.phase === "complete") {
            ensureItem("save", d, "video");
            const parts = [];
            if (typeof d.count_local === "number")
                parts.push(`${d.count_local} local`);
            if (typeof d.count_cloud === "number")
                parts.push(`${d.count_cloud} cloud`);
            updateItem(
                key,
                100,
                `Completed ${parts.join(" and ") || ""}`.trim()
            );
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("save", d, "video");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Video load events
    app.api.addEventListener("comfyui.loadvideoextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("load", d);
        if (d.phase === "start") {
            ensureItem("load", d, "video");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("load", d, "video");
            updateItem(key, calcPct(d), detailText("Loading", d));
        } else if (d.phase === "complete") {
            ensureItem("load", d, "video");
            updateItem(key, 100, `Completed ${d.count || 0} item(s)`);
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("load", d, "video");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Workflow save events
    app.api.addEventListener("comfyui.saveworkflowextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("save", d);
        if (d.phase === "start") {
            ensureItem("save", d, "workflows");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("save", d, "workflows");
            updateItem(key, calcPct(d), detailText("Saving", d));
        } else if (d.phase === "complete") {
            ensureItem("save", d, "workflows");
            const parts = [];
            if (typeof d.count_local === "number")
                parts.push(`${d.count_local} local`);
            if (typeof d.count_cloud === "number")
                parts.push(`${d.count_cloud} cloud`);
            updateItem(
                key,
                100,
                `Completed ${parts.join(" and ") || ""}`.trim()
            );
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("save", d, "workflows");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // Workflow load events
    app.api.addEventListener("comfyui.loadworkflowextended.status", (ev) => {
        const d = ev.detail || {};
        bumpActivity();
        const key = keyFor("load", d);
        if (d.phase === "start") {
            ensureItem("load", d, "workflows");
            updateItem(key, 0, detailText("Starting", d));
        } else if (d.phase === "progress") {
            ensureItem("load", d, "workflows");
            updateItem(key, calcPct(d), detailText("Loading", d));
        } else if (d.phase === "complete") {
            ensureItem("load", d, "workflows");
            updateItem(key, 100, `Completed ${d.count || 0} item(s)`);
            completeItem(key, "ok");
        } else if (d.phase === "error") {
            ensureItem("load", d, "workflows");
            updateItem(key, undefined, `Error: ${d.message || "unknown"}`);
            completeItem(key, "error");
        }
    });

    // If mouse moves over the panel, keep it visible
    panel.addEventListener("mouseenter", () => {
        showPanel();
        if (idleTimer) clearTimeout(idleTimer);
    });
    panel.addEventListener("mouseleave", () => {
        bumpActivity();
    });

    // Pin toggle
    const pinBtnEl = panel.querySelector("button[aria-label='Pin']");
    if (pinBtnEl) {
        setPinned(pinned);
        pinBtnEl.addEventListener("click", (e) => {
            e.stopPropagation();
            setPinned(!pinned);
            if (pinned) showPanel();
        });
    }

    // Drag to move via header
    const headerEl = panel.firstChild;
    let dragging = false;
    let startX = 0,
        startY = 0;
    let startTop = 0,
        startLeft = 0;
    function savePos() {
        try {
            const rect = panel.getBoundingClientRect();
            const pos = {
                top: rect.top + "px",
                left: rect.left + "px",
                bottom: "",
                right: "",
            };
            panel.style.top = pos.top;
            panel.style.left = pos.left;
            panel.style.bottom = "";
            panel.style.right = "";
            localStorage.setItem(POS_KEY, JSON.stringify(pos));
        } catch {}
    }
    function onMove(ev) {
        if (!dragging) return;
        const x = ev.touches ? ev.touches[0].clientX : ev.clientX;
        const y = ev.touches ? ev.touches[0].clientY : ev.clientY;
        const dx = x - startX;
        const dy = y - startY;
        panel.style.top = startTop + dy + "px";
        panel.style.left = startLeft + dx + "px";
        panel.style.bottom = "";
        panel.style.right = "";
    }
    function endDrag() {
        if (!dragging) return;
        dragging = false;
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", endDrag);
        document.removeEventListener("touchmove", onMove);
        document.removeEventListener("touchend", endDrag);
        savePos();
    }
    if (headerEl) {
        headerEl.addEventListener("mousedown", (e) => {
            if (
                e.target.getAttribute("aria-label") === "Close" ||
                e.target.getAttribute("aria-label") === "Pin"
            )
                return;
            dragging = true;
            const rect = panel.getBoundingClientRect();
            startX = e.clientX;
            startY = e.clientY;
            startTop = rect.top;
            startLeft = rect.left;
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", endDrag);
        });
        headerEl.addEventListener("touchstart", (e) => {
            const t = e.touches[0];
            dragging = true;
            const rect = panel.getBoundingClientRect();
            startX = t.clientX;
            startY = t.clientY;
            startTop = rect.top;
            startLeft = rect.left;
            document.addEventListener("touchmove", onMove, { passive: true });
            document.addEventListener("touchend", endDrag);
        });
    }
}
