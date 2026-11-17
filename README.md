## Memoshpere

### Email verification

Apply the database migration from `project_1_be` with `alembic upgrade head` before running the updated backend. Existing accounts remain verified; new accounts must verify their email before login.

In development, email delivery defaults to console mode. The backend log prints the verification link, which opens the frontend at `http://localhost:5173/auth`.

For SMTP delivery, set `EMAIL_DELIVERY_MODE=smtp`, `SMTP_HOST`, and `SMTP_FROM_EMAIL`. Set `SMTP_PORT` (default `587`), and `SMTP_USERNAME` / `SMTP_PASSWORD` if the server requires authentication. Set `FRONTEND_BASE_URL` to the frontend origin. The token lifetime defaults to 24 hours and can be changed with `EMAIL_VERIFICATION_EXPIRE_HOURS`.

Production defaults to SMTP mode. Do not enable console delivery in production because verification links are bearer credentials.

### Feed pagination

`GET /posts` returns up to 20 visible posts by default. Use `limit` (1-100) to change the page size, and pass the returned `next_cursor` as `cursor` to fetch the next page. The response contains `posts` and `next_cursor`; a `null` cursor means there are no more posts. Use `category_id` to filter a category feed on the server.

### Drafts

Saving a post as a draft stores it in the database without publishing it. Authenticated users can list their drafts with `GET /posts/me/drafts` and load one of their drafts with `GET /posts/me/drafts/{post_id}`. Update a draft with `PUT /posts/{post_id}`; set `is_draft` to `false` when ready to publish. Draft queries are restricted to the signed-in author.

### Global search

Authenticated clients can call `GET /search?q=...` to search usernames and post titles, excerpts, and content. The initial response contains separate `users` and `posts` pages, each with `items` and `next_cursor`. To load more of one result type, pass the same `q`, set `section=users` or `section=posts`, and send that section's cursor. Search returns usernames only for user results and excludes drafts and posts the viewer cannot access.

### Sharing posts

Apply the latest migration with `alembic upgrade head` before using post sharing. Authenticated clients can `POST /posts/{post_id}/share` with `{"recipient_ids": [1, 2]}`. Recipients must be active followers of the sender, and the sender must be able to view the non-draft post. Each recipient gets an in-app notification. Sharing does not grant access: opening the notification still applies the post's existing visibility rules.

### Opt-in writing assistant

Set `GOOGLE_API_KEY` in the backend environment (never in the frontend) to enable the authenticated `POST /ai/writing-assistant` endpoint. It uses `gemini-3.5-flash-lite` by default; set `GEMINI_MODEL` to override the model. The endpoint accepts `polish_content`, `suggest_title`, or `suggest_excerpt` tasks and returns a suggestion without saving or publishing it. The composer sends draft text only when the user explicitly requests a suggestion, and applies it only after the user chooses to use it. With unpaid Gemini API quota, Google may use prompts and responses to improve products, and human reviewers may process them. Avoid submitting sensitive, confidential, or personal information; review Google's Gemini API terms for the data handling that applies to your billing status.
