(function (global) {
    "use strict";

    var DEBOUNCE_MS = 220;

    function debounce(fn, waitMs) {
        var timerId = null;
        return function () {
            var args = arguments;
            var context = this;
            if (timerId !== null) {
                window.clearTimeout(timerId);
            }
            timerId = window.setTimeout(function () {
                fn.apply(context, args);
            }, waitMs);
        };
    }

    function filterTableRows(table, query) {
        var normalized = query.trim().toLowerCase();
        var rows = table.querySelectorAll("tbody tr");
        var visibleCount = 0;

        rows.forEach(function (row) {
            var text = row.textContent || "";
            var matches = normalized === "" || text.toLowerCase().indexOf(normalized) !== -1;
            row.hidden = !matches;
            if (matches) {
                visibleCount += 1;
            }
        });

        return visibleCount;
    }

    function initClientTableFilter(container) {
        var input = container.querySelector("[data-cf-table-filter-input]");
        var table = container.parentElement
            ? container.parentElement.querySelector(".table-wrap table.data-table")
            : null;

        if (!input || !table) {
            return;
        }

        var status = container.querySelector("[data-cf-table-filter-status]");
        var runFilter = debounce(function () {
            var visibleCount = filterTableRows(table, input.value);
            if (status) {
                if (input.value.trim() === "") {
                    status.textContent = "";
                } else {
                    status.textContent =
                        visibleCount + " visible row(s) on this page (client-side scan only).";
                }
            }
        }, DEBOUNCE_MS);

        input.addEventListener("input", runFilter);
    }

    function initTableControls() {
        document
            .querySelectorAll("[data-cf-client-table-filter]")
            .forEach(initClientTableFilter);
    }

    global.CF = global.CF || {};
    global.CF.tableControls = { init: initTableControls };
})(window);
