# Share Text

Share encrypted text with a link that expires automatically. The frontend is a Vite/React app in `frontend`; the API is FastAPI in `backend` and uses PostgreSQL.

## Expiry and capacity

- A share expires after the selected period (1 hour to 7 days; 24 hours by default).
- Owners can cap successful reads (including one-time links) and optionally protect a share with a password. Passwords are stored as salted scrypt hashes. Incorrect or missing passwords do not consume a view.
- View-limited reads lock the share row and increment the counter in the same PostgreSQL transaction as reading. The final allowed read returns its text and removes the stored ciphertext atomically; concurrent reads cannot exceed the configured limit.
- API reads reject expired links even if physical cleanup is waiting to run.
- Each API process runs a cleanup worker. Workers claim expired rows in batches using PostgreSQL `FOR UPDATE SKIP LOCKED`, then delete ciphertext and its association in one transaction. This supports multiple Uvicorn workers and replicas without double processing.
- Text writes and deletes are transactional. Management operations lock their secret row so concurrent edits/deletes are serialized. The database pool can be sized with `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` per process; set these with the total replica count and PostgreSQL connection budget in mind.
- With `REDIS_URL` configured, all API processes share an atomic Redis sliding-window rate limit per client IP (120 requests per 60 seconds by default). Redis is checked at startup; an outage returns `503` rather than silently bypassing the limit. Without Redis, the process-local limiter is intended only for development. When behind a proxy, configure Uvicorn to trust only that proxy so `request.client.host` identifies the real client safely.
- `/metrics` exposes Prometheus request counters and latency histograms with route-template labels. It is process-local; run one Uvicorn worker per container and let Prometheus scrape each replica directly. Restrict this endpoint to your monitoring network at the ingress.
- `backend/loadtests/share_load.js` is a k6 profile for concurrent create/read throughput and racing readers against a one-time share. Run it against staging with `k6 run -e BASE_URL=https://staging.example.com -e RATE=20 -e DURATION=30s backend/loadtests/share_load.js`. Its latency and error thresholds are starting points; tune them to your deployment's service objectives. At `RATE=20`, raise the staging client limit above 3,600 requests per minute and use isolated data before running it.
- Run `backend/migrations/001_text_expiry.sql` once against an existing database before deploying this version. New database installs should create tables from the SQLAlchemy models and then apply the migration as well.
- Then run `backend/migrations/002_share_access_controls.sql` once to add view limits and password hashes.

## Configuration

Required backend environment variables: `DATABASE_URL` and a valid Fernet `CRYPT_SECRET_KEY`. Set `REDIS_URL` (for example `redis://localhost:6379/0`) to enable shared production rate limiting. Other optional settings include `CORS_ALLOW_ORIGINS`, `MAX_REQUEST_BODY_BYTES`, `DB_POOL_SIZE`, and `DB_MAX_OVERFLOW`. The request size default supports the API's 40,000-character text limit.

## API

- `POST /text/store` accepts `{ "text": "...", "ttl_hours": 24, "max_views": 1, "password": "optional password" }`. `max_views` and `password` are optional; a password must be at least 8 characters.
- `POST /text/{text_id}/read` with `{ "password": "..." }` reads a share. Successful reads consume the optional view limit; missing or wrong passwords do not.
- `GET /text/{text_id}` remains available for unprotected shares.
- `POST /text/manage`, `PUT /text/edit`, and `DELETE /text/delete` use the secret key for management.

Run the API from `backend` with Uvicorn and the frontend from `frontend` with `npm run dev`.
