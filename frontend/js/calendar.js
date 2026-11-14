/* =========================================================
   FireSync — calendar page logic (vanilla)
   صفحة التقويم: عرض عدد الـ hotspots في كل يوم (UTC)،
   والضغط على أي يوم يعرض ملخص كل منصة + تفاصيل الملاحظات.
   متكاملة مع FireSync API الحقيقي (api.py): الحقول الجديدة
   (sensor / satellite_name / frp / confidence الأصلي) والألوان ديناميكية.
   ========================================================= */
(function () {
  'use strict';

  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  var DOW = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']; // week starts Saturday (Egypt)

  var el = function (id) { return document.getElementById(id); };

  var state = {
    dataset: null,
    colors: {},          // platform_label -> color (dynamic, from data)
    byDate: {},          // 'YYYY-MM-DD' -> [observations]
    viewYear: 0,
    viewMonth: 0,        // 0-based
    selectedDate: null
  };

  function fmtInt(n) { return n == null ? '—' : Number(n).toLocaleString('en-US'); }

  function median(arr) {
    var vals = arr.filter(function (v) { return typeof v === 'number'; });
    if (!vals.length) return null;
    var s = vals.slice().sort(function (a, b) { return a - b; });
    var m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  function heatClass(count) {
    // relative heat 1..4 compared to the busiest day
    var max = 0;
    Object.keys(state.byDate).forEach(function (d) { max = Math.max(max, state.byDate[d].length); });
    if (count >= max * 0.75) return 'h4';
    if (count >= max * 0.5) return 'h3';
    if (count >= max * 0.25) return 'h2';
    return 'h1';
  }

  // ---------- calendar grid ----------
  function renderCalendar() {
    var y = state.viewYear, m = state.viewMonth;
    el('monthLabel').textContent = MONTHS[m] + ' ' + y;

    var grid = el('calGrid');
    grid.innerHTML = '';
    DOW.forEach(function (d) {
      var c = document.createElement('div');
      c.className = 'cal-dow';
      c.textContent = d;
      grid.appendChild(c);
    });

    var firstDow = (new Date(Date.UTC(y, m, 1)).getUTCDay() + 6) % 7; // Saturday = 0
    var daysInMonth = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();

    for (var i = 0; i < firstDow; i++) {
      var pad = document.createElement('div');
      pad.className = 'cal-day empty';
      grid.appendChild(pad);
    }

    var today = new Date();
    for (var d = 1; d <= daysInMonth; d++) {
      var key = y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      var cell = document.createElement('div');
      cell.className = 'cal-day';
      var obs = state.byDate[key];

      if (obs && obs.length) {
        cell.className = 'cal-day has ' + heatClass(obs.length);
        cell.innerHTML =
          '<div class="dnum">' + d + '</div>' +
          '<span class="cnt">' + fmtInt(obs.length) + '</span>';
        cell.addEventListener('click', function (k) {
          return function () { selectDay(k); };
        }(key));
        if (state.selectedDate === key) cell.classList.add('selected');
      } else {
        cell.innerHTML = '<div class="dnum">' + d + '</div>';
        if (d === today.getDate() && m === today.getMonth() && y === today.getFullYear()) {
          cell.style.borderColor = 'rgba(255,107,61,0.6)';
        }
      }
      grid.appendChild(cell);
    }
  }

  function buildHeatStyles() {
    var css = document.createElement('style');
    css.textContent =
      '.cal-day.has.h1 .cnt{background:#ffe14d}' +
      '.cal-day.has.h2 .cnt{background:#ff9a3d}' +
      '.cal-day.has.h3 .cnt{background:#ff5d3d}' +
      '.cal-day.has.h4 .cnt{background:#c62828;color:#fff}';
    document.head.appendChild(css);
  }

  // ---------- day details ----------
  function selectDay(key) {
    state.selectedDate = key;
    renderCalendar(); // refresh selection outline

    var obs = state.byDate[key] || [];
    var box = el('dayDetail');

    // per-platform summary — aggregated per sensor, never mixed (FireSync principle)
    var groups = {};
    obs.forEach(function (o) {
      if (!groups[o.platform_label]) groups[o.platform_label] = [];
      groups[o.platform_label].push(o);
    });

    var rowsHtml = '';
    state.dataset.meta.platforms.forEach(function (p) {
      var g = groups[p];
      if (!g) return;
      var medFrp = median(g.map(function (o) { return o.frp_raw; }));
      var confs = {};
      g.forEach(function (o) {
        var c = o.confidence == null ? '—' : String(o.confidence);
        confs[c] = (confs[c] || 0) + 1;
      });
      var confSummary = Object.keys(confs)
        .sort(function (a, b) { return confs[b] - confs[a]; })
        .slice(0, 3)
        .map(function (c) { return c + '×' + confs[c]; })
        .join(', ');
      var sensor = g[0] && g[0].sensor ? ' <span style="color:var(--muted)">(' + g[0].sensor + ')</span>' : '';
      rowsHtml +=
        '<tr><td><span class="chip">' +
        '<span class="sw" style="width:10px;height:10px;border-radius:50%;background:' +
        state.colors[p] + ';display:inline-block"></span>' + p + sensor + '</span></td>' +
        '<td>' + fmtInt(g.length) + '</td>' +
        '<td>' + (medFrp == null ? '—' : medFrp + ' MW') + '</td>' +
        '<td>' + confSummary + '</td></tr>';
    });

    var obsRows = obs.slice(0, 200).map(function (o) {
      var time = o.acq_datetime ? o.acq_datetime.replace('T', ' ').replace('Z', '') : '—';
      return '<div class="obs-row">' +
        '<span class="sw" style="background:' + (state.colors[o.platform_label] || '#999') + '"></span>' +
        '<span class="t">' + time + '</span>' +
        '<span>' + o.platform_label + '</span>' +
        '<span class="conf">conf ' + (o.confidence == null ? '—' : o.confidence) + '</span>' +
        '<span class="frp">' + (o.frp_raw == null ? '—' : o.frp_raw + ' MW') + ' · ' + (o.grid_id || '—') + '</span>' +
        '</div>';
    }).join('');

    box.innerHTML =
      '<div class="cal-card">' +
      '<h2>' + key + '</h2>' +
      '<div class="sub">' + fmtInt(obs.length) + ' observations · grouped by platform (values never mixed between sensors)</div>' +
      '<table class="plat-table"><thead><tr>' +
      '<th>Platform</th><th>Observations</th><th>Median FRP</th><th>Confidence values</th>' +
      '</tr></thead><tbody>' + rowsHtml + '</tbody></table>' +
      (obs.length ? '<div class="obs-list">' + obsRows + '</div>' : '') +
      '<a class="open-map-btn" href="index.html?date=' + key + '">Open this day on the map →</a>' +
      '</div>';

    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ---------- month navigation ----------
  function shiftMonth(delta) {
    var d = new Date(Date.UTC(state.viewYear, state.viewMonth + delta, 1));
    state.viewYear = d.getUTCFullYear();
    state.viewMonth = d.getUTCMonth();
    renderCalendar();
  }

  // ---------- boot ----------
  async function boot() {
    var dataset = await window.FireSyncAPI.loadHotspots();
    state.dataset = dataset;

    state.dataset.meta.platforms.forEach(function (p, i) {
      state.colors[p] = window.FireSyncAPI.platformColor(p, i);
    });

    state.byDate = {};
    dataset.observations.forEach(function (o) {
      (state.byDate[o.acq_date] = state.byDate[o.acq_date] || []).push(o);
    });

    // header badge
    var range = dataset.meta.date_range;
    el('dataBadgeText').innerHTML =
      '<b>' + fmtInt(dataset.observations.length) + '</b> hotspots · ' +
      (range ? range[0] + ' → ' + range[1] + ' · ' : '') +
      (dataset.meta.demo ? 'demo data' : 'live API');
    el('dataBadge').classList.toggle('demo', !!dataset.meta.demo);
    el('dataBadge').title = (dataset.meta.source_label || '') + '\n' + (dataset.meta.disclaimer || '');

    // summary boxes
    el('sumTotal').textContent = fmtInt(dataset.observations.length);
    el('sumDays').textContent = fmtInt(Object.keys(state.byDate).length);
    el('sumCells').textContent = fmtInt(dataset.meta.unique_grid_cells);
    el('sumPlatforms').textContent = fmtInt(state.dataset.meta.platforms.length);

    // start on the first month that has data
    var dates = Object.keys(state.byDate).sort();
    if (dates.length) {
      var first = dates[0].split('-');
      state.viewYear = parseInt(first[0], 10);
      state.viewMonth = parseInt(first[1], 10) - 1;
    } else {
      var now = new Date();
      state.viewYear = now.getUTCFullYear();
      state.viewMonth = now.getUTCMonth();
    }

    buildHeatStyles();
    renderCalendar();

    el('prevMonth').addEventListener('click', function () { shiftMonth(-1); });
    el('nextMonth').addEventListener('click', function () { shiftMonth(1); });

    // deep link: calendar.html?date=YYYY-MM-DD selects the day directly
    var q = new URLSearchParams(location.search);
    if (q.get('date') && state.byDate[q.get('date')]) {
      selectDay(q.get('date'));
    }
  }

  boot();
})();
