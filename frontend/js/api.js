/* =========================================================
   FireSync — API layer
   ---------------------------------------------------------
   متكاملة مع FireSync API الحقيقي (api.py بتاع الفريق).
   Endpoints المستخدمة:
     GET /api/overview            → ملخص + date range + region
     GET /api/hotspots/geojson    → GeoJSON جاهز (limit حتى 20000)
     GET /api/observations        → pagination لو الداتا أكتر من 20000
   الترتيب:
     1) نحاول نجيب الداتا من السيرفر (apiBaseUrl في config.js)
     2) السيرفر مش متاح أو رجّع 0 ملاحظات → بيانات تجريبية مدمجة
   ========================================================= */
window.FireSyncAPI = (function () {

  var MAX_LIMIT = 20000;   // matches FIRESYNC_MAX_LIMIT in api.py
  var PAGE_SIZE = 5000;    // matches FIRESYNC_DEFAULT_LIMIT in api.py
  var lastError = null;

  function fetchWithTimeout(url, ms) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ms);
    return fetch(url, { signal: controller.signal })
      .finally(() => clearTimeout(timer));
  }

  function getLastError() { return lastError; }

  /* ---------- normalization (live + demo share the same path) ---------- */

  // لون كل منصة: أسماء معروفة ليها لون ثابت، وغير كده palette بديل بالترتيب
  var KNOWN_COLORS = [
    [/terra/,            '#ff4d4d'],
    [/aqua/,             '#c084fc'],
    [/snpp|suomi/,       '#ffb020'],
    [/noaa-20|(^|\D)n20/, '#35d07f'],
    [/noaa-21|(^|\D)n21/, '#4da3ff']
  ];
  var FALLBACK_PALETTE = ['#c084fc', '#22d3ee', '#fb7185', '#a3e635', '#f97316', '#94a3b8'];

  function platformColor(name, idx) {
    var s = String(name || '').toLowerCase();
    for (var i = 0; i < KNOWN_COLORS.length; i++) {
      if (KNOWN_COLORS[i][0].test(s)) return KNOWN_COLORS[i][1];
    }
    return FALLBACK_PALETTE[(idx || 0) % FALLBACK_PALETTE.length];
  }

  function pickPlatformLabel(o) {
    return o.platform || o.satellite_name || o.satellite || o.sensor || 'Unknown';
  }

  function normalizeObservation(o) {
    var obs = Object.assign({}, o);
    obs.platform_label = pickPlatformLabel(o);
    // frp: الرقم المطلوب للـ FRP bins؛ frp_raw: القيمة الأصلية للعرض (قد تكون null)
    obs.frp_raw = (typeof o.frp === 'number') ? o.frp : null;
    obs.frp = (typeof o.frp === 'number') ? o.frp : 0;
    obs.acq_date = o.acq_date || String(o.acq_datetime || '').slice(0, 10);
    obs.acq_datetime = o.acq_datetime || null;
    obs.confidence = (o.confidence === null || o.confidence === undefined) ? null : String(o.confidence);
    return obs;
  }

  function buildMeta(observations, extra) {
    var perPlatform = {}, platforms = [];
    observations.forEach(function (o) {
      if (!(o.platform_label in perPlatform)) {
        perPlatform[o.platform_label] = 0;
        platforms.push(o.platform_label);
      }
      perPlatform[o.platform_label]++;
    });
    platforms.sort(function (a, b) { return perPlatform[b] - perPlatform[a]; });
    return Object.assign({
      demo: true, source_label: '', count: observations.length,
      unique_grid_cells: null, date_range: null, region: null, disclaimer: null,
      platforms: platforms, per_platform: perPlatform
    }, extra || {});
  }

  /* ---------- live API ---------- */

  function obsToFeature(o) {
    return {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [o.longitude, o.latitude] },
      properties: Object.assign({}, o)
    };
  }

  async function loadLive(cfg) {
    // 1) overview → date range, region, disclaimer
    var ovRes = await fetchWithTimeout(cfg.apiBaseUrl + '/api/overview', cfg.apiTimeoutMs);
    if (!ovRes.ok) throw new Error('overview HTTP ' + ovRes.status);
    var ov = await ovRes.json();

    // 2) GeoJSON جاهز من السيرفر (أسرع طريق)
    var gjRes = await fetchWithTimeout(
      cfg.apiBaseUrl + '/api/hotspots/geojson?limit=' + MAX_LIMIT,
      cfg.apiTimeoutMs + 8000
    );
    if (!gjRes.ok) throw new Error('hotspots/geojson HTTP ' + gjRes.status);
    var fc = await gjRes.json();
    if (!fc || !Array.isArray(fc.features)) throw new Error('unexpected geojson shape');

    var observations = fc.features.map(function (f) {
      return normalizeObservation(f.properties);
    });

    // 3) pagination: لو فيه ملاحظات فوق الـ limit، نجيبها من /api/observations
    var total = (fc.metadata && typeof fc.metadata.total_matching === 'number')
      ? fc.metadata.total_matching : observations.length;
    while (observations.length < total) {
      var pgRes = await fetchWithTimeout(
        cfg.apiBaseUrl + '/api/observations?limit=' + PAGE_SIZE + '&offset=' + observations.length,
        cfg.apiTimeoutMs + 10000
      );
      if (!pgRes.ok) break;
      var pg = await pgRes.json();
      (pg.observations || []).forEach(function (o) { observations.push(normalizeObservation(o)); });
      if (!pg.count) break;  // أمان ضد اللوب اللانهائي
    }

    if (!observations.length) {
      throw new Error('API returned 0 observations (no processed data — run pipeline.py + harmonization.py)');
    }

    var meta = buildMeta(observations, {
      demo: false,
      source_label: 'Live API · ' + cfg.apiBaseUrl,
      unique_grid_cells: ov.unique_grid_cells,
      date_range: ov.date_range ? [ov.date_range.start, ov.date_range.end] : null,
      region: ov.region,
      disclaimer: ov.disclaimer
    });
    return { meta: meta, observations: observations };
  }

  /* ---------- demo fallback ---------- */

  function loadDemo() {
    var ds = window.FIRESYNC_DEMO_DATA;
    var observations = ds.observations.map(normalizeObservation);
    var label = 'Demo data (bundled sample)';
    if (lastError) label += ' · API: ' + lastError;
    var meta = buildMeta(observations, {
      demo: true,
      source_label: label,
      unique_grid_cells: ds.meta.unique_grid_cells,
      date_range: ds.meta.date_range,
      region: ds.meta.region,
      disclaimer: ds.meta.note
    });
    return Promise.resolve({ meta: meta, observations: observations });
  }

  /* ---------- public ---------- */

  async function loadHotspots() {
    var cfg = window.FIRESYNC_CONFIG;
    lastError = null;
    if (cfg.apiBaseUrl) {
      try {
        return await loadLive(cfg);
      } catch (err) {
        lastError = err.message;
        console.warn('API unreachable (' + err.message + ') → falling back to demo data.');
      }
    }
    return loadDemo();
  }

  function toGeoJSON(dataset) {
    return {
      type: 'FeatureCollection',
      features: dataset.observations.map(obsToFeature)
    };
  }

  return {
    loadHotspots: loadHotspots,
    toGeoJSON: toGeoJSON,
    platformColor: platformColor,
    getLastError: getLastError
  };
})();
