// Flash-sale base price + discount are fetched from the token-gated
// flash-sale.json, not embedded as HTML data attributes -- an earlier
// version put them in data-base-price/data-discount attributes, which
// defeated the whole point (a bare curl of the raw HTML revealed both
// numbers without executing any JS at all).
(function () {
  var el = document.getElementById("flash-price");
  if (!el) return;
  nkFetch("flash-sale.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var final = Math.round(data.base_price * (1 - data.discount_pct / 100) * 100) / 100;
      el.textContent = "$" + final.toFixed(2);
      // Set the USD reference price so common.js's region conversion can
      // override the display currency once regions.json has also loaded.
      el.dataset.usdPrice = final.toFixed(2);
      if (window.nkApplyRegionPricing) window.nkApplyRegionPricing();
    });
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
