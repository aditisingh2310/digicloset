# Local Run, UI Testing, and GDPR Checklist

This guide is the simplest way to run DigiCloset locally on Windows and sanity-check the product without needing to know the whole stack.

## Current status

- Backend GDPR and uninstall webhook paths are wired in the root app at `app/main.py`.
- Full Python test suite currently passes:

```bash
pytest tests
```

- Latest verified result:
  - `40 passed`
  - `3 skipped`

## 1. Backend: run the app locally

Open `cmd` in the repo root:

```bash
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
```

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Set the minimum environment variables for local boot:

```bash
set DATABASE_URL=sqlite:///./test.db
set SHOPIFY_API_KEY=dev-key
set SHOPIFY_API_SECRET=dev-secret
set CONTACT_EMAIL=you@example.com
set APP_URL=http://localhost:8000
```

Start the backend:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

What to open in the browser:

- [http://localhost:8000/health](http://localhost:8000/health)
- [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- [http://localhost:8000/docs](http://localhost:8000/docs)

If `/health` returns `{"status":"ok"}`, the backend is up.

## 2. Python tests

Run everything:

```bash
pytest tests
```

Run the GDPR and webhook tests only:

```bash
pytest tests/test_gdpr_uninstall.py tests/test_webhook_hmac.py tests/test_uninstall_webhook_cleanup.py tests/test_webhook_idempotency.py tests/test_webhook_queue_unavailable.py tests/test_oauth_hmac.py
```

What these cover:

- Shopify webhook HMAC validation
- uninstall webhook behavior
- duplicate webhook protection
- queue failure handling
- GDPR data request path

## 3. Admin UI: run locally

Open a second terminal in the repo root:

```bash
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
npm install
npm run dev
```

This starts the root Vite app. Open the URL shown in the terminal. It is usually:

- [http://localhost:5173](http://localhost:5173)

Pages to click through:

- `/`
- `/onboarding`
- `/pricing`

## 4. Widget UI: run locally

Open a third terminal:

```bash
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset\apps\shopify-widget"
npm install
npm run dev
```

The widget dev server is expected on:

- [http://localhost:3000](http://localhost:3000)

The widget expects the backend on port `8000`, so keep the backend running while testing.

You can also build the widget:

```bash
npm run build
```

Useful reference file for manual embedding:

- `apps/shopify-widget/example.html`

## 5. Manual UI/UX test checklist

Do not try to test everything at once. Use this exact order.

### Admin UI

1. Open the home page.
2. Confirm the navigation works.
3. Open onboarding.
4. Open pricing.
5. Shrink the browser width and confirm the layout still looks clean.

What to watch for:

- text overlapping
- buttons too close together
- broken spacing
- unreadable contrast
- cards jumping around between screen sizes

### Widget flow

1. Load the widget page.
2. Upload an image.
3. Confirm a loading state appears.
4. Confirm success state shows a result.
5. Turn the backend off and try again.
6. Confirm the error state is understandable.

What to watch for:

- upload button confusion
- unclear progress state
- no feedback after clicking
- ugly mobile layout
- result actions not obvious

### Mobile check

Use Chrome DevTools:

1. Open the page.
2. Press `F12`.
3. Click the device toolbar icon.
4. Test `iPhone 12` and a narrow Android width.

Look for:

- cut-off text
- controls off screen
- cramped forms
- image previews overflowing containers

## 6. GDPR status: what is already in place

The backend currently has webhook endpoints for:

- `app/uninstalled`
- `customers/data_request`
- `customers/redact`
- `shop/redact`

Relevant code:

- `app/api/webhooks.py`
- `app/services/data_deletion.py`
- `docs/data-deletion.md`
- `docs/shopify-webhooks.md`

The latest test pass confirms the uninstall and GDPR webhook path is working at the test level.

## 7. GDPR work still remaining

Passing tests does not mean full legal compliance is finished. These items still need product/legal confirmation:

1. Finalize the privacy policy text shown to merchants.
2. Finalize the terms text.
3. Confirm exactly what merchant data is stored and for how long.
4. Confirm who receives deletion requests at `CONTACT_EMAIL`.
5. Verify Shopify webhook subscriptions are registered in the deployed app.
6. Decide whether analytics, logs, or support tools store personal data.
7. If EU personal data is processed, make sure you have the right legal basis, retention policy, and vendor agreements.

## 8. Easiest test flow for you

If you just want the shortest possible loop:

1. Start backend with `python -m uvicorn app.main:app --reload --port 8000`
2. Run `pytest tests`
3. In another terminal run `npm run dev`
4. Open the Vite URL
5. Click home, onboarding, and pricing
6. In another terminal run the widget with `cd apps/shopify-widget && npm run dev`
7. Upload an image and check loading, success, and error states

## 9. Important note

For local backend testing, use the root app entrypoint:

```bash
app.main:app
```

That is the path the current tests are using.
