git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/REPO.git
git push -u origin main
# Printify Product Automation – Render Deployment (Free)

You said you want **Render**, not localhost. Follow these exact steps.

## 1) Push project to GitHub
1. Create a GitHub repo.
2. Upload this full project.

## 2) Deploy on Render
1. Go to Render dashboard.
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repo.
4. Render will detect `render.yaml` and create the web service automatically.

## 3) Set required environment variables in Render
In Render service settings, add:
- `PRINTIFY_API_KEY` = your Printify API key
- `PRINTIFY_SHOP_ID` = your Printify Shop ID
- `OLLAMA_MODEL` = `llama3.1:8b` (or keep default)

Already configured in `render.yaml`:
- `DATABASE_PATH=/tmp/app.db`
- `STORAGE_DIR=/tmp/data`

## 4) Open your Render URL
After deploy succeeds, open your service URL:
- `https://<your-service-name>.onrender.com`

Health check:
- `https://<your-service-name>.onrender.com/api/health`

## 5) Important note about AI on Render free tier
Render free tier does **not** run local Ollama server by default.
This app now handles that safely:
- if Ollama is unavailable, app still runs,
- analysis/listing uses deterministic fallback text,
- Printify draft creation still works.

## 6) If deploy fails
Check Render logs for:
- missing env vars (`PRINTIFY_API_KEY`, `PRINTIFY_SHOP_ID`)
- Python install/build errors

Then redeploy.

---

## Files used for Render
- `render.yaml`
- `Procfile`
