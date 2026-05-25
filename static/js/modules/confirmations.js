(function (global) {
    "use strict";

    function bindConfirm(target) {
        var message = target.getAttribute("data-cf-confirm");
        if (!message) {
            return;
        }
        target.addEventListener("click", function (event) {
            if (!window.confirm(message)) {
                event.preventDefault();
                event.stopPropagation();
            }
        });
    }

    function initConfirmations() {
        document.querySelectorAll("[data-cf-confirm]").forEach(function (element) {
            bindConfirm(element);
        });

        document.querySelectorAll("form[data-cf-confirm]").forEach(function (form) {
            var message = form.getAttribute("data-cf-confirm");
            if (!message) {
                return;
            }
            form.addEventListener("submit", function (event) {
                if (!window.confirm(message)) {
                    event.preventDefault();
                }
            });
        });
    }

    global.CF = global.CF || {};
    global.CF.confirmations = { init: initConfirmations };
})(window);
