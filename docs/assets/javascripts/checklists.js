// Checklist boxes (pymdownx.tasklist) are display-only; give each one the text
// of its item so screen readers announce "Update the ISP, checkbox" instead of
// an unlabelled checkbox.
function dpLabelChecklists() {
  document.querySelectorAll(".task-list-item").forEach((item) => {
    const box = item.querySelector('input[type="checkbox"]');
    if (box && !box.hasAttribute("aria-label")) box.setAttribute("aria-label", item.textContent.trim());
  });
}
if (typeof document$ !== "undefined") document$.subscribe(dpLabelChecklists);
else document.addEventListener("DOMContentLoaded", dpLabelChecklists);
