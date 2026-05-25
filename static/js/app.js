(function () {
    "use strict";

    var docEl = document.documentElement;
    docEl.classList.remove("no-js");
    docEl.classList.add("cf-js-ready");

    function initModules() {
        if (window.CF && window.CF.sidebar) {
            window.CF.sidebar.init();
        }
        if (window.CF && window.CF.tableControls) {
            window.CF.tableControls.init();
        }
        if (window.CF && window.CF.filters) {
            window.CF.filters.init();
        }
        if (window.CF && window.CF.forms) {
            window.CF.forms.init();
        }
        if (window.CF && window.CF.confirmations) {
            window.CF.confirmations.init();
        }
        if (window.CF && window.CF.copyEvidence) {
            window.CF.copyEvidence.init();
        }
        if (window.CF && window.CF.reportAccordions) {
            window.CF.reportAccordions.init();
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initModules);
    } else {
        initModules();
    }
})();
