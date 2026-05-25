(function (global) {
    "use strict";

    function enhanceSection(section) {
        var header = section.querySelector(":scope > .card-header");
        if (!header || header.querySelector(".cf-collapse-toggle")) {
            return;
        }

        var panel = document.createElement("div");
        panel.className = "cf-collapsible-panel";
        var sibling = header.nextElementSibling;
        while (sibling) {
            var next = sibling.nextElementSibling;
            panel.appendChild(sibling);
            sibling = next;
        }
        section.appendChild(panel);

        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "cf-collapse-toggle";
        toggle.setAttribute("aria-expanded", "true");
        toggle.textContent = "Collapse section";
        header.appendChild(toggle);

        function setExpanded(isExpanded) {
            section.classList.toggle("cf-section-collapsed", !isExpanded);
            toggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
            toggle.textContent = isExpanded ? "Collapse section" : "Expand section";
        }

        toggle.addEventListener("click", function () {
            var isExpanded = toggle.getAttribute("aria-expanded") === "true";
            setExpanded(!isExpanded);
        });
    }

    function initReportAccordions() {
        document
            .querySelectorAll("[data-cf-report-accordions] .cf-report-section, [data-cf-collapsible-card]")
            .forEach(enhanceSection);
    }

    global.CF = global.CF || {};
    global.CF.reportAccordions = { init: initReportAccordions };
})(window);
