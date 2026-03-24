/* Minimal JS for Trader dashboard */

// Auto-resize charts on window resize
window.addEventListener('resize', function() {
    const charts = document.querySelectorAll('[data-chart]');
    charts.forEach(function(el) {
        if (el._chart) {
            el._chart.applyOptions({ width: el.clientWidth });
        }
    });
});
