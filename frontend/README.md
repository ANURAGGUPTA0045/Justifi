# JustiFi frontend

The React/Vite interface includes a dashboard, legal assistant, document
explainer, source explorer, privacy center, and local settings. It submits
questions and consent-gated document analyses to the FastAPI backend and
renders retrieved citations, limitations, and service errors.

## Run locally

1. Start the backend from `../backend/` using the setup steps in
   [`../backend/README.md`](../backend/README.md).
2. From this directory, run:

   ```powershell
   npm install
   npm run dev
   ```

The Vite development server proxies `/api` requests to
`http://127.0.0.1:8000`. Set `VITE_API_TARGET` in the frontend environment if
the backend runs on a different local address. Configure browser origins on
the backend with `CORS_ORIGINS` when using a non-proxied deployment.

## Checks

```powershell
npm run lint
npm run build
```

Language and theme preferences are stored in browser local storage.
Conversations remain in memory for the current browser session only and are
not stored in MongoDB. The frontend contains no API credentials.
