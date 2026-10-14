// main.js — small, framework-free UI behaviour shared by every page.

(function () {
    // Render Lucide icons (<i data-lucide="...">) into inline SVGs.
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // Category bars: replace the 10%-step fallback class with the exact share.
    document.querySelectorAll('.bar-fill[data-pct]').forEach(function (bar) {
        var pct = Math.max(0, Math.min(100, Number(bar.dataset.pct) || 0));
        bar.style.width = pct + '%';
    });
})();
