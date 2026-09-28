// Open links to other websites in a new tab.
function dpOpenExternalLinksInNewTab() {
  document.querySelectorAll("a[href]").forEach((link) => {
    let url;
    try {
      url = new URL(link.href, window.location.href);
    } catch {
      return; // unparseable href: leave this link alone, keep processing the rest
    }

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
