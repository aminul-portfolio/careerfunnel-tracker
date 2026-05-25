(function (global) {
    "use strict";

    var TOAST_DURATION_MS = 3200;

    function ensureRoot() {
        var root = document.getElementById("cf-toast-root");
        if (!root) {
            root = document.createElement("div");
            root.id = "cf-toast-root";
            root.className = "cf-toast-root";
            root.setAttribute("aria-live", "polite");
            root.setAttribute("aria-atomic", "true");
            document.body.appendChild(root);
        }
        return root;
    }

    function show(message) {
        if (!message) {
            return;
        }
        var root = ensureRoot();
        var toast = document.createElement("div");
        toast.className = "cf-toast";
        toast.setAttribute("role", "status");
        toast.textContent = message;
        root.appendChild(toast);
        window.setTimeout(function () {
            toast.classList.add("cf-toast--hide");
            window.setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 220);
        }, TOAST_DURATION_MS);
    }

    global.CF = global.CF || {};
    global.CF.toast = { show: show };
})(window);
