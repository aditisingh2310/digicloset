# Beginner Local Setup

This is the easiest way to run DigiCloset on Windows if you are starting from zero.

The goal of this guide is:

1. boot the root backend
2. run the admin UI
3. run the widget UI shell
4. run tests
5. understand which API keys are real and which can be fake for local work

## 1. What you are running

There are three useful local pieces in this repo:

- root backend: `app.main:app`
- root admin UI: the Vite app in the repo root
- storefront widget UI: `apps/shopify-widget`

Important honesty up front:

- the root backend and admin UI are the easiest local setup
- the widget UI can run locally
- the widget's real try-on API flow points at `/api/v1/*` endpoints and is part of a broader service stack under `services/`
- if you only start the root backend, use the widget mainly for layout and basic UI checks

## 2. Install the software first

You need:

- Python 3.11+
- Node.js 18+
- Git
- optional: Docker Desktop if you want local Redis

Quick checks in `cmd`:

```bat
python --version
node --version
npm --version
git --version
```

If one of those fails, install it first before continuing.

## 3. Open the project folder

Open `cmd` and run:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
```

## 4. Create your local `.env` file

This repo now has an example env file:

- [.env.example](C:/Users/anime/3D%20Objects/DigiIPI/digicloset/.env.example)

Copy it:

```bat
copy .env.example .env
```

Open it:

```bat
notepad .env
```

### Use these values for the simplest local run

If you only want the app to boot and tests to run, this is enough:

```env
DATABASE_URL=sqlite:///./test.db
REDIS_URL=redis://localhost:6379/0
REDIS_REQUIRED=0
APP_URL=http://localhost:8000
CONTACT_EMAIL=you@example.com
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
SHOPIFY_API_KEY=dev-key
SHOPIFY_API_SECRET=dev-secret
SHOPIFY_API_VERSION=2024-01
DEBUG=1
```

### What each key means

- `DATABASE_URL`: where the backend stores data locally
- `REDIS_URL`: used for sessions, queues, and some webhook/runtime features
- `APP_URL`: base URL of your backend
- `CONTACT_EMAIL`: used for policy/compliance contact info
- `SHOPIFY_API_KEY`: Shopify client id
- `SHOPIFY_API_SECRET`: Shopify client secret

## 5. Where to get the real Shopify API keys

You only need real Shopify keys if you want a real Shopify install/OAuth flow.

Go here:

1. Log in to Shopify Partner Dashboard.
2. Open your app.
3. Open the app's API credentials page.
4. Copy the client id into `SHOPIFY_API_KEY`.
5. Copy the client secret into `SHOPIFY_API_SECRET`.

For real Shopify installs, your `APP_URL` must be a public HTTPS URL, not `http://localhost:8000`.

## 6. Optional but recommended: run Redis

If you have Docker Desktop, run Redis like this:

```bat
docker run --name digicloset-redis -p 6379:6379 redis:7
```

If you skip Redis:

- the backend can still start
- some queue/session features are limited
- `/health` still returns OK by default for local use because `REDIS_REQUIRED=0`

## 7. Run the backend

Still in the repo root:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Leave that terminal open.

### Open these URLs in your browser

- [http://localhost:8000/docs](http://localhost:8000/docs)
- [http://localhost:8000/privacy](http://localhost:8000/privacy)
- [http://localhost:8000/terms](http://localhost:8000/terms)
- [http://localhost:8000/health](http://localhost:8000/health)
- [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

What to expect:

- `/docs` should open Swagger UI
- `/privacy` and `/terms` should load text pages
- `/health/ready` should tell you whether required Shopify keys exist

## 8. Run the Python tests

Open a second `cmd` window:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
.venv\Scripts\activate
pytest tests
```

Current expected result:

- `65 passed`
- `3 skipped`

The three skips are currently normal in this local Windows setup:

- one RQ/worker test is skipped because the installed `rq` path expects `fork`
- two integration tests skip if no live local API session is being targeted

## 9. Run the admin UI

Open a third `cmd` window:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
npm install
npm run dev
```

Open the URL shown in the terminal. It is usually:

- [http://localhost:5173](http://localhost:5173)

Check these pages:

- [http://localhost:5173/](http://localhost:5173/)
- [http://localhost:5173/onboarding](http://localhost:5173/onboarding)
- [http://localhost:5173/pricing](http://localhost:5173/pricing)

This is the easiest part of the app to test locally.

## 10. Run the widget UI

Open a fourth `cmd` window:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset\apps\shopify-widget"
npm install
npm run dev
```

Open:

- [http://localhost:3000](http://localhost:3000)

Important note:

- the widget dev server proxies `/api/*` to `http://localhost:8000`
- the current widget client code expects `/api/v1/*` backend routes
- that means the widget shell can run locally, but the full try-on generation flow is not guaranteed from the root backend alone

Use the widget locally for:

- layout checks
- upload UI checks
- loading/error state checks
- responsive behavior

## 11. Beginner-safe test order

Do it in this order:

1. Boot backend
2. Open `/docs`
3. Run `pytest tests`
4. Start root frontend
5. Open `/`, `/onboarding`, `/pricing`
6. Start widget
7. Check the widget layout and interactions

## 12. Common beginner problems

### Problem: `python` is not recognized

Install Python and reopen `cmd`.

### Problem: `npm` is not recognized

Install Node.js and reopen `cmd`.

### Problem: port `8000` or `5173` is already in use

Stop the old process or use another port.

Example:

```bat
python -m uvicorn app.main:app --reload --port 8010
```

If you change the backend port, also update `APP_URL` in `.env` to match it.

### Problem: `/health` is not fully healthy

Most likely Redis is not running.

Either:

- start Redis with Docker
- or continue anyway if you are only doing basic local UI/testing

If you want local Redis to be mandatory, set:

```env
REDIS_REQUIRED=1
```

### Problem: Shopify install flow does not work

That is expected if:

- you are using fake `SHOPIFY_API_KEY` and `SHOPIFY_API_SECRET`
- your `APP_URL` is just `http://localhost:8000`

For real Shopify install tests, you need:

- real Shopify credentials
- a public HTTPS URL
- matching callback/webhook configuration

## 13. Which keys are actually required?

### For basic local boot and tests

You can use:

- fake `SHOPIFY_API_KEY`
- fake `SHOPIFY_API_SECRET`
- real `CONTACT_EMAIL`

That is enough to:

- boot the root backend
- run tests
- run the admin UI

### For real Shopify OAuth/install tests

You need real:

- `SHOPIFY_API_KEY`
- `SHOPIFY_API_SECRET`
- `APP_URL` on HTTPS

### For the broader try-on service stack

You may also need real values for services outside the root app, such as:

- `REPLICATE_API_TOKEN`
- `REDIS_URL`
- a proper database URL

## 14. If you want the absolute shortest version

Use these commands in order:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Then in a new terminal:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
.venv\Scripts\activate
pytest tests
```

Then in another terminal:

```bat
cd "C:\Users\anime\3D Objects\DigiIPI\digicloset"
npm install
npm run dev
```

Open:

- `http://localhost:5173`

If you want, the next thing I should write is a second guide for the full widget/try-on stack under `services/`, because that setup is more advanced than the root app boot.
