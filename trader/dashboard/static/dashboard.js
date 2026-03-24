/* Minimal JS for Trader dashboard — chart resize handled inline in equity_curve.html */

document.addEventListener('htmx:responseError', function(evt) {
    evt.detail.target.innerHTML =
        '<article><p class="sell">Failed to load widget. Retrying...</p></article>';
});
