import { beforeRegisterNodeDef as uiBeforeRegisterNodeDef } from "./enhance-ui.js";
import { setupProgress } from "./progress.js";
import { setupToasts } from "./toasts.js";
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "comfyui.savefileextended",
    async setup(app) {
        await Promise.all([setupProgress(app), setupToasts(app)]);
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        await uiBeforeRegisterNodeDef(nodeType, nodeData, app);
    },
});
