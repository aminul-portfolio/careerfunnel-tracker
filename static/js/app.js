(function () {
    var path = window.location.pathname;
    var links = document.querySelectorAll(".sidebar-link");
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
    }
})();
