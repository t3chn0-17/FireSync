/* =========================================================
   FireSync — map page logic (MapLibre GL JS, vanilla)
   - Mode A: color by sensor platform (who saw it)
   - Mode B: color by FRP bins (how strong the signal was)
   - Platform toggles + date filter + side panel + details card
   مناسبة مع FireSync API الحقيقي (api.py):
   المنصات بتتبني ديناميكيًا من الداتا (platform_list) مش hard-coded.
   ========================================================= */
(function () {
  'use strict';

  var cfg = window.FIRESYNC_CONFIG;
  var FRP_STEPS = [[1, '#ffe14d'], [3, '#ff9a3d'], [10, '#ff5d3d']]; // <1 | 1–3 | 3–10 | ≥10

  var state = {
    dataset: null,
    geojson: null,
    colors: {},                      // platform_label -> color (built from data)
    mode: 'A',                       // 'A' = platform colors, 'B' = FRP colors
    enabled: {},                     // platform_label -> bool
    date: 'all'
  };

  // ---------- DOM ----------
  var el = function (id) { return document.getElementById(id); };
  var loadingOverlay = el('loadingOverlay');
  var errorOverlay = el('errorOverlay');
  var errorMsg = el('errorMsg');

  // ---------- helpers ----------
  function colorModeAExpr() {
    var pairs = [];
    state.dataset.meta.platforms.forEach(function (p) {
      pairs.push(p, state.colors[p]);
    });
    return ['match', ['get', 'platform_label']].concat(pairs, ['#9aa7b8']);
  }

  function colorModeBExpr() {
    var e = ['step', ['get', 'frp'], FRP_STEPS[0][1]];
    FRP_STEPS.forEach(function (s) { e.push(s[0], s[1]); });
    return e;
  }

  function currentColorExpr() {
    return state.mode === 'A' ? colorModeAExpr() : colorModeBExpr();
  }

  function currentFilterExpr() {
    var platforms = Object.keys(state.enabled).filter(function (p) { return state.enabled[p]; });
    var dateExpr = state.date === 'all'
      ? true
      : ['==', ['get', 'acq_date'], state.date];
    return ['all', ['in', ['get', 'platform_label'], ['literal', platforms]], dateExpr];
  }

  function applyFilters() {
    if (!window._fsMap || !state.geojson) return;
    var f = currentFilterExpr();
    window._fsMap.setFilter('hotspot-glow', f);
    window._fsMap.setFilter('hotspot-core', f);
    updateStats();
  }

  function applyColors() {
    if (!window._fsMap || !window._fsMap.isStyleLoaded()) return;
    var c = currentColorExpr();
    window._fsMap.setPaintProperty('hotspot-glow', 'circle-color', c);
    window._fsMap.setPaintProperty('hotspot-core', 'circle-color', c);
  }

  function fmtInt(n) { return n == null ? '—' : Number(n).toLocaleString('en-US'); }

  function updateStats() {
    var obs = state.dataset.observations;
    var platforms = Object.keys(state.enabled).filter(function (p) { return state.enabled[p]; });
    var perPlatform = {};
    var total = 0;
    obs.forEach(function (o) {
      if (platforms.indexOf(o.platform_label) === -1) return;
      if (state.date !== 'all' && o.acq_date !== state.date) return;
      perPlatform[o.platform_label] = (perPlatform[o.platform_label] || 0) + 1;
      total++;
    });
    var html = '<b>' + fmtInt(total) + '</b> shown of ' + fmtInt(obs.length) + '<br>';
    state.dataset.meta.platforms.forEach(function (p) {
      if (state.enabled[p] === false) return;
      html += '<span style="color:' + state.colors[p] + '">●</span> ' + p + ': <b>' +
        fmtInt(perPlatform[p] || 0) + '</b><br>';
    });
    el('statsBox').innerHTML = html;
  }

  // ---------- side panel UI ----------
  function buildPlatformToggles() {
    var box = el('platformToggles');
    var counts = state.dataset.meta.per_platform || {};
    state.dataset.meta.platforms.forEach(function (p) {
      state.enabled[p] = true;
      state.colors[p] = window.FireSyncAPI.platformColor(p, state.dataset.meta.platforms.indexOf(p));

      var t = document.createElement('div');
      t.className = 'pt';
      t.innerHTML =
        '<span class="sw" style="background:' + state.colors[p] + '"></span>' +
        '<span>' + p + '</span><span class="cnt">' + fmtInt(counts[p] || 0) + '</span>';
      t.addEventListener('click', function () {
        state.enabled[p] = !state.enabled[p];
        t.classList.toggle('off', !state.enabled[p]);
        applyFilters();
      });
      box.appendChild(t);
    });
  }

  function buildDateFilter() {
    var sel = el('dateFilter');
    var days = {};
    state.dataset.observations.forEach(function (o) { days[o.acq_date] = (days[o.acq_date] || 0) + 1; });
    Object.keys(days).sort().forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d + '  (' + days[d] + ')';
      sel.appendChild(opt);
    });
    sel.addEventListener('change', function () {
      state.date = sel.value;
      applyFilters();
    });
  }

  function setMode(mode) {
    state.mode = mode;
    el('modeA').classList.toggle('active', mode === 'A');
    el('modeB').classList.toggle('active', mode === 'B');
    // Mode A → the platform toggles themselves are the legend (colors + counts).
    // Mode B → show the FRP bins legend.
    var showFrpLegend = mode === 'B';
    el('legendBox').style.display = showFrpLegend ? 'flex' : 'none';
    el('legendTitle').style.display = showFrpLegend ? 'block' : 'none';
    applyColors();
  }

  // ---------- details card ----------
  function showDetails(props) {
    var p = state.colors[props.platform_label] || '#9aa7b8';
    el('dSw').style.background = p;
    el('dPlatform').textContent = props.platform_label || '—';
    el('dFrp').innerHTML =
      (props.frp_raw == null ? '—' : props.frp_raw) + ' <small>MW FRP</small>';
    el('dInst').textContent = props.sensor || props.instrument || '—';
    el('dSat').textContent = props.satellite_name || props.satellite || '—';
    el('dTime').textContent = props.acq_datetime || '—';
    el('dConf').textContent = props.confidence == null ? '—' : String(props.confidence);
    el('dBright').textContent = props.brightness == null ? '—' : props.brightness + ' K';
    el('dDN').textContent = props.daynight === 'D' ? 'Day' :
      props.daynight === 'N' ? 'Night' : (props.daynight || '—');
    el('dGrid').textContent = props.grid_id || '—';
    if (props._coords) {
      el('dCoords').textContent = props._coords[1].toFixed(3) + ', ' + props._coords[0].toFixed(3);
    }
    el('detailsCard').classList.add('show');
  }

  // ---------- map init ----------
  function initMap() {
    var map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: cfg.map.center,
      zoom: cfg.map.zoom,
      attributionControl: { compact: true }
    });
    window._fsMap = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

    map.on('error', function () {
      if (map._fsErrorShown) return;
      map._fsErrorShown = true;
      errorMsg.textContent =
        'Could not load the basemap. Check your internet connection, then reload the page. ' +
        '(Map tiles and MapLibre come from a CDN.)';
      errorOverlay.classList.remove('hidden');
    });

    map.on('load', function () {
      map.addSource('hotspots', { type: 'geojson', data: state.geojson });

      map.addLayer({
        id: 'hotspot-glow',
        type: 'circle',
        source: 'hotspots',
        paint: {
          'circle-color': currentColorExpr(),
          'circle-radius': 9,
          'circle-opacity': 0.22
        }
      });

      map.addLayer({
        id: 'hotspot-core',
        type: 'circle',
        source: 'hotspots',
        paint: {
          'circle-color': currentColorExpr(),
          'circle-radius': 4.5,
          'circle-opacity': 0.95,
          'circle-stroke-width': 0.8,
          'circle-stroke-color': 'rgba(0,0,0,0.55)'
        }
      });

      map.addSource('selected', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });
      map.addLayer({
        id: 'selected-ring',
        type: 'circle',
        source: 'selected',
        paint: {
          'circle-color': 'rgba(255,255,255,0.08)',
          'circle-radius': 11,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });

      map.on('mouseenter', 'hotspot-core', function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'hotspot-core', function () { map.getCanvas().style.cursor = ''; });

      map.on('click', 'hotspot-core', function (e) {
        var f = e.features && e.features[0];
        if (!f) return;
        var props = Object.assign({}, f.properties, { _coords: f.geometry.coordinates });
        showDetails(props);
        map.getSource('selected').setData({
          type: 'FeatureCollection',
          features: [f]
        });
      });

      applyFilters();
      setMode(state.mode);
      loadingOverlay.classList.add('hidden');
    });
  }

  // ---------- boot ----------
  async function boot() {
    try {
      var dataset = await window.FireSyncAPI.loadHotspots();
      state.dataset = dataset;
      state.geojson = window.FireSyncAPI.toGeoJSON(dataset);

      // build dynamic platform colors before anything renders
      state.dataset.meta.platforms.forEach(function (p, i) {
        state.colors[p] = window.FireSyncAPI.platformColor(p, i);
      });

      // header badge
      var badge = el('dataBadge');
      var range = dataset.meta.date_range;
      el('dataBadgeText').innerHTML =
        '<b>' + fmtInt(dataset.observations.length) + '</b> hotspots · ' +
        (range ? range[0] + ' → ' + range[1] + ' · ' : '') +
        (dataset.meta.demo ? 'demo data' : 'live API');
      badge.classList.toggle('demo', !!dataset.meta.demo);
      badge.title = (dataset.meta.source_label || '') + '\n' + (dataset.meta.disclaimer || '');

      buildPlatformToggles();
      buildDateFilter();
      updateStats();

      el('modeA').addEventListener('click', function () { setMode('A'); });
      el('modeB').addEventListener('click', function () { setMode('B'); });
      el('detailsClose').addEventListener('click', function () {
        el('detailsCard').classList.remove('show');
        window._fsMap.getSource('selected').setData({ type: 'FeatureCollection', features: [] });
      });

      // support ?date=YYYY-MM-DD (used by the calendar page "open on map" link)
      var q = new URLSearchParams(location.search);
      if (q.get('date')) {
        state.date = q.get('date');
        el('dateFilter').value = state.date;
      }

      if (!window.maplibregl) throw new Error('MapLibre failed to load from CDN');
      initMap();
    } catch (err) {
      console.error(err);
      loadingOverlay.classList.add('hidden');
      errorMsg.textContent = 'Failed to load data: ' + err.message;
      errorOverlay.classList.remove('hidden');
    }
  }

  boot();
})();
