(() => {
    'use strict';
    if (window.RKPTableWheel) return;
    window.RKPTableWheel = true;
    const selector = '.gkp-table-scroll, .gkp-table-wrap, .init-table-scroll';
    const observed = new WeakSet();
    function update(region) {
        const hint = region.nextElementSibling;
        if (hint?.classList.contains('table-column-hint')) {
            hint.hidden = region.scrollWidth <= region.clientWidth + 1;
        }
    }
    const resize = new ResizeObserver(entries => entries.forEach(({target}) => {
        update(target.matches(selector) ? target : target.parentElement);
    }));
    function initialize() {
        document.querySelectorAll(selector).forEach(region => {
            if (observed.has(region)) return;
            observed.add(region);
            if (!region.hasAttribute('tabindex')) region.tabIndex = 0;
            if (!region.hasAttribute('role')) region.setAttribute('role', 'region');
            if (!region.hasAttribute('aria-label')) region.setAttribute('aria-label', 'Tabla desplazable');
            const hint = document.createElement('p');
            hint.className = 'table-column-hint';
            hint.textContent = 'Shift + rueda para ver columnas';
            hint.hidden = true;
            region.after(hint);
            resize.observe(region);
            if (region.querySelector('table')) resize.observe(region.querySelector('table'));
            update(region);
        });
    }
    document.addEventListener('wheel', event => {
        if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.deltaX !== 0) return;
        if (event.target.closest('input, textarea, select, [contenteditable="true"]') ||
            document.activeElement?.matches('select')) return;
        const region = event.target.closest(selector);
        if (!region || region.scrollWidth <= region.clientWidth + 1) return;
        // Vertical overflow stays native; horizontal touchpad gestures stay native too.
        if (!event.shiftKey && region.scrollHeight > region.clientHeight + 1) return;
        const unit = event.deltaMode === 1 ? parseFloat(getComputedStyle(region).lineHeight) || 16 :
            event.deltaMode === 2 ? region.clientWidth : 1;
        const delta = event.deltaY * unit;
        const next = Math.max(0, Math.min(region.scrollWidth - region.clientWidth, region.scrollLeft + delta));
        const previous = region.scrollLeft;
        if (Math.abs(next - previous) < 0.5) return;
        region.scrollLeft = next;
        // Reserved scrollbar gutters can make the reported extent larger than
        // the actual scroll range. Only cancel after the browser moves it.
        if (Math.abs(region.scrollLeft - previous) >= 0.5) event.preventDefault();
    }, {passive: false});
    initialize();
    new MutationObserver(initialize).observe(document.body, {childList: true, subtree: true});
})();
