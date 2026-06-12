(function (global) {
    "use strict";

    var STORAGE_KEY = "cf-sidebar-collapsed";
    var SCROLL_STORAGE_KEY = "cf-sidebar-scroll-top";
    var DESKTOP_MEDIA = "(min-width: 901px)";

    function readStoredScrollTop() {
        try {
            var value = window.sessionStorage.getItem(SCROLL_STORAGE_KEY);
            if (value === null) {
                return null;
            }
            var parsed = parseInt(value, 10);
            return Number.isFinite(parsed) ? Math.max(0, parsed) : null;
        } catch (error) {
            return null;
        }
    }

    function writeStoredScrollTop(scrollTop) {
        try {
            window.sessionStorage.setItem(
                SCROLL_STORAGE_KEY,
                String(Math.max(0, Math.round(scrollTop)))
            );
        } catch (error) {
            /* UI preference only - ignore storage errors */
        }
    }

    function restoreSidebarScroll(sidebar) {
        if (!sidebar) {
            return;
        }
        var stored = readStoredScrollTop();
        if (stored === null) {
            return;
        }
        sidebar.scrollTop = stored;
    }

    function initSidebarScrollPersistence(sidebar) {
        if (!sidebar) {
            return;
        }

        restoreSidebarScroll(sidebar);
        window.requestAnimationFrame(function () {
            restoreSidebarScroll(sidebar);
        });

        sidebar.addEventListener(
            "scroll",
            function () {
                writeStoredScrollTop(sidebar.scrollTop);
            },
            { passive: true }
        );

        sidebar.addEventListener("click", function (event) {
            var link = event.target.closest(".sidebar-link, .cf-nav-link");
            if (link) {
                writeStoredScrollTop(sidebar.scrollTop);
            }
        });
    }

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

    function isDesktopViewport() {
        return window.matchMedia(DESKTOP_MEDIA).matches;
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
            var isMobile = !isDesktopViewport();
            if (isMobile && !isOpen) {
                sidebar.setAttribute("aria-hidden", "true");
            } else {
                sidebar.removeAttribute("aria-hidden");
            }
        }
    }

    function updateReopenButton(reopenBtn, isCollapsed) {
        if (!reopenBtn) {
            return;
        }
        reopenBtn.hidden = !isCollapsed || !isDesktopViewport();
    }

    function setCollapsed(docEl, sidebar, collapseToggle, reopenBtn, isCollapsed) {
        docEl.classList.toggle("cf-sidebar-collapsed", isCollapsed);
        if (sidebar) {
            sidebar.classList.toggle("is-collapsed", isCollapsed);
        }
        if (collapseToggle) {
            collapseToggle.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
            collapseToggle.setAttribute(
                "aria-label",
                isCollapsed ? "Expand sidebar" : "Collapse sidebar"
            );
        }
        updateReopenButton(reopenBtn, isCollapsed);
        writeCollapsedPreference(isCollapsed);
    }

    function handleCollapseToggle(docEl, sidebar, collapseToggle, reopenBtn) {
        var isCollapsed = !docEl.classList.contains("cf-sidebar-collapsed");
        setCollapsed(docEl, sidebar, collapseToggle, reopenBtn, isCollapsed);
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
        var reopenBtn = document.getElementById("sidebar-reopen-btn");

        initSidebarScrollPersistence(sidebar);
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

        if (sidebar && !isDesktopViewport()) {
            sidebar.setAttribute("aria-hidden", "true");
        }

        if (collapseToggle) {
            setCollapsed(
                docEl,
                sidebar,
                collapseToggle,
                reopenBtn,
                readCollapsedPreference()
            );
            collapseToggle.addEventListener("click", function () {
                handleCollapseToggle(docEl, sidebar, collapseToggle, reopenBtn);
            });
        }

        if (reopenBtn) {
            reopenBtn.addEventListener("click", function () {
                if (docEl.classList.contains("cf-sidebar-collapsed")) {
                    handleCollapseToggle(docEl, sidebar, collapseToggle, reopenBtn);
                }
            });
        }

        window.addEventListener("resize", function () {
            if (!isDesktopViewport()) {
                closeDrawer();
            }
            if (collapseToggle) {
                updateReopenButton(
                    reopenBtn,
                    docEl.classList.contains("cf-sidebar-collapsed")
                );
            }
        });
    }

    global.CF = global.CF || {};
    global.CF.sidebar = { init: initSidebar };
})(window);
