// Drag and drop for the upload form: files dropped on the zone go into its file
// input. Without JavaScript the zone is still a label that opens the file picker.
// File names come from the user's disk, so they are only ever set with textContent.
(function () {
    "use strict";

    var zone = document.querySelector("[data-dropzone]");
    if (!zone) return;
    var input = zone.querySelector("input[type=file]");
    var list = zone.querySelector("[data-dropzone-files]");
    var accepted = /\.(xls|xlsx)$/i;
    // The list below replaces the native "Choose files" text
    zone.classList.add("enhanced");

    function showFiles() {
        var names = Array.prototype.map.call(input.files, function (f) { return f.name; });
        list.textContent = names.length ? names.join(", ") : "Ningún archivo elegido";
    }

    function hasFiles(event) {
        return event.dataTransfer && Array.prototype.indexOf.call(event.dataTransfer.types, "Files") !== -1;
    }

    // A file dropped next to the zone would make the browser open it and leave the page
    ["dragover", "drop"].forEach(function (type) {
        window.addEventListener(type, function (event) {
            if (hasFiles(event)) event.preventDefault();
        });
    });

    // dragenter/dragleave also fire for the zone's children, so count them
    var depth = 0;
    zone.addEventListener("dragenter", function (event) {
        if (!hasFiles(event)) return;
        depth += 1;
        zone.classList.add("drag");
    });
    zone.addEventListener("dragleave", function () {
        depth = Math.max(0, depth - 1);
        if (!depth) zone.classList.remove("drag");
    });
    zone.addEventListener("dragover", function (event) {
        if (!hasFiles(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
    });
    zone.addEventListener("drop", function (event) {
        if (!hasFiles(event)) return;
        event.preventDefault();
        depth = 0;
        zone.classList.remove("drag");

        var files = new DataTransfer();
        Array.prototype.forEach.call(event.dataTransfer.files, function (f) {
            if (accepted.test(f.name)) files.items.add(f);
        });
        if (!files.files.length) {
            list.textContent = "Solo se aceptan archivos .xls o .xlsx.";
            return;
        }
        input.files = files.files;
        showFiles();
    });

    input.addEventListener("change", showFiles);
    showFiles();
})();
