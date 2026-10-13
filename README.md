## Memoshpere

### Email verification

Apply the database migration from `project_1_be` with `alembic upgrade head` before running the updated backend. Existing accounts remain verified; new accounts must verify their email before login.

In development, email delivery defaults to console mode. The backend log prints the verification link, which opens the frontend at `http://localhost:5173/auth`.

For SMTP delivery, set `EMAIL_DELIVERY_MODE=smtp`, `SMTP_HOST`, and `SMTP_FROM_EMAIL`. Set `SMTP_PORT` (default `587`), and `SMTP_USERNAME` / `SMTP_PASSWORD` if the server requires authentication. Set `FRONTEND_BASE_URL` to the frontend origin. The token lifetime defaults to 24 hours and can be changed with `EMAIL_VERIFICATION_EXPIRE_HOURS`.

Production defaults to SMTP mode. Do not enable console delivery in production because verification links are bearer credentials.
