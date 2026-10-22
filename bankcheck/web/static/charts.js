// Tooltips for the charts made by bankcheck/charts.py, and the light/dark toggle.
// Everything is optional: without JavaScript the charts keep their `title` tooltips.
// Labels come from bank descriptions, so they are only ever set with textContent.
(function () {
    "use strict";

    var tip = document.createElement("div");
    tip.className = "viz-tooltip";
    tip.hidden = true;
    document.body.appendChild(tip);

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function place(x, y) {
        var w = tip.offsetWidth, h = tip.offsetHeight;
        var left = x + 14, top = y - h - 14;
        if (left + w > window.innerWidth - 8) left = x - w - 14;
        if (left < 8) left = 8;
        if (top < 8) top = y + 18;
        tip.style.left = left + "px";
        tip.style.top = top + "px";
    }

    // rows: [{value, name?, role?}]; the value leads, the series name follows
    function show(title, rows, x, y) {
        tip.replaceChildren(el("div", "viz-tooltip-title", title));
        rows.forEach(function (row) {
            var line = el("div", "viz-tooltip-row");
            if (row.role) line.appendChild(el("span", "viz-key " + row.role));
            line.appendChild(el("strong", "", row.value));
            if (row.name) line.appendChild(el("span", "viz-tooltip-name", row.name));
            tip.appendChild(line);
        });
        tip.hidden = false;
        place(x, y);
    }

    function hide() { tip.hidden = true; }

    // Bars, columns: the mark is the target
    document.addEventListener("pointerover", function (event) {
        var mark = event.target.closest && event.target.closest("[data-tip]");
        if (!mark) return;
        mark.removeAttribute("title");  // the custom tooltip replaces the native one
        mark.classList.add("is-hover");
        show(mark.dataset.tipTitle, [{ value: mark.dataset.tip }], event.clientX, event.clientY);
        mark.addEventListener("pointerleave", function () {
            mark.classList.remove("is-hover");
            hide();
        }, { once: true });
    });
    document.addEventListener("pointermove", function (event) {
        if (!tip.hidden && event.target.closest && event.target.closest("[data-tip]")) place(event.clientX, event.clientY);
    });

    // Lines: a crosshair snaps to the nearest x and the tooltip lists every series
    document.querySelectorAll(".viz-line[data-chart]").forEach(function (chart) {
        var data = JSON.parse(chart.dataset.chart);
        var plot = chart.querySelector(".viz-plot");
        var cross = plot.querySelector(".viz-cross");
        var dots = plot.querySelectorAll(".viz-hover-dot");
        var n = data.x.length;

        function at(event) {
            var box = plot.getBoundingClientRect();
            var i = Math.round((event.clientX - box.left) / box.width * (n - 1));
            i = Math.max(0, Math.min(n - 1, i));
            var left = (i / (n - 1)) * 100 + "%";
            cross.style.left = left;
            cross.hidden = false;
            var rows = [];
            data.series.forEach(function (series, k) {
                var y = series.y[i];
                dots[k].hidden = y === null;
                if (y === null) return;
                dots[k].style.left = left;
                dots[k].style.top = y + "%";
                rows.push({ value: series.v[i], name: series.name, role: series.role });
            });
            show(data.x[i], rows.length ? rows : [{ value: "Sin datos" }], event.clientX, event.clientY);
        }

        plot.addEventListener("pointermove", at);
        plot.addEventListener("pointerdown", at);
        plot.addEventListener("pointerleave", function () {
            cross.hidden = true;
            dots.forEach(function (dot) { dot.hidden = true; });
            hide();
        });
    });

    // Light / dark: follows the system until chosen; the choice is kept in this browser
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
        button.addEventListener("click", function () {
            var root = document.documentElement;
            var dark = root.dataset.theme
                ? root.dataset.theme === "dark"
                : window.matchMedia("(prefers-color-scheme: dark)").matches;
            root.dataset.theme = dark ? "light" : "dark";
            try { localStorage.setItem("bankcheck-theme", root.dataset.theme); } catch (e) { /* private mode */ }
        });
    });
})();
