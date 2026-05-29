/**
 * Sprint 52 - local Funnel Metrics SVG charts (saved-record data only).
 * No fetch, polling, intervals, remote scripts, or external APIs.
 */
(function () {
    "use strict";

    var CHART_WIDTH = 800;
    var CHART_HEIGHT = 280;
    var BAR_CHART_HEIGHT = 300;
    var PAD_LEFT = 48;
    var PAD_RIGHT = 16;
    var PAD_TOP = 20;
    var PAD_BOTTOM = 52;
    var PLOT_WIDTH = CHART_WIDTH - PAD_LEFT - PAD_RIGHT;
    var PLOT_HEIGHT = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;

    function escapeSvgText(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function maxInList(values) {
        var maxValue = 1;
        var i;
        for (i = 0; i < values.length; i += 1) {
            if (values[i] > maxValue) {
                maxValue = values[i];
            }
        }
        return maxValue;
    }

    function mountChart(root, legendHtml, svgHtml) {
        root.innerHTML = legendHtml + svgHtml;
        root.classList.add("cf-chart-canvas--ready");
    }

    function readPayload(root) {
        var dataId = root.getAttribute("data-chart-source");
        if (!dataId) {
            return null;
        }
        var dataEl = document.getElementById(dataId);
        if (!dataEl) {
            return null;
        }
        return JSON.parse(dataEl.textContent);
    }

    function shortLabel(isoDate) {
        if (!isoDate || isoDate.length < 10) {
            return isoDate || "";
        }
        var parts = isoDate.split("-");
        var months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
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
        var baseline = (PAD_TOP + PLOT_HEIGHT).toFixed(1);
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
        if (!payload || !payload.labels || !payload.labels.length) {
            return;
        }
        var labels = payload.labels || [];
        var applications = payload.applications || [];
        var responses = payload.responses || [];
        var count = labels.length;
        var maxValue = maxInList(applications.concat(responses));

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
        var i;
        for (i = 0; i < count; i += 1) {
            var lx = PAD_LEFT + step * i;
            xLabels +=
                '<text class="cf-chart-axis-label" x="' +
                lx +
                '" y="' +
                (CHART_HEIGHT - 12) +
                '" text-anchor="middle">' +
                escapeSvgText(shortLabel(labels[i])) +
                "</text>";
        }

        var svg =
            '<svg class="cf-chart-svg" viewBox="0 0 ' +
            CHART_WIDTH +
            " " +
            CHART_HEIGHT +
            '" role="img" aria-label="Weekly applications and responses from saved tracker records" preserveAspectRatio="xMidYMid meet">' +
            '<defs><linearGradient id="cf-weekly-apps-fill" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="#2563eb" stop-opacity="0.22"/>' +
            '<stop offset="100%" stop-color="#2563eb" stop-opacity="0.02"/>' +
            "</linearGradient>" +
            '<linearGradient id="cf-weekly-resp-fill" x1="0" y1="0" x2="0" y2="1">' +
            '<stop offset="0%" stop-color="#16a34a" stop-opacity="0.18"/>' +
            '<stop offset="100%" stop-color="#16a34a" stop-opacity="0.02"/>' +
            "</linearGradient></defs>" +
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

        mountChart(
            root,
            '<div class="cf-chart-legend">' +
                '<span class="cf-chart-legend-item"><span class="cf-chart-legend-swatch cf-chart-legend-swatch--applications"></span>Applications</span>' +
                '<span class="cf-chart-legend-item"><span class="cf-chart-legend-swatch cf-chart-legend-swatch--responses"></span>Responses</span>' +
                "</div>",
            svg
        );
    }

    function renderHorizontalBars(root, payload, kind) {
        var items = payload.stages || payload.segments || [];
        if (!payload.has_data || !items.length) {
            return;
        }
        var maxValue = maxInList(items.map(function (item) {
            return item.count || 0;
        }));
        var barHeight = 28;
        var gap = 12;
        var labelWidth = 160;
        var barStart = labelWidth + 12;
        var barMaxWidth = CHART_WIDTH - barStart - PAD_RIGHT;
        var totalHeight = PAD_TOP + items.length * (barHeight + gap) + 24;
        var svgParts = [
            '<svg class="cf-chart-svg cf-chart-svg--bars" viewBox="0 0 ',
            CHART_WIDTH,
            " ",
            totalHeight,
            '" role="img" aria-label="',
            escapeSvgText(kind),
            ' from saved tracker records" preserveAspectRatio="xMidYMid meet">',
        ];
        var idx;
        for (idx = 0; idx < items.length; idx += 1) {
            var item = items[idx];
            var count = item.count || 0;
            var y = PAD_TOP + idx * (barHeight + gap);
            var width = maxValue > 0 ? (count / maxValue) * barMaxWidth : 0;
            var rate = item.rate ? " (" + escapeSvgText(item.rate) + ")" : "";
            svgParts.push(
                '<text class="cf-chart-axis-label cf-chart-bar-label" x="8" y="' +
                    (y + barHeight * 0.65) +
                    '">' +
                    escapeSvgText(item.label) +
                    "</text>"
            );
            svgParts.push(
                '<rect class="cf-chart-bar-track" x="' +
                    barStart +
                    '" y="' +
                    y +
                    '" width="' +
                    barMaxWidth +
                    '" height="' +
                    barHeight +
                    '" rx="8" />'
            );
            svgParts.push(
                '<rect class="cf-chart-bar-fill cf-chart-bar-fill--primary" x="' +
                    barStart +
                    '" y="' +
                    y +
                    '" width="' +
                    Math.max(width, count > 0 ? 4 : 0) +
                    '" height="' +
                    barHeight +
                    '" rx="8" />'
            );
            svgParts.push(
                '<text class="cf-chart-bar-value" x="' +
                    (barStart + barMaxWidth + 8) +
                    '" y="' +
                    (y + barHeight * 0.65) +
                    '">' +
                    count +
                    rate +
                    "</text>"
            );
        }
        svgParts.push("</svg>");
        mountChart(root, "", svgParts.join(""));
    }

    function renderGroupedBars(root, payload, title) {
        if (!payload.has_data || !payload.labels || !payload.labels.length) {
            return;
        }
        var labels = payload.labels;
        var seriesList = payload.series || [
            {
                key: "applications",
                label: "Applications",
                values: payload.applications || [],
                className: "applications",
            },
            {
                key: "responses",
                label: "Responses",
                values: payload.responses || [],
                className: "responses",
            },
        ];
        if (payload.interviews) {
            seriesList.push({
                key: "interviews",
                label: "Interviews",
                values: payload.interviews,
                className: "interviews",
            });
        }
        var allValues = [];
        var s;
        for (s = 0; s < seriesList.length; s += 1) {
            allValues = allValues.concat(seriesList[s].values || []);
        }
        var maxValue = maxInList(allValues);
        var groupCount = labels.length;
        var groupWidth = Math.min(72, (PLOT_WIDTH / groupCount) * 0.85);
        var barWidth = Math.max(8, (groupWidth / seriesList.length) - 4);
        var chartH = BAR_CHART_HEIGHT;
        var plotH = chartH - PAD_TOP - PAD_BOTTOM;
        var legend = '<div class="cf-chart-legend">';
        for (s = 0; s < seriesList.length; s += 1) {
            legend +=
                '<span class="cf-chart-legend-item"><span class="cf-chart-legend-swatch cf-chart-legend-swatch--' +
                seriesList[s].className +
                '"></span>' +
                escapeSvgText(seriesList[s].label) +
                "</span>";
        }
        legend += "</div>";

        var svg =
            '<svg class="cf-chart-svg cf-chart-svg--grouped" viewBox="0 0 ' +
            CHART_WIDTH +
            " " +
            chartH +
            '" role="img" aria-label="' +
            escapeSvgText(title) +
            ' from saved tracker records" preserveAspectRatio="xMidYMid meet">';
        var slotWidth = PLOT_WIDTH / groupCount;
        var g;
        for (g = 0; g < groupCount; g += 1) {
            var groupX = PAD_LEFT + slotWidth * g + (slotWidth - groupWidth) / 2;
            groupX = Math.max(PAD_LEFT, groupX);
            var b;
            for (b = 0; b < seriesList.length; b += 1) {
                var val = (seriesList[b].values || [])[g] || 0;
                var h = maxValue > 0 ? (val / maxValue) * plotH : 0;
                var bx = groupX + b * (barWidth + 4) + 2;
                var by = PAD_TOP + plotH - h;
                svg +=
                    '<rect class="cf-chart-bar-fill cf-chart-bar-fill--' +
                    seriesList[b].className +
                    '" x="' +
                    bx +
                    '" y="' +
                    by +
                    '" width="' +
                    barWidth +
                    '" height="' +
                    Math.max(h, val > 0 ? 3 : 0) +
                    '" rx="4" />';
            }
            svg +=
                '<text class="cf-chart-axis-label" x="' +
                (groupX + groupWidth / 2) +
                '" y="' +
                (chartH - 10) +
                '" text-anchor="middle">' +
                escapeSvgText(labels[g]) +
                "</text>";
        }
        svg += "</svg>";
        mountChart(root, legend, svg);
    }

    function initChartGroup(selector, renderer) {
        var roots = document.querySelectorAll(selector);
        var idx;
        for (idx = 0; idx < roots.length; idx += 1) {
            var root = roots[idx];
            try {
                var payload = readPayload(root);
                if (payload) {
                    renderer(root, payload);
                }
            } catch (err) {
                root.classList.add("cf-chart-canvas--error");
            }
        }
    }

    function initAllCharts() {
        initChartGroup("[data-cf-weekly-trend-chart]", renderWeeklyTrend);
        initChartGroup("[data-cf-funnel-conversion-chart]", function (root, payload) {
            renderHorizontalBars(root, payload, "Funnel conversion stages");
        });
        initChartGroup("[data-cf-outcome-breakdown-chart]", function (root, payload) {
            renderHorizontalBars(root, payload, "Outcome breakdown");
        });
        initChartGroup("[data-cf-source-performance-chart]", function (root, payload) {
            renderGroupedBars(root, payload, "Source performance");
        });
        initChartGroup("[data-cf-cv-performance-chart]", function (root, payload) {
            renderGroupedBars(root, payload, "CV version performance");
        });
    }

    window.CF = window.CF || {};
    window.CF.funnelCharts = {
        init: initAllCharts,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAllCharts);
    } else {
        initAllCharts();
    }
})();
