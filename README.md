# FileForge 2.0 — Unified Project

This replaces both `~/fileforge` (backend/frontend fragments + a separate,
much larger multi-platform product) and `~/fileforge-web-site` (the Next.js
site). Everything the web app needs — backend, worker, ffmpeg abstraction,
frontend, CLI, launcher — now lives in this one directory.

**Not included:** `android2/`, `windows/`, `desktop/`, `cloud-api/`,
`license-server/`, `magisk-module/`, and the `src/fileforge/` multi-format
CLI+licensing library that were bundled inside the old `~/fileforge`. Those
are a separate product line your spec didn't describe touching — they're
untouched and still wherever they were.

## Layout

```
fileforge/
├── backend/            FastAPI app, ffmpeg/ImageMagick/Pandoc engine, Redis worker
├── app/                 Next.js App Router pages + API proxy routes
├── components/           Dashboard UI components
├── cli/fileforge-cli      Bash CLI over the dashboard API
├── fileforge-launcher.sh  Starts Redis + backend + worker + frontend together
├── scripts/               Termux setup (install_conversion_tools.sh)
└── package.json / next.config.js / tailwind.config.js / tsconfig.json
```

## Running it

**Termux:**
```bash
./scripts/install_conversion_tools.sh   # ffmpeg, ImageMagick, Pandoc, Redis, proot Ubuntu for LibreOffice
npm install
./fileforge-launcher.sh                 # Redis + backend (:8091) + worker + frontend (:8090)
```

**Linux/macOS (dev):**
```bash
pip install -r backend/requirements.txt
npm install
cd backend && ./run_backend.sh &        # :8091
./run_worker.sh &                       # needs redis-server running
cd .. && npm run dev                    # :8090
```

Open `http://127.0.0.1:8090/conversion-dashboard`.

## What was actually broken, and what I fixed

I read every file in both directories before touching anything — this
isn't a rewrite from the spec alone, it's a real merge. Here's what was
actually wrong with the code as it existed:

**Backend never really worked:**
- `server.py` and four `server_*_patch.py` files (batch, queue, thumbnails,
  compression) each created their **own separate `FastAPI()` instance**.
  `server.py` never imported any of them. Only `/convert` ever actually
  ran on the live server — `/batch-convert`, `/queue-convert`,
  `/thumbnail/*`, `/compress/video` all 404'd. Fixed by merging all five
  into one `app` via `APIRouter`, and verified all 15 routes respond
  (tested with real files through ffmpeg/ImageMagick, not just imports).
- `server.py` used `from .engine import ...` (relative import) while
  `run_backend.sh` ran `uvicorn server:app` directly — that combination
  throws `ImportError: attempted relative import with no known parent
  package` the moment any endpoint is hit. Switched every backend module
  to absolute imports.
- `backend/queue.py` shadowed Python's stdlib `queue` module for every
  other file in the package. Renamed to `ff_queue.py` and updated
  `run_worker.sh` and `server.py` accordingly.
- `engine.py`'s SVG→PNG and HEIC→JPG special cases were dead code — a
  broader `if ext in [".png", ...]` check above them caught those
  extensions first, so the special-cased converters could never run.
  Reordered so specific cases are checked before general ones.
- `requirements.txt` was missing `redis`, despite `ff_queue.py` and
  `run_worker.sh` depending on it.

**Frontend was mostly unwired scaffolding:**
- `wire_endpoints.sh` and `wire_ui_components.sh` — which generate the 6
  missing API routes and all 5 dashboard components — were never
  actually run. None of their output files existed anywhere in either
  directory. I used their code as the intended design and actually
  generated the files.
- Those scripts' heredocs had a literal stray `\;` baked into every
  `const BACKEND = "...":` line, which would have broken the TypeScript
  build the moment they were run. Fixed.
- `fileforge-web-site/app/api/convert/route.ts` was a JSON-based mock
  that never called any backend. `fileforge/app/api/convert/route.ts`
  was the real, working multipart proxy. Kept the real one; the mock
  version of `app/conversion/page.tsx` that matched it is gone too.
- **The project would not have built at all.** `package.json` pins
  Tailwind v4, but `globals.css` used Tailwind v3's `@tailwind base/
  components/utilities` syntax with no `@config` directive — v4 never
  loaded `tailwind.config.js`'s custom theme colors, so every
  `fileforgeBg`/`fileforgeAccent`/etc. class in every component would
  fail the build with "Cannot apply unknown utility class." Fixed by
  switching to `@import "tailwindcss";` plus `@config
  "../tailwind.config.js";`. I confirmed this by actually running
  `next build` — first reproducing the failure, then verifying the
  fix compiles clean and the compiled CSS contains the real theme
  rules (`#0f0f0f` background, `#ff6b00` accent, etc.).
- Next.js 16 also hard-errors on `next build` if a custom `webpack()`
  config exists without an explicit Turbopack opt-out — it doesn't
  silently fall back the way earlier versions did. Added `--webpack`
  to the `build` script (it was already on `dev`), and dropped the
  `eslint` key from `next.config.js`, which Next 16 now rejects outright.
- `@types/react-dom` was referenced in `tsconfig.json`'s `types` array
  but never added to `package.json` — `tsc` failed immediately. Added it.
- `app/page.tsx` used `ff-card-title` / `ff-hero-title` / etc. classes
  that were never defined in `globals.css` — silently unstyled. Added
  the missing tokens.
- The dynamic route handlers (`queue-status/[jobId]`, etc.) used
  `{ params }: any` with synchronous `params.jobId` access — Next.js 15+
  made route params a `Promise`, so this throws at runtime on the
  pinned Next 16. Fixed to `await params` throughout.
- Dashboard API routes (`/api/dashboard/jobs|queue|thumbs`) returned
  hardcoded fake data. They now proxy to real backend endpoints I added
  (`/dashboard/jobs`, `/dashboard/queue`, `/dashboard/thumbs`) backed by
  actual job history and real Redis queue depth.
- The 5 dashboard components had a real type bug: buttons used
  `onClick={handleSubmit}` where `handleSubmit` was typed to accept a
  `React.FormEvent`, not a `MouseEvent` — wrapped each in a proper
  `<form onSubmit={...}>` instead, which also gets you Enter-to-submit
  for free. `Thumbnails.tsx` had no error handling at all — a failed
  conversion would try to render an error-JSON response as an image.
  Added proper `res.ok` checks throughout.

**Scripts:**
- `fileforge-cli` did an unconditional `shift` that crashes on zero
  arguments, and had no file-existence checks before handing paths to
  curl. Fixed both, added a proper `--help`-style usage screen.
- `fileforge-launcher.sh` never cleaned up its background processes —
  Ctrl+C left uvicorn/worker/npm orphaned. Added a `trap ... EXIT INT
  TERM` cleanup handler and a final `wait`. Also fixed the hardcoded
  `$HOME/fileforge-web-site` path now that everything lives in one
  directory, and it derives its root from its own location instead of
  assuming `$HOME/fileforge`.

Everything above was verified by actually running it in a sandboxed
Linux container — real `ffmpeg`/`ImageMagick` conversions, a real Redis
queue processed by the actual worker loop, a real `next build`, and the
full browser → Next.js → FastAPI proxy chain end to end — not just
written and assumed to work.
