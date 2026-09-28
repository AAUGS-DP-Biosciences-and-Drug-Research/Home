// Live filter for the supervisor grid (works with Zensical/Material instant navigation).
// Case- and accent-insensitive: "tornroos" finds Törnroos, "strasse" finds Straße.
const dpFold = (s) => s.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/ß/g, "ss");

function dpInitFilter() {
  const bar = document.querySelector("[data-dp-filter]");
  if (!bar || bar.dataset.ready) return;
  bar.dataset.ready = "1";
  const search = bar.querySelector("[data-dp-search]");
  const subject = bar.querySelector("[data-dp-subject]");
  const count = bar.querySelector("[data-dp-count]");
  const people = [...document.querySelectorAll(".dp-person")];
  people.forEach((p) => { p.dataset.folded = dpFold(p.dataset.search); });
  const sections = [...document.querySelectorAll(".dp-subject")];
  const apply = () => {
    const q = dpFold(search.value.trim());
    const s = subject.value;
    let shown = 0;
    people.forEach((p) => {
      const ok = (!s || p.dataset.subject === s) && (!q || p.dataset.folded.includes(q));
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
