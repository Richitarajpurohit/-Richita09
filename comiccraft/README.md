# ComicCraft - AI Comic Story Creator (Gemini + Stable Diffusion)

Enter a story idea, character, setting, tone and art style. ComicCraft builds a 5-panel comic:

1. **Gemini Flash** writes the panel outline (JSON)
2. **Gemini Pro** writes narration, captions and dialogue
3. **Stable Diffusion** (Hugging Face Diffusers) paints each panel
4. `layout_builder.py` matches images with text, `exporters.py` builds the PDF (fpdf2)
5. You preview in the browser, download the PDF, and land on the export-success page

## Project layout

```
comiccraft/
├── app/  main.py routes.py config.py errors.py gemini_client.py gemini_flash.py
│         gemini_pro.py image_generator.py layout_builder.py exporters.py
├── templates/  index.html  comic_preview.html  export_success.html
├── static/  css/  panels/ (generated images)  exports/ (PDFs)  fonts/ (DejaVu, bundled)
├── tests/test_offline.py
├── .vscode/launch.json
├── .env.example        requirements.txt
```

## 1. Prerequisites

- Python 3.10 - 3.12 (3.11 recommended), VS Code with the Python extension
- A free Gemini API key: https://aistudio.google.com/apikey
- ~6 GB free disk for the Stable Diffusion download (first generation only)
- A GPU is optional. On CPU each panel takes roughly 1-5 minutes (see "Speed tips").

## 2. Open in VS Code

Unzip, then **File > Open Folder...** and choose the `comiccraft` folder.
Open a terminal (**Terminal > New Terminal**); all commands below run from the project root.

## 3. Create the virtual environment

Windows (PowerShell):
```
python -m venv venv
venv\Scripts\Activate.ps1
```
If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process Bypass` once, or use `venv\Scripts\activate.bat` in cmd.

macOS / Linux:
```
python3 -m venv venv
source venv/bin/activate
```
Then press **Ctrl+Shift+P > Python: Select Interpreter** and pick the `venv` one.

## 4. Install dependencies

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
NVIDIA GPU users: install the CUDA build of PyTorch *first* (pick your CUDA version at https://pytorch.org/get-started/locally), e.g.
```
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

## 5. Configure your keys

```
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```
Open `.env` and set `GEMINI_API_KEY=...`. Everything else has working defaults.

## 6. Run

```
uvicorn app.main:app --reload --reload-dir app
```
Or press **F5** in VS Code and choose **ComicCraft: run FastAPI**.

Open http://127.0.0.1:8000 (app) and http://127.0.0.1:8000/docs (API docs).

## 7. Test

1. **Offline smoke test** (no keys, no GPU, no downloads): `python -m tests.test_offline`
   should print `OK - offline pipeline works`.
2. **Health check:** http://127.0.0.1:8000/health should show `"gemini_key_configured": true`.
3. **Fast UI test without waiting for Stable Diffusion:** set `USE_PLACEHOLDER_IMAGES=true` in `.env`, restart, and generate a comic. You get real Gemini text with placeholder images. Set it back to `false` for real art.
4. **Image only:** http://127.0.0.1:8000/test-image (first call downloads the model, be patient).
5. **Full flow in the browser:** fill the form > Generate comic > review panels > Download comic as PDF > success page.
6. **JSON API** (PowerShell: use `curl.exe`):
```
curl -X POST http://127.0.0.1:8000/generate-comic/json -H "Content-Type: application/json" \
  -d "{\"prompt\":\"A brave fox exploring an enchanted forest\",\"character_name\":\"Finn\",\"setting\":\"forest\",\"tone\":\"funny\",\"style\":\"comic book\"}"
```

## Routes

| Route | Purpose |
|---|---|
| `GET /` | Input form |
| `POST /generate` | Form submit, runs the pipeline, shows the preview |
| `POST /generate-comic/json` | Same pipeline for API clients, returns layout + PDF path |
| `GET /download/{file}` | Serves an exported PDF |
| `GET /export-success` | Confirmation page |
| `GET /test-image` | Image generation test |
| `GET /health` | Configuration status |

## Settings (.env)

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | none | Required |
| `GEMINI_FLASH_MODEL` / `GEMINI_PRO_MODEL` | `gemini-2.5-flash` / `gemini-2.5-pro` | Falls back to `*-latest` aliases, and Pro falls back to Flash if quota-limited |
| `SD_MODEL_ID` | `stable-diffusion-v1-5/stable-diffusion-v1-5` | |
| `IMAGE_SIZE`, `INFERENCE_STEPS` | 512, 25 | Lower for speed |
| `USE_PLACEHOLDER_IMAGES` | false | Skip Stable Diffusion |
| `ALLOW_PLACEHOLDER_FALLBACK` | true | If Stable Diffusion fails, draw a placeholder instead of erroring |

## Speed tips (CPU)

Set `IMAGE_SIZE=384` and `INFERENCE_STEPS=15` in `.env`. Generation happens once per panel (5 total), and the model loads on the first request only.

## Troubleshooting

- **"GEMINI_API_KEY is not set"**: `.env` must be in the project root (next to `requirements.txt`); restart the server after editing.
- **Gemini 404 / model not found**: models get renamed; set `GEMINI_FLASH_MODEL` / `GEMINI_PRO_MODEL` to a current name from https://ai.google.dev/gemini-api/docs/models.
- **Gemini 429 / quota**: wait a minute or use Flash for both by setting `GEMINI_PRO_MODEL` to the Flash model name.
- **Panels show "Placeholder panel"**: Stable Diffusion failed to load; read the terminal for the reason (usually out of memory or a blocked download). Set `ALLOW_PLACEHOLDER_FALLBACK=false` to see the error in the browser instead.
- **CUDA out of memory**: lower `IMAGE_SIZE` to 384.
- **`ModuleNotFoundError: app`**: run commands from the project root, not from inside `app/`.

## Differences from the original documentation

These were changed so the project actually runs today:

- `gemini-1.5-*` models are retired, so current models are used (configurable).
- `google-generativeai` is deprecated, so the maintained `google-genai` SDK is used.
- `runwayml/stable-diffusion-v1-5` was removed from Hugging Face, so the community mirror `stable-diffusion-v1-5/stable-diffusion-v1-5` is used.
- `fpdf` (v1) is replaced by `fpdf2`, its maintained successor with the same `from fpdf import FPDF` import.
- The story parser is tolerant of Gemini formatting differences instead of splitting on a fixed string.
- Extra routes: `/download/{file}` and `/health`. The unused `result.html` / `all_users.html` templates from the Milestone 5 text are not needed.

Bundled font: DejaVu Sans (free license), used for Unicode support in the PDF.
