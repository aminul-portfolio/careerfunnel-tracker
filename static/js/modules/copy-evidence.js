(function (global) {
    "use strict";

    function copyText(text) {
        if (!text) {
            return Promise.reject(new Error("Nothing to copy"));
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        var textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        var succeeded = document.execCommand("copy");
        document.body.removeChild(textarea);
        return succeeded
            ? Promise.resolve()
            : Promise.reject(new Error("Copy command failed"));
    }

    function initCopyButtons() {
        document.querySelectorAll("[data-cf-copy]").forEach(function (button) {
            button.addEventListener("click", function () {
                var value = button.getAttribute("data-cf-copy") || "";
                copyText(value)
                    .then(function () {
                        if (global.CF && global.CF.toast) {
                            global.CF.toast.show("Copied to clipboard (local UI only).");
                        }
                    })
                    .catch(function () {
                        if (global.CF && global.CF.toast) {
                            global.CF.toast.show("Copy failed - select the text manually.");
                        }
                    });
            });
        });
    }

    global.CF = global.CF || {};
    global.CF.copyEvidence = { init: initCopyButtons };
})(window);
