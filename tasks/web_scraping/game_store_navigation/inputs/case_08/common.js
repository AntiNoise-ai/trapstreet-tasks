// Shared across every page: header region selector + USD->region price
// conversion. Every price on the site is authored once in USD (as a
// data-usd-price attribute) and rendered in whatever region is selected —
// there is no separate "EU price" or "BR price" anywhere in the HTML/JSON,
// only the USD figure + a conversion rate. Selection persists via
// localStorage, same as a real storefront remembering your region across
// page loads (a request-only scraper that doesn't carry that state will
// silently see US pricing on every page, even after "selecting" another
// region — which is itself a realistic scraping trap).
var NK_REGIONS = {
  US: { symbol: "$", mult: 1.00 },
  EU: { symbol: "€", mult: 0.93 },
  BR: { symbol: "R$", mult: 5.35 }
};

function nkGetRegion() {
  var r = localStorage.getItem("nk_region");
  return NK_REGIONS[r] ? r : "US";
}

function nkApplyRegionPricing() {
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
  nkApplyRegionPricing();
});
