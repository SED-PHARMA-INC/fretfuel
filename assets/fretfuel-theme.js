document.addEventListener('DOMContentLoaded', () => {
  const menu = document.getElementById('mega-menu');
  const toggles = document.querySelectorAll('[data-menu-toggle]');
  const setMenu = open => {
    if (!menu) return;
    menu.hidden = !open;
    toggles.forEach(button => button.setAttribute('aria-expanded', String(open)));
  };
  toggles.forEach(button => button.addEventListener('click', () => setMenu(menu.hidden)));
  document.querySelector('[data-menu-close]')?.addEventListener('click', () => setMenu(false));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') setMenu(false); });
  document.addEventListener('click', event => {
    if (menu && !menu.hidden && !event.target.closest('.shop-header')) setMenu(false);
  });

  const variantSelect = document.getElementById('ProductVariant');
  const productPrice = document.querySelector('.ff-product-copy .detail-price');
  variantSelect?.addEventListener('change', () => {
    const option = variantSelect.selectedOptions[0];
    if (productPrice && option?.dataset.price) productPrice.textContent = option.dataset.price;
  });

  document.querySelectorAll('[data-ff-product-gallery]').forEach(gallery => {
    const panels = Array.from(gallery.querySelectorAll('.ff-product-media-panel'));
    const thumbs = Array.from(gallery.querySelectorAll('.ff-product-thumb'));

    const pauseMedia = panel => {
      panel.querySelector('video')?.pause();
      panel.modelViewerUI?.pause();
      if (panel.dataset.mediaType === 'external_video') {
        panel.querySelector('.ff-media-embedded')?.remove();
        const activate = panel.querySelector('.ff-media-activate');
        if (activate) activate.hidden = false;
      }
    };

    thumbs.forEach(thumb => thumb.addEventListener('click', () => {
      const next = panels.find(panel => panel.dataset.mediaId === thumb.dataset.mediaId);
      if (!next || !next.hidden) return;
      panels.forEach(panel => {
        if (!panel.hidden) pauseMedia(panel);
        panel.hidden = panel !== next;
      });
      thumbs.forEach(item => item.setAttribute('aria-pressed', String(item === thumb)));
    }));

    panels.forEach(panel => {
      const activate = panel.querySelector('.ff-media-activate');
      if (!activate) return;
      activate.addEventListener('click', () => {
        if (panel.querySelector('.ff-media-embedded')) return;
        const template = panel.querySelector('template');
        const media = template?.content.firstElementChild?.cloneNode(true);
        if (!media) return;
        media.classList.add('ff-media-embedded');

        if (panel.dataset.mediaType === 'model') {
          if (!window.Shopify?.loadFeatures) return;
          activate.disabled = true;
          const label = activate.querySelector('.ff-media-activate-label');
          if (label) label.textContent = 'Loading 3D model…';
          panel.appendChild(media);
          window.Shopify.loadFeatures([{
            name: 'model-viewer-ui',
            version: '1.0',
            onLoad: errors => {
              activate.disabled = false;
              if (errors || !window.Shopify.ModelViewerUI) {
                media.remove();
                if (label) label.textContent = 'Retry 3D model';
                return;
              }
              panel.modelViewerUI = new window.Shopify.ModelViewerUI(media);
              activate.hidden = true;
              if (panel.hidden) panel.modelViewerUI.pause();
              else media.focus();
            }
          }]);
          return;
        }

        panel.appendChild(media);
        activate.hidden = true;
        if (media.tagName === 'VIDEO') media.play().catch(() => {});
        else media.focus();
      });
    });
  });
});
