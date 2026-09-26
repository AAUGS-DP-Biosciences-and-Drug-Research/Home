// Live filter for the supervisor grid (works with Zensical/Material instant navigation).
function dpInitFilter() {
  const bar = document.querySelector("[data-dp-filter]");
  if (!bar || bar.dataset.ready) return;
  bar.dataset.ready = "1";
  const search = bar.querySelector("[data-dp-search]");
  const subject = bar.querySelector("[data-dp-subject]");
  const count = bar.querySelector("[data-dp-count]");
  const people = [...document.querySelectorAll(".dp-person")];
  const sections = [...document.querySelectorAll(".dp-subject")];
  const apply = () => {
    const q = search.value.trim().toLowerCase();
    const s = subject.value;
    let shown = 0;
    people.forEach((p) => {
      const ok = (!s || p.dataset.subject === s) && (!q || p.dataset.search.includes(q));
      p.hidden = !ok;
      if (ok) shown++;
    });
    sections.forEach((sec) => { sec.hidden = !sec.querySelector(".dp-person:not([hidden])"); });
    count.textContent = `${shown} of ${people.length} supervisors`;
  };
  search.addEventListener("input", apply);
  subject.addEventListener("change", apply);
  apply();
}
if (typeof document$ !== "undefined") document$.subscribe(dpInitFilter);
else document.addEventListener("DOMContentLoaded", dpInitFilter);
