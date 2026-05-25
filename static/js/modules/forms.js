(function (global) {
    "use strict";

    function markDirty(form) {
        form.setAttribute("data-cf-dirty", "true");
    }

    function clearDirty(form) {
        form.removeAttribute("data-cf-dirty");
    }

    function setSubmitLoading(form) {
        var submitButton = form.querySelector(
            'button[type="submit"], input[type="submit"]'
        );
        if (!submitButton || submitButton.disabled) {
            return;
        }
        submitButton.classList.add("cf-btn-loading");
        submitButton.setAttribute("aria-busy", "true");
        if (!submitButton.getAttribute("data-cf-original-label")) {
            submitButton.setAttribute(
                "data-cf-original-label",
                submitButton.textContent || submitButton.value || "Submit"
            );
        }
        var label = submitButton.getAttribute("data-cf-original-label");
        if (submitButton.tagName === "BUTTON") {
            submitButton.textContent = label + "...";
        } else {
            submitButton.value = label + "...";
        }
    }

    function initUnsavedWarnings() {
        document
            .querySelectorAll('form.form-stack[method="post"], form.delete-actions[method="post"]')
            .forEach(function (form) {
                form.addEventListener("input", function () {
                    markDirty(form);
                });
                form.addEventListener("change", function () {
                    markDirty(form);
                });
                form.addEventListener("submit", function () {
                    clearDirty(form);
                    setSubmitLoading(form);
                });
            });

        window.addEventListener("beforeunload", function (event) {
            var dirtyForms = document.querySelectorAll('form[data-cf-dirty="true"]');
            if (dirtyForms.length === 0) {
                return;
            }
            event.preventDefault();
            event.returnValue = "";
        });
    }

    global.CF = global.CF || {};
    global.CF.forms = { init: initUnsavedWarnings };
})(window);
