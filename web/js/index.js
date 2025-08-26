import { setupProgress } from "./progress.js";
import { setupToasts } from "./toasts.js";
import { beforeRegisterNodeDef as uiBeforeRegisterNodeDef } from "./ui_enhance.js";

(function registerOnceWhenAppReady() {
    if (window.__CSE_REGISTERED__) return;

    const tryRegister = () => {
        const app = window.app;
        if (!app) return false;
        if (window.__CSE_REGISTERED__) return true;
        window.__CSE_REGISTERED__ = true;

        app.registerExtension({
            name: "comfyui.savefileextended",
            async setup(app) {
                await Promise.all([setupProgress(app), setupToasts(app)]);
            },
            async beforeRegisterNodeDef(nodeType, nodeData, app) {
                await uiBeforeRegisterNodeDef(nodeType, nodeData, app);
            },
        });
        return true;
    };

    if (!tryRegister()) {
        const interval = setInterval(() => {
            if (tryRegister()) clearInterval(interval);
        }, 50);
    }
})();
