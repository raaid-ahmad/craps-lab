# craps-lab web

React + TypeScript + Vite frontend for the craps-lab simulator.

## Run locally

The frontend talks to the FastAPI backend in `api/`. Start both:

```bash
# Terminal 1 — API
uvicorn api.main:app --reload

# Terminal 2 — Vite dev server (proxies /api to http://localhost:8000)
cd web
npm install
npm run dev
```

Then open http://localhost:5173.

## Scripts

- `npm run dev` — Vite dev server with HMR
- `npm run build` — typecheck + production build into `dist/`
- `npm run lint` — ESLint
- `npm run preview` — serve the production build locally

See the [root README](../README.md) for the full project overview.
