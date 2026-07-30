// Shared across every page.
//
// nkFetch(): every request for real data (games.json, bundle-data*.json,
// regions.json, flash-sale.json) must carry the X-Nk-Token header, whose
// value is injected by serve.py into window.NK_TOKEN at serve time (a
// fresh, random value each server run -- never hardcoded in this file or
// committed anywhere). serve.py rejects requests to those files without
// the correct header. This is deliberately not unbeatable -- a scraper
// that actually reads the HTML/JS can still find and replay the token --
// it exists to filter out the naive case (guess a filename, curl it
// directly) the same way a real site's CSRF/session-token-gated internal
// API would, while being completely transparent to anything that actually
// executes the page's JS (a real browser needs to do nothing extra).
//
// Region pricing: every price on the site is authored once in USD (as a
// data-usd-price attribute) and rendered in whatever region is selected --
// there is no separate "EU price" or "BR price" anywhere in the HTML,
// only the USD figure + a conversion rate fetched from regions.json.
// Selection persists via localStorage, same as a real storefront
// remembering your region across page loads.
function nkFetch(path) {
  return fetch(path, { headers: { "X-Nk-Token": window.NK_TOKEN || "" } });
}

var NK_REGIONS = null; // populated async below; null until regions.json loads
var NK_REGIONS_READY = nkFetch("regions.json")
  .then(function (r) {
    if (!r.ok) throw new Error("regions.json fetch failed: " + r.status);
    return r.json();
  })
  .then(function (data) {
    NK_REGIONS = data;
    nkApplyRegionPricing();
    return data;
  });

function nkGetRegion() {
  var r = localStorage.getItem("nk_region");
  return NK_REGIONS && NK_REGIONS[r] ? r : "US";
}

function nkApplyRegionPricing() {
  if (!NK_REGIONS) return; // not loaded yet -- NK_REGIONS_READY re-applies once it is
  var region = nkGetRegion();
  var r = NK_REGIONS[region];
  document.querySelectorAll("[data-usd-price]").forEach(function (el) {
    var usd = parseFloat(el.dataset.usdPrice);
    if (isNaN(usd)) return;
    el.textContent = r.symbol + (usd * r.mult).toFixed(2);
  });
  var sel = document.getElementById("region-select");
  if (sel) sel.value = region;
}

function nkInitRegionSelector() {
  var sel = document.getElementById("region-select");
  if (!sel) return;
  sel.addEventListener("change", function () {
    localStorage.setItem("nk_region", sel.value);
    nkApplyRegionPricing();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  nkInitRegionSelector();
  nkApplyRegionPricing(); // no-op if NK_REGIONS isn't loaded yet; harmless
});
