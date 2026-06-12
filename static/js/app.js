(function () {
    "use strict";

    var docEl = document.documentElement;
    docEl.classList.remove("no-js");
    docEl.classList.add("cf-js-ready");

    function safeInit(moduleName, initFn) {
        if (typeof initFn !== "function") {
            return;
        }
        try {
            initFn();
        } catch (error) {
            /* One module failure must not block other UI enhancements. */
        }
    }

    function initModules() {
        var cf = window.CF || {};
        safeInit("sidebar", cf.sidebar && cf.sidebar.init);
        safeInit("tableControls", cf.tableControls && cf.tableControls.init);
        safeInit("filters", cf.filters && cf.filters.init);
        safeInit("forms", cf.forms && cf.forms.init);
        safeInit("confirmations", cf.confirmations && cf.confirmations.init);
        safeInit("copyEvidence", cf.copyEvidence && cf.copyEvidence.init);
        safeInit("reportAccordions", cf.reportAccordions && cf.reportAccordions.init);
        safeInit("downloadDropdowns", cf.downloadDropdowns && cf.downloadDropdowns.init);
        safeInit("topbarMenus", cf.topbarMenus && cf.topbarMenus.init);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initModules);
    } else {
        initModules();
    }
})();
