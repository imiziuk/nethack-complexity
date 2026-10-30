/* "From a random NetHack level to ours": step-through and the menu of level contents.
   Without JS every step and every reason is simply shown in order (see style.css, html:not(.js)). */
(function () {
  "use strict";
  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }

  /* ---------- stepper ---------- */
  var host = document.getElementById("lvs");
  if (host) {
    var steps = $$(".lvs-step", host), cur = 0;
    var nav = document.createElement("div");
    nav.className = "lvs-nav";
    nav.setAttribute("role", "group");
    nav.setAttribute("aria-label", "Steps");
    var prev = document.createElement("button"), next = document.createElement("button"), ctr = document.createElement("span");
    prev.type = next.type = "button";
    prev.className = "lvs-pn"; next.className = "lvs-pn";
    prev.innerHTML = "&#9664; Back"; next.innerHTML = "Next &#9654;";
    ctr.className = "lvs-ctr";
    ctr.setAttribute("aria-live", "polite");
    var idx = document.createElement("ol");
    idx.className = "lvs-idx";
    var btns = steps.map(function (st, i) {
      var li = document.createElement("li"), b = document.createElement("button");
      b.type = "button";
      b.textContent = i + ". " + (st.getAttribute("data-t") || "");
      b.addEventListener("click", function () { show(i); });
      li.appendChild(b); idx.appendChild(li);
      return b;
    });
    nav.appendChild(prev); nav.appendChild(ctr); nav.appendChild(next);
    host.insertBefore(idx, host.firstChild);
    host.insertBefore(nav, idx.nextSibling);
    prev.addEventListener("click", function () { show(cur - 1); });
    next.addEventListener("click", function () { show(cur + 1); });
    host.addEventListener("keydown", function (e) {
      if (e.target.closest && e.target.closest("pre, a")) { return; }
      if (e.key === "ArrowRight") { e.preventDefault(); show(cur + 1); next.focus(); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); show(cur - 1); prev.focus(); }
    });
    host.classList.add("on");
    function show(i) {
      cur = Math.max(0, Math.min(steps.length - 1, i));
      steps.forEach(function (st, k) { st.hidden = k !== cur; });
      btns.forEach(function (b, k) { if (k === cur) { b.setAttribute("aria-current", "step"); } else { b.removeAttribute("aria-current"); } });
      prev.disabled = cur === 0; next.disabled = cur === steps.length - 1;
      ctr.textContent = "Step " + cur + " of " + (steps.length - 1) + ": " + (steps[cur].getAttribute("data-t") || "");
      /* warm the next pictures so Next feels instant */
      var n = steps[cur + 1];
      if (n) { $$("img", n).forEach(function (im) { im.loading = "eager"; }); }
    }
    show(0);
  }

  /* ---------- menu: tap an item to open its reason under it ---------- */
  var menu = document.getElementById("lvm");
  if (menu) {
    var all = $$(".lvm-all", menu)[0], items = $$(".lvm-i", menu);
    items.forEach(function (b) {
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") !== "true";
        b.setAttribute("aria-pressed", String(on));
      });
    });
    if (all) {
      all.addEventListener("click", function () {
        var on = all.getAttribute("aria-pressed") !== "true";
        all.setAttribute("aria-pressed", String(on));
        all.textContent = on ? "Hide all reasons" : "Show all reasons";
        items.forEach(function (b) { b.setAttribute("aria-pressed", String(on)); });
      });
    }
  }
})();
