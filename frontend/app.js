const api = async (path, opts = {}) => {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.detail || JSON.stringify(payload));
  return payload;
};

let settings = {
  selected_variants: [],
  selected_mockups: [],
  copy_previous: true,
};
let latestAnalysis = null;
let latestListing = null;
let loadedVariants = [];
let loadedMockups = [];

const $ = (id) => document.getElementById(id);

function bindTabs() {
  document.querySelectorAll('.nav').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      btn.classList.add('active');
      $(btn.dataset.tab).classList.add('active');
    });
  });
}

function hydrateSettingsForm() {
  ['watch_folder', 'printify_api_key', 'printify_shop_id', 'blueprint_id', 'print_provider_id', 'base_price', 'profit_percent'].forEach((k) => {
    if ($(k)) $(k).value = settings[k] ?? '';
  });
  $('copy_previous').checked = !!settings.copy_previous;
  updateVariantLimit();
}

async function loadSettings() {
  settings = await api('/settings');
  if (!settings.selected_variants) settings.selected_variants = [];
  if (!settings.selected_mockups) settings.selected_mockups = [];
  hydrateSettingsForm();
}

async function saveSettings() {
  settings.watch_folder = $('watch_folder').value.trim();
  settings.printify_api_key = $('printify_api_key').value.trim();
  settings.printify_shop_id = $('printify_shop_id').value.trim();
  settings.blueprint_id = Number($('blueprint_id').value || 0);
  settings.print_provider_id = Number($('print_provider_id').value || 0);
  settings.base_price = $('base_price').value ? Number($('base_price').value) : null;
  settings.profit_percent = $('profit_percent').value ? Number($('profit_percent').value) : null;
  settings.copy_previous = $('copy_previous').checked;
  await api('/settings', { method: 'POST', body: JSON.stringify(settings) });
}

function setStatus(el, text, ok = true) {
  el.textContent = text;
  el.className = ok ? 'ok' : 'error';
}

async function refreshMonitorStatus() {
  try {
    const s = await api('/monitor/status');
    setStatus(
      $('monitor_status'),
      `Monitoring: ${s.monitoring ? 'ON' : 'OFF'} | Folder: ${s.watch_folder || '-'} | Queue: ${s.queue_size} | Current: ${s.current_file || '-'}`,
      true
    );
  } catch (e) {
    setStatus($('monitor_status'), e.message, false);
  }
}

async function refreshDashboard() {
  const [stats, runs, logs] = await Promise.all([api('/dashboard'), api('/runs'), api('/logs')]);
  $('stat_total').textContent = stats.total_products;
  $('stat_draft').textContent = stats.draft_products;
  $('stat_logs').textContent = stats.total_logs;
  $('stat_errors').textContent = stats.error_logs;

  $('recent_runs').innerHTML = runs.length
    ? runs.slice(0, 8).map((r) => `<div class="run"><b>${r.status.toUpperCase()}</b> | ${r.image_path} ${r.printify_product_id ? `| draft: ${r.printify_product_id}` : ''}${r.error_message ? ` | <span class='error'>${r.error_message}</span>` : ''}</div>`).join('')
    : '<div class="muted">[ NO PRODUCTS YET ] Upload images to start creating products</div>';

  $('runs_json').textContent = JSON.stringify(runs, null, 2);
  $('logs_json').textContent = JSON.stringify(logs, null, 2);
}

function prettyAnalysis(analysis, listing) {
  return [
    `THEME:\n${analysis.theme}`,
    `STYLE:\n${analysis.style}`,
    `MOOD:\n${analysis.mood}`,
    `AUDIENCE:\n${analysis.target_audience}`,
    `CAPTION:\n${analysis.caption}`,
    `TITLE:\n${listing.title}`,
    `BULLETS:\n${listing.bullets.map((b) => `• ${b}`).join('\n')}`,
    `TAGS:\n${listing.tags.join(', ')}`,
    `DESCRIPTION:\n${listing.description}`,
  ].join('\n\n');
}

function updateVariantLimit() {
  const count = (settings.selected_variants || []).length;
  $('variant_limit').textContent = `Variants selected: ${count}/100 ${count >= 100 ? '(MAX LIMIT REACHED)' : ''}`;
  $('variant_limit').className = count >= 100 ? 'error' : 'muted';
}

function colorHex(name) {
  const map = {
    black: '#0f1115', white: '#ffffff', navy: '#1f2a5a', red: '#d11a2a', blue: '#1f60dc', green: '#1a8d51',
    yellow: '#e6c700', orange: '#e17e1c', pink: '#d56a97', purple: '#7d51c2', gray: '#7b8799', grey: '#7b8799',
  };
  return map[(name || '').toLowerCase()] || '#d8dce6';
}

