(function (global) {
    "use strict";

    var CLOSE_MS = 160;
    var openMenu = null;
    var documentHandlersBound = false;

    function prefersReducedMotion() {
        return (
            window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches
        );
    }

    function getTrigger(menu) {
        return menu.querySelector("[data-topbar-menu-trigger]");
    }

    function getPanel(menu) {
        return menu.querySelector(".topbar__menu-panel, .cf-menu-panel");
    }

    function getMenuItems(menu) {
        var panel = getPanel(menu);
        if (!panel) {
            return [];
        }
        return Array.prototype.slice.call(
            panel.querySelectorAll('[role="menuitem"]')
        );
    }

    function focusFirstMenuItem(menu) {
        var items = getMenuItems(menu);
        if (items.length) {
            items[0].focus();
        }
    }

    function resetPanelPosition(panel) {
        panel.style.left = "";
        panel.style.right = "";
    }

    function clampPanelPosition(menu) {
        var panel = getPanel(menu);
        if (!panel) {
            return;
        }

        resetPanelPosition(panel);

        var rect = panel.getBoundingClientRect();
        var margin = 8;
        if (rect.right > window.innerWidth - margin) {
            panel.style.right = "0";
            panel.style.left = "auto";
        }
        if (rect.left < margin) {
            panel.style.left = "0";
            panel.style.right = "auto";
        }
    }

    function closeMenu(menu, focusTrigger) {
        if (!menu || !menu.classList.contains("is-open")) {
            return;
        }

        var trigger = getTrigger(menu);
        var panel = getPanel(menu);
        menu.classList.remove("is-open");
        if (trigger) {
            trigger.setAttribute("aria-expanded", "false");
        }
        if (openMenu === menu) {
            openMenu = null;
        }
        if (!panel) {
            return;
        }

        if (prefersReducedMotion()) {
            panel.hidden = true;
            resetPanelPosition(panel);
            if (focusTrigger && trigger) {
                trigger.focus();
            }
            return;
        }

        var finished = false;
        function hidePanel() {
            if (finished) {
                return;
            }
            finished = true;
            panel.hidden = true;
            resetPanelPosition(panel);
        }

        panel.addEventListener(
            "transitionend",
            function onEnd(event) {
                if (event.target !== panel) {
                    return;
                }
                panel.removeEventListener("transitionend", onEnd);
                hidePanel();
            }
        );
        window.setTimeout(hidePanel, CLOSE_MS + 40);

        if (focusTrigger && trigger) {
            trigger.focus();
        }
    }

    function openMenuPanel(menu) {
        if (openMenu && openMenu !== menu) {
            closeMenu(openMenu, false);
        }

        var trigger = getTrigger(menu);
        var panel = getPanel(menu);
        if (!panel) {
            return;
        }

        panel.hidden = false;
        if (trigger) {
            trigger.setAttribute("aria-expanded", "true");
        }

        window.requestAnimationFrame(function () {
            menu.classList.add("is-open");
            clampPanelPosition(menu);
            focusFirstMenuItem(menu);
        });

        openMenu = menu;
    }

    function toggleMenu(menu) {
        if (menu.classList.contains("is-open")) {
            closeMenu(menu, false);
        } else {
            openMenuPanel(menu);
        }
    }

    function bindDocumentHandlers() {
        if (documentHandlersBound) {
            return;
        }
        documentHandlersBound = true;

        document.addEventListener("click", function (event) {
            if (!openMenu) {
                return;
            }
            if (!openMenu.contains(event.target)) {
                closeMenu(openMenu, false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape" || !openMenu) {
                return;
            }
            closeMenu(openMenu, true);
        });

        window.addEventListener("resize", function () {
            if (openMenu) {
                clampPanelPosition(openMenu);
            }
        });

        window.addEventListener(
            "scroll",
            function () {
                if (openMenu) {
                    closeMenu(openMenu, false);
                }
            },
            true
        );
    }

    function initTopbarMenus() {
        var menus = document.querySelectorAll("[data-topbar-menu]");
        if (!menus.length) {
            return;
        }

        menus.forEach(function (menu) {
            if (menu.getAttribute("data-cf-topbar-bound") === "true") {
                return;
            }
            var trigger = getTrigger(menu);
            var panel = getPanel(menu);
            if (!trigger || !panel) {
                return;
            }

            menu.setAttribute("data-cf-topbar-bound", "true");
            panel.hidden = true;
            trigger.setAttribute("aria-expanded", "false");

            trigger.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                toggleMenu(menu);
            });

            trigger.addEventListener("keydown", function (event) {
                if (event.key === "ArrowDown" && !menu.classList.contains("is-open")) {
                    event.preventDefault();
                    openMenuPanel(menu);
                }
            });

            panel.addEventListener("keydown", function (event) {
                    var items = getMenuItems(menu);
                    if (!items.length) {
                        return;
                    }
                    var index = items.indexOf(document.activeElement);
                    if (event.key === "ArrowDown") {
                        event.preventDefault();
                        items[(index + 1) % items.length].focus();
                    } else if (event.key === "ArrowUp") {
                        event.preventDefault();
                        items[(index - 1 + items.length) % items.length].focus();
                    } else if (event.key === "Home") {
                        event.preventDefault();
                        items[0].focus();
                    } else if (event.key === "End") {
                        event.preventDefault();
                        items[items.length - 1].focus();
                    }
                });
        });

        bindDocumentHandlers();
    }

    global.CF = global.CF || {};
    global.CF.topbarMenus = { init: initTopbarMenus };
})(window);
