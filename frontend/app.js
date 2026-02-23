const api = async (path, opts = {}) => {
  const res = await fetch(`/api${path}`, opts);
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.detail || JSON.stringify(payload));
  return payload;
};

let settings = {
  selected_variants: [],
  selected_mockups: [],
};

let latestAnalysis = null;
let latestListing = null;

const $ = (id) => document.getElementById(id);

function setStatus(el, text, ok = true) {
  el.textContent = text;
  el.className = ok ? 'ok' : 'error';
}

async function saveSettings() {
  settings.printify_api_key = $('printify_api_key').value.trim();
  settings.printify_shop_id = $('printify_shop_id').value.trim();
  settings.blueprint_id = Number($('blueprint_id').value || 0);
  settings.print_provider_id = Number($('print_provider_id').value || 0);
  settings.base_price = $('base_price').value ? Number($('base_price').value) : null;
  settings.profit_percent = $('profit_percent').value ? Number($('profit_percent').value) : null;

  await api('/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
}

function bindActions() {

  $('btn_analyze').addEventListener('click', async () => {
    try {
      await saveSettings();

      const file = $('image_file').files[0];
      if (!file) return setStatus($('upload_status'), "Please select image", false);

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch('/api/analyze', {
        method: "POST",
        body: formData
      });

      const result = await res.json();

      latestAnalysis = result.analysis;
      latestListing = result.listing;

      $('analysis_result').textContent = JSON.stringify(result.analysis, null, 2);

      setStatus($('upload_status'), 'Analysis complete', true);

    } catch (e) {
      setStatus($('upload_status'), e.message, false);
    }
  });

  $('btn_create').addEventListener('click', async () => {
    try {
      await saveSettings();

      const file = $('image_file').files[0];
      if (!file) return setStatus($('upload_status'), "Please select image", false);

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch('/api/draft', {
        method: "POST",
        body: formData
      });

      const result = await res.json();

      setStatus($('upload_status'), `Draft created: ${result.printify_product_id}`, true);

    } catch (e) {
      setStatus($('upload_status'), e.message, false);
    }
  });
}

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

async function bootstrap() {
  bindTabs();
  bindActions();
}

bootstrap();