function renderVariants() {
  const selectedIds = new Set((settings.selected_variants || []).map((v) => v.variant_id));
  $('variants').innerHTML = loadedVariants.map((v) => {
    const active = selectedIds.has(v.id);
    const color = v.options?.color || v.title || 'color';
    return `<button class="chip ${active ? 'active' : ''}" data-variant="${v.id}"><span class="color" style="background:${colorHex(color)}"></span>${v.title || v.id}</button>`;
  }).join('');

  document.querySelectorAll('[data-variant]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = Number(btn.dataset.variant);
      const exists = settings.selected_variants.find((x) => x.variant_id === id);
      if (exists) settings.selected_variants = settings.selected_variants.filter((x) => x.variant_id !== id);
      else settings.selected_variants.push({ variant_id: id, enabled: true, price: 1999 });
      if (settings.selected_variants.length > 100) {
        settings.selected_variants = settings.selected_variants.slice(0, 100);
        alert('Printify limit is 100 variants.');
      }
      updateVariantLimit();
      renderVariants();
      await saveSettings();
    });
  });

  updateVariantLimit();
}

function renderMockups() {
  const selected = new Set(settings.selected_mockups || []);
  $('mockups').innerHTML = loadedMockups.map((m) => `<button class="chip ${selected.has(m.mockup_id) ? 'active' : ''}" data-mockup="${m.mockup_id}">${m.display_name || m.mockup_id}</button>`).join('');
  document.querySelectorAll('[data-mockup]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.mockup;
      if (selected.has(id)) settings.selected_mockups = settings.selected_mockups.filter((x) => x !== id);
      else settings.selected_mockups.push(id);
      renderMockups();
      await saveSettings();
    });
  });
}

function bindActions() {
  $('btn_save_settings').addEventListener('click', async () => {
    try { await saveSettings(); setStatus($('monitor_status'), 'Settings saved', true); }
    catch (e) { setStatus($('monitor_status'), e.message, false); }
  });

  $('btn_monitor_start').addEventListener('click', async () => {
    try { await saveSettings(); await api('/monitor/start', { method: 'POST' }); await refreshMonitorStatus(); }
    catch (e) { setStatus($('monitor_status'), e.message, false); }
  });

  $('btn_monitor_stop').addEventListener('click', async () => {
    try { await api('/monitor/stop', { method: 'POST' }); await refreshMonitorStatus(); }
    catch (e) { setStatus($('monitor_status'), e.message, false); }
  });

  $('btn_reset').addEventListener('click', async () => {
    await api('/settings/reset', { method: 'POST' });
    await loadSettings();
    setStatus($('upload_status'), 'Settings reset', true);
  });

  $('btn_analyze').addEventListener('click', async () => {
    try {
      await saveSettings();
      const image_path = $('image_path').value.trim();
      const result = await api('/analyze', { method: 'POST', body: JSON.stringify({ image_path }) });
      latestAnalysis = result.analysis;
      latestListing = result.listing;
      $('analysis_result').textContent = prettyAnalysis(result.analysis, result.listing);
      setStatus($('upload_status'), 'Analysis complete', true);
    } catch (e) {
      setStatus($('upload_status'), e.message, false);
    }
  });

  $('btn_create').addEventListener('click', async () => {
    try {
      await saveSettings();
      const image_path = $('image_path').value.trim();
      const result = await api('/draft', { method: 'POST', body: JSON.stringify({ image_path, analysis: latestAnalysis, listing: latestListing }) });
      setStatus($('upload_status'), `Draft created: ${result.printify_product_id}`, true);
      await refreshDashboard();
    } catch (e) {
      setStatus($('upload_status'), e.message, false);
    }
  });

  $('btn_queue').addEventListener('click', async () => {
    try {
      const image_path = $('image_path').value.trim();
      const result = await api('/queue', { method: 'POST', body: JSON.stringify({ image_path }) });
      setStatus($('upload_status'), `Queued: ${result.queued_path}`, true);
      await refreshMonitorStatus();
    } catch (e) {
      setStatus($('upload_status'), e.message, false);
    }
  });

  $('btn_fetch_variants').addEventListener('click', async () => {
    await saveSettings();
    loadedVariants = (await api(`/printify/variants?blueprint_id=${settings.blueprint_id}&print_provider_id=${settings.print_provider_id}`)).variants || [];
    renderVariants();
  });

  $('btn_select_all').addEventListener('click', async () => {
    settings.selected_variants = loadedVariants.slice(0, 100).map((v) => ({ variant_id: v.id, enabled: true, price: v.price || 1999, cost: v.cost }));
    renderVariants();
    await saveSettings();
  });

  $('btn_clear_variants').addEventListener('click', async () => {
    settings.selected_variants = [];
    renderVariants();
    await saveSettings();
  });

  $('btn_fetch_mockups').addEventListener('click', async () => {
    await saveSettings();
    loadedMockups = (await api(`/printify/mockups?blueprint_id=${settings.blueprint_id}&print_provider_id=${settings.print_provider_id}`)).mockups || [];
    renderMockups();
  });
}

async function bootstrap() {
  bindTabs();
  bindActions();
  await loadSettings();
  await refreshMonitorStatus();
  await refreshDashboard();
  setInterval(refreshMonitorStatus, 4000);
  setInterval(refreshDashboard, 7000);
}

bootstrap();
