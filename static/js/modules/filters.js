(function (global) {
    "use strict";

    function initReportFilterHints() {
        document.querySelectorAll(".cf-report-filter-bar").forEach(function (form) {
            if (form.getAttribute("data-cf-filter-hint-bound") === "true") {
                return;
            }
            form.setAttribute("data-cf-filter-hint-bound", "true");
            var note = document.createElement("p");
            note.className = "cf-report-filter-hint";
            note.textContent =
                "Server-side filters: click Apply filters to reload results. " +
                "This form does not auto-submit.";
            form.appendChild(note);
        });
    }

    global.CF = global.CF || {};
    global.CF.filters = { init: initReportFilterHints };
})(window);
