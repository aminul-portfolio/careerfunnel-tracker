(function (global) {
    "use strict";

    var STORAGE_KEY = "cf-sidebar-collapsed";

    function readCollapsedPreference() {
        try {
            return window.localStorage.getItem(STORAGE_KEY) === "1";
        } catch (error) {
            return false;
        }
    }

    function writeCollapsedPreference(isCollapsed) {
        try {
            window.localStorage.setItem(STORAGE_KEY, isCollapsed ? "1" : "0");
        } catch (error) {
            /* UI preference only - ignore storage errors */
        }
    }

    function setDrawerOpen(docEl, toggle, overlay, sidebar, isOpen) {
        docEl.classList.toggle("cf-sidebar-open", isOpen);
        if (toggle) {
            toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
            toggle.setAttribute(
                "aria-label",
                isOpen ? "Close navigation menu" : "Open navigation menu"
            );
        }
        if (overlay) {
            overlay.hidden = !isOpen;
            overlay.setAttribute("aria-hidden", isOpen ? "false" : "true");
        }
        if (sidebar) {
            var isMobile = window.matchMedia("(max-width: 900px)").matches;
            if (isMobile && !isOpen) {
                sidebar.setAttribute("aria-hidden", "true");
            } else {
                sidebar.removeAttribute("aria-hidden");
            }
        }
    }

    function setCollapsed(docEl, collapseToggle, isCollapsed) {
        docEl.classList.toggle("cf-sidebar-collapsed", isCollapsed);
        if (collapseToggle) {
            collapseToggle.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
            collapseToggle.setAttribute(
                "aria-label",
                isCollapsed ? "Expand sidebar" : "Collapse sidebar"
            );
        }
        writeCollapsedPreference(isCollapsed);
    }

    function initActiveNav(path) {
        var links = document.querySelectorAll(".sidebar-link, .cf-nav-link");
        var bestMatch = null;
        var bestLength = -1;

        links.forEach(function (link) {
            var href = link.getAttribute("href");
            if (!href) {
                return;
            }
            if (path === href || (href !== "/" && path.startsWith(href))) {
                if (href.length > bestLength) {
                    bestMatch = link;
                    bestLength = href.length;
                }
            }
        });

        if (bestMatch) {
            bestMatch.classList.add("active");
            bestMatch.setAttribute("aria-current", "page");
        }
    }

    function initSidebar() {
        var docEl = document.documentElement;
        var path = window.location.pathname;
        var toggle = document.getElementById("mobile-nav-toggle");
        var overlay = document.getElementById("sidebar-overlay");
        var sidebar = document.getElementById("app-sidebar");
        var collapseToggle = document.getElementById("sidebar-collapse-toggle");

        initActiveNav(path);

        function closeDrawer() {
            setDrawerOpen(docEl, toggle, overlay, sidebar, false);
        }

        function openDrawer() {
            setDrawerOpen(docEl, toggle, overlay, sidebar, true);
        }

        if (toggle) {
            toggle.addEventListener("click", function () {
                if (docEl.classList.contains("cf-sidebar-open")) {
                    closeDrawer();
                } else {
                    openDrawer();
                }
            });
        }

        if (overlay) {
            overlay.addEventListener("click", closeDrawer);
        }

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeDrawer();
            }
        });

        if (sidebar && window.matchMedia("(max-width: 900px)").matches) {
            sidebar.setAttribute("aria-hidden", "true");
        }

        if (collapseToggle) {
            setCollapsed(docEl, collapseToggle, readCollapsedPreference());
            collapseToggle.addEventListener("click", function () {
                var isCollapsed = !docEl.classList.contains("cf-sidebar-collapsed");
                setCollapsed(docEl, collapseToggle, isCollapsed);
            });
        }

        window.addEventListener("resize", function () {
            if (!window.matchMedia("(max-width: 900px)").matches) {
                closeDrawer();
            }
        });
    }

    global.CF = global.CF || {};
    global.CF.sidebar = { init: initSidebar };
})(window);
