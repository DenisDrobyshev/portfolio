/* Publications page: abstract toggle, copy DOI / BibTeX, live Zenodo counts. */
(function () {
  var list = document.querySelector('.pub-list');
  if (!list) return;

  var ru = document.documentElement.lang === 'ru';
  var T = ru
    ? { more: 'Аннотация', less: 'Свернуть', copied: 'Скопировано', cite: 'Цитировать', bib: 'BibTeX скопирован', dl: 'скач.', views: 'просм.' }
    : { more: 'Abstract', less: 'Collapse', copied: 'Copied', cite: 'Cite', bib: 'BibTeX copied', dl: 'downloads', views: 'views' };

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    var area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(area);
    area.select();
    try { document.execCommand('copy'); } finally { document.body.removeChild(area); }
    return Promise.resolve();
  }

  function flash(button, label) {
    var original = button.dataset.label || button.textContent;
    button.dataset.label = original;
    button.textContent = label;
    button.classList.add('is-done');
    clearTimeout(button._t);
    button._t = setTimeout(function () {
      button.textContent = original;
      button.classList.remove('is-done');
    }, 1600);
  }

  function bibtex(item) {
    var title = item.querySelector('.pub-title a').textContent;
    var doi = (item.querySelector('.pub-doi') || {}).dataset;
    var authors = item.dataset.authors || '';
    var first = (authors.split(',')[0] || 'paper').toLowerCase().replace(/[^a-z]/g, '');
    var word = (title.match(/[A-Za-z]{4,}/) || ['paper'])[0].toLowerCase();
    var lines = [
      '@misc{' + first + item.dataset.year + word + ',',
      '  author    = {' + authors + '},',
      '  title     = {{' + title + '}},',
      '  year      = {' + item.dataset.year + '},',
      '  publisher = {Zenodo},'
    ];
    if (doi && doi.copy) {
      lines.push('  doi       = {' + doi.copy + '},');
      lines.push('  url       = {https://doi.org/' + doi.copy + '}');
    }
    return lines.join('\n') + '\n}';
  }

  // Abstract toggle: only for abstracts that are actually cut off.
  list.querySelectorAll('.pub').forEach(function (item) {
    var text = item.querySelector('.pub-abstract');
    var more = item.querySelector('.pub-more');
    if (!text || !more) return;
    var first = text.querySelector('p');
    var cut = first && first.scrollHeight - first.clientHeight > 4;
    if (cut || text.querySelectorAll('p').length > 1) more.hidden = false;
  });

  list.addEventListener('click', function (event) {
    var button = event.target.closest('button');
    if (!button) return;
    var item = button.closest('.pub');
    if (button.classList.contains('pub-more')) {
      var open = item.classList.toggle('is-open');
      button.setAttribute('aria-expanded', String(open));
      button.textContent = open ? T.less : T.more;
    } else if (button.classList.contains('pub-doi')) {
      copy(button.dataset.copy).then(function () { flash(button, T.copied); });
    } else if (button.classList.contains('pub-cite')) {
      copy(bibtex(item)).then(function () { flash(button, T.bib); });
    }
  });

  // Live counts from Zenodo; the page works the same if this fails.
  var fmt = new Intl.NumberFormat(ru ? 'ru-RU' : 'en-US');
  var items = {};
  list.querySelectorAll('.pub').forEach(function (item) { items[item.dataset.id] = item; });
  var totals = { downloads: 0, views: 0 };

  function load(page) {
    var url = 'https://zenodo.org/api/records?size=25&page=' + page +
      '&q=' + encodeURIComponent('"Drobyshev, Denis"');
    return fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var hits = (data.hits && data.hits.hits) || [];
        hits.forEach(function (hit) {
          var item = items[String(hit.id)];
          if (!item || !hit.stats) return;
          var dl = hit.stats.unique_downloads || 0;
          var views = hit.stats.unique_views || 0;
          totals.downloads += dl;
          totals.views += views;
          if (!dl && !views) return;
          var slot = item.querySelector('.pub-stats');
          slot.innerHTML = '<span>' + fmt.format(dl) + ' ' + T.dl + '</span><span>' + fmt.format(views) + ' ' + T.views + '</span>';
          slot.hidden = false;
        });
        if (hits.length === 25 && page < 10) return load(page + 1);
      });
  }

  load(1).then(function () {
    Object.keys(totals).forEach(function (key) {
      var box = document.querySelector('.pub-stat[data-total="' + key + '"]');
      if (!box || !totals[key]) return;
      box.querySelector('.pub-stat-num').textContent = fmt.format(totals[key]);
      box.hidden = false;
    });
  }).catch(function () {});
})();
