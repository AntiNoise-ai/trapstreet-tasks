// Tier prices AND game lists are fetched at runtime, not present anywhere in
// bundle.html's source. A tool that only parses static HTML sees an empty
// #tier-buttons div and nothing else — it has to execute this script (and,
// to see any single tier's game list, actually click that tier's button).
(function () {
  var buttonRow = document.getElementById("tier-buttons");
  var source = buttonRow.dataset.source || "bundle-data.json";
  nkFetch(source)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var detail = document.getElementById("tier-detail");

      data.tiers.forEach(function (tier) {
        var btn = document.createElement("button");
        btn.className = "tier-btn";
        btn.dataset.tier = tier.tier;
        btn.innerHTML = "Tier " + tier.tier +
          '<span class="tier-price" data-usd-price="' + tier.price.toFixed(2) + '">$' + tier.price.toFixed(2) + "</span>";
        btn.addEventListener("click", function () {
          Array.prototype.forEach.call(buttonRow.children, function (b) {
            b.classList.remove("active");
          });
          btn.classList.add("active");

          var perGame = tier.price / tier.games.length;
          var html = "<strong>Tier " + tier.tier +
            ' — <span data-usd-price="' + tier.price.toFixed(2) + '">$' + tier.price.toFixed(2) + "</span>" +
            " for " + tier.games.length + " games</strong>" +
            ' <span style="color:#9aa0aa">(<span data-usd-price="' + perGame.toFixed(2) + '">$' + perGame.toFixed(2) + "</span> / game)</span>" +
            '<ul class="game-list-inline">' +
            tier.games.map(function (g) { return "<li>" + g + "</li>"; }).join("") +
            "</ul>";
          detail.innerHTML = html;
          if (window.nkApplyRegionPricing) window.nkApplyRegionPricing();
        });
        buttonRow.appendChild(btn);
      });
      if (window.nkApplyRegionPricing) window.nkApplyRegionPricing();
    });
})();
