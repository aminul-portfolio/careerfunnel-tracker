/**
 * Sprint 52 - local weekly trend chart (SVG/CSS, saved-record data only).
 * No fetch, polling, intervals, remote scripts, or external APIs.
 */
(function () {
    "use strict";

    var CHART_WIDTH = 800;
    var CHART_HEIGHT = 280;
    var PAD_LEFT = 48;
    var PAD_RIGHT = 16;
    var PAD_TOP = 20;
    var PAD_BOTTOM = 52;
    var PLOT_WIDTH = CHART_WIDTH - PAD_LEFT - PAD_RIGHT;
    var PLOT_HEIGHT = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;

    function shortLabel(isoDate) {
        if (!isoDate || isoDate.length < 10) {
            return isoDate || "";
        }
        var parts = isoDate.split("-");
        var months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ];
        var monthIndex = parseInt(parts[1], 10) - 1;
        var month = months[monthIndex] || parts[1];
        return month + " " + parseInt(parts[2], 10);
    }

    function buildPoints(values, maxValue, count) {
        var points = [];
        var step = count > 1 ? PLOT_WIDTH / (count - 1) : 0;
        var i;
        for (i = 0; i < count; i += 1) {
            var value = values[i] || 0;
            var x = PAD_LEFT + step * i;
            var y =
                PAD_TOP +
                PLOT_HEIGHT -
                (maxValue > 0 ? (value / maxValue) * PLOT_HEIGHT : 0);
            points.push(x.toFixed(1) + "," + y.toFixed(1));
        }
        return points.join(" ");
    }

    function buildAreaPoints(values, maxValue, count) {
        var line = buildPoints(values, maxValue, count).split(" ");
        if (!line.length || line[0] === "") {
            return "";
        }
        var first = line[0].split(",");
        var last = line[line.length - 1].split(",");
        var baseline =
            (PAD_TOP + PLOT_HEIGHT).toFixed(1);
        return (
            first[0] +
            "," +
            baseline +
            " " +
            buildPoints(values, maxValue, count) +
            " " +
            last[0] +
            "," +
            baseline
        );
    }

    function renderWeeklyTrend(root, payload) {
        var labels = payload.labels || [];
        var applications = payload.applications || [];
        var responses = payload.responses || [];
        var count = labels.length;
        var maxValue = 1;
        var i;

        for (i = 0; i < applications.length; i += 1) {
            if (applications[i] > maxValue) {
                maxValue = applications[i];
            }
        }
        for (i = 0; i < responses.length; i += 1) {
            if (responses[i] > maxValue) {
                maxValue = responses[i];
            }
        }

        var gridLines = "";
        var tick;
        for (tick = 0; tick <= 4; tick += 1) {
            var gy = PAD_TOP + (PLOT_HEIGHT / 4) * tick;
            gridLines +=
                '<line class="cf-chart-grid-line" x1="' +
                PAD_LEFT +
                '" y1="' +
                gy +
                '" x2="' +
                (CHART_WIDTH - PAD_RIGHT) +
                '" y2="' +
                gy +
                '" />';
        }

        var xLabels = "";
        var step = count > 1 ? PLOT_WIDTH / (count - 1) : 0;
        for (i = 0; i < count; i += 1) {
            var lx = PAD_LEFT + step * i;
            xLabels +=
                '<text class="cf-chart-axis-label" x="' +
                lx +
                '" y="' +
                (CHART_HEIGHT - 12) +
                '" text-anchor="middle">' +
                shortLabel(labels[i]) +
                "</text>";
        }

        var yMaxLabel =
            '<text class="cf-chart-axis-label" x="' +
            (PAD_LEFT - 8) +
            '" y="' +
            (PAD_TOP + 4) +
            '" text-anchor="end">' +
            maxValue +
            "</text>";

        var svg =
            '<svg class="cf-chart-svg" viewBox="0 0 ' +
            CHART_WIDTH +
            " " +
            CHART_HEIGHT +
            '" role="img" aria-label="Weekly applications and responses from saved tracker records" preserveAspectRatio="xMidYMid meet">' +
            '<defs>' +
            '<linearGradient id="cf-weekly-apps-fill" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="#2563eb" stop-opacity="0.22"/>' +
            '<stop offset="100%" stop-color="#2563eb" stop-opacity="0.02"/>' +
            "</linearGradient>" +
            '<linearGradient id="cf-weekly-resp-fill" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="#16a34a" stop-opacity="0.18"/>' +
            '<stop offset="100%" stop-color="#16a34a" stop-opacity="0.02"/>' +
            "</linearGradient>" +
            "</defs>" +
            '<rect class="cf-chart-plot-bg" x="' +
            PAD_LEFT +
            '" y="' +
            PAD_TOP +
            '" width="' +
            PLOT_WIDTH +
            '" height="' +
            PLOT_HEIGHT +
            '" rx="10" />' +
            gridLines +
            yMaxLabel +
            '<polygon class="cf-chart-area cf-chart-area--applications" points="' +
            buildAreaPoints(applications, maxValue, count) +
            '" fill="url(#cf-weekly-apps-fill)" />' +
            '<polygon class="cf-chart-area cf-chart-area--responses" points="' +
            buildAreaPoints(responses, maxValue, count) +
            '" fill="url(#cf-weekly-resp-fill)" />' +
            '<polyline class="cf-chart-line cf-chart-line--applications" points="' +
            buildPoints(applications, maxValue, count) +
            '" />' +
            '<polyline class="cf-chart-line cf-chart-line--responses" points="' +
            buildPoints(responses, maxValue, count) +
            '" />' +
            xLabels +
            "</svg>";

        var legend =
            '<div class="cf-chart-legend">' +
            '<span class="cf-chart-legend-item"><span class="cf-chart-legend-swatch cf-chart-legend-swatch--applications"></span>Applications</span>' +
            '<span class="cf-chart-legend-item"><span class="cf-chart-legend-swatch cf-chart-legend-swatch--responses"></span>Responses</span>' +
            "</div>";

        root.innerHTML = legend + svg;
        root.classList.add("cf-chart-canvas--ready");
    }

    function initWeeklyTrendCharts() {
        var roots = document.querySelectorAll("[data-cf-weekly-trend-chart]");
        var idx;
        for (idx = 0; idx < roots.length; idx += 1) {
            var root = roots[idx];
            var dataId = root.getAttribute("data-chart-source");
            if (!dataId) {
                continue;
            }
            var dataEl = document.getElementById(dataId);
            if (!dataEl) {
                continue;
            }
            try {
                var payload = JSON.parse(dataEl.textContent);
                renderWeeklyTrend(root, payload);
            } catch (err) {
                root.classList.add("cf-chart-canvas--error");
            }
        }
    }

    window.CF = window.CF || {};
    window.CF.funnelCharts = {
        init: initWeeklyTrendCharts,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWeeklyTrendCharts);
    } else {
        initWeeklyTrendCharts();
    }
})();
