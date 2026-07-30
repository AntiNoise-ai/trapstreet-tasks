// Full catalog is fetched once into memory, but the DOM only ever shows one
// page's worth (PAGE_SIZE games) of whatever the current filter+sort
// produces — nothing renders until this script runs, and seeing every game
// (e.g. to count how many are rated 90+) requires paging all the way
// through, not just waiting for one render.
(function () {
  var PAGE_SIZE = 6;
  var allGames = [];
  var page = 1;

  function filtered() {
    var category = document.getElementById("f-category").value;
    var minRating = parseInt(document.getElementById("f-rating").value, 10);
    var sortBy = document.getElementById("f-sort").value;

    var out = allGames.filter(function (g) {
      if (category !== "all" && g.category !== category) return false;
      if (g.rating < minRating) return false;
      return true;
    });

    out.sort(function (a, b) {
      if (sortBy === "price-asc") return a.price - b.price;
      if (sortBy === "price-desc") return b.price - a.price;
      if (sortBy === "rating-desc") return b.rating - a.rating;
      return a.name.localeCompare(b.name);
    });
    return out;
  }

  function render() {
    var results = filtered();
    var totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
    if (page > totalPages) page = totalPages;
    var start = (page - 1) * PAGE_SIZE;
    var pageItems = results.slice(start, start + PAGE_SIZE);

    var grid = document.getElementById("catalog-grid");
    grid.innerHTML = pageItems.map(function (g) {
      // Only Wraithbound has a real detail page (DLC/editions/system reqs);
      // every other title is catalog-only, so it renders as plain text, not
      // a link to a detail page that would show the wrong game's content.
      var title = g.id === "wraithbound"
        ? '<a href="game.html?id=' + g.id + '" style="color:inherit">' + g.name + "</a>"
        : g.name;
      return '<div class="card">' +
        '<div class="title">' + title + "</div>" +
        '<div class="meta">' + g.category + " · " + g.rating + "% positive</div>" +
        '<span class="price" data-usd-price="' + g.price.toFixed(2) + '">$' + g.price.toFixed(2) + "</span>" +
        "</div>";
    }).join("");

    document.getElementById("catalog-summary").textContent =
      "Showing " + (results.length ? (start + 1) + "–" + Math.min(start + PAGE_SIZE, results.length) : 0) +
      " of " + results.length + " games";
    document.getElementById("page-label").textContent = "Page " + page + " of " + totalPages;
    document.getElementById("prev-page").disabled = page <= 1;
    document.getElementById("next-page").disabled = page >= totalPages;

    if (window.nkApplyRegionPricing) window.nkApplyRegionPricing();
  }

  document.getElementById("f-category").addEventListener("change", function () { page = 1; render(); });
  document.getElementById("f-rating").addEventListener("change", function () { page = 1; render(); });
  document.getElementById("f-sort").addEventListener("change", function () { page = 1; render(); });
  document.getElementById("prev-page").addEventListener("click", function () { page--; render(); });
  document.getElementById("next-page").addEventListener("click", function () { page++; render(); });

  nkFetch("games.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      allGames = data;
      render();
    });
})();
