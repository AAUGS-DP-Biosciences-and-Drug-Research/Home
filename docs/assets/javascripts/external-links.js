// Open links to other websites in a new tab.
function dpOpenExternalLinksInNewTab() {
  document.querySelectorAll("a[href]").forEach((link) => {
    const url = new URL(link.href, window.location.href);

    if (!["http:", "https:"].includes(url.protocol)) return;
    if (url.origin === window.location.origin) return;

    link.target = "_blank";
    link.relList.add("noopener", "noreferrer");
  });
}

if (typeof document$ !== "undefined") {
  document$.subscribe(dpOpenExternalLinksInNewTab);
} else {
  document.addEventListener("DOMContentLoaded", dpOpenExternalLinksInNewTab);
}
