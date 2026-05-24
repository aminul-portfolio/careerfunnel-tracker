(function () {
    var docEl = document.documentElement;
    docEl.classList.remove("no-js");
    docEl.classList.add("cf-js-ready");

    var path = window.location.pathname;
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

    var toggle = document.getElementById("mobile-nav-toggle");
    var overlay = document.getElementById("sidebar-overlay");
    var sidebar = document.getElementById("app-sidebar");

    function setDrawerOpen(isOpen) {
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

    function closeDrawer() {
        setDrawerOpen(false);
    }

    function openDrawer() {
        setDrawerOpen(true);
    }

    if (toggle) {
        toggle.addEventListener("click", function () {
            var isOpen = docEl.classList.contains("cf-sidebar-open");
            if (isOpen) {
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
})();
