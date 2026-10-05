// Collapse groups and hosts by clicking their name. A host with nothing under
// its name (a "leaf") has nothing to collapse, so its name isn't wired.
//
// The collapsed state is rendered server-side (so nothing flashes open on
// load) and posted back here, which means it survives reloads, reboots, and
// following the page from another browser or device.
(function () {
  "use strict";

  function persist(kind, key, collapsed) {
    fetch("api/collapsed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: kind, key: key, collapsed: collapsed })
    }).catch(function () {
      // Collapsing still works for this pageview if the save fails.
    });
  }

  function wire(nameSelector, boxSelector, kind, datasetKey) {
    document.querySelectorAll(nameSelector).forEach(function (name) {
      name.addEventListener("click", function () {
        var box = name.closest(boxSelector);
        persist(kind, box.dataset[datasetKey], box.classList.toggle("collapsed"));
      });
    });
  }

  wire(".machinegroupname", ".machinegroup", "group", "group");
  wire(".machine:not(.leaf) .machinename", ".machine", "host", "host");
})();
