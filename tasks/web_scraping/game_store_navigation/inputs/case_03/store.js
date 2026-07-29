// Flash-sale price is computed client-side from data attributes — never
// present as a literal number in the page source. A scraper that only reads
// raw HTML sees "computing…"; it has to execute this script.
(function () {
  var el = document.getElementById("flash-price");
  if (!el) return;
  var base = parseFloat(el.dataset.basePrice);
  var discount = parseFloat(el.dataset.discount);
  var final = Math.round(base * (1 - discount / 100) * 100) / 100;
  el.textContent = "$" + final.toFixed(2);
  // Set the USD reference price so common.js's region conversion (which runs
  // on DOMContentLoaded, after this) can override the display currency.
  el.dataset.usdPrice = final.toFixed(2);
})();

// Countdown is cosmetic (fixed, non-real-time) — just needs to look alive.
(function () {
  var el = document.getElementById("countdown");
  if (!el) return;
  var remaining = 6 * 3600 + 42 * 60 + 17;
  function tick() {
    var h = Math.floor(remaining / 3600);
    var m = Math.floor((remaining % 3600) / 60);
    var s = remaining % 60;
    el.textContent = [h, m, s].map(function (n) { return String(n).padStart(2, "0"); }).join(":");
    if (remaining > 0) remaining--;
  }
  tick();
  setInterval(tick, 1000);
})();
