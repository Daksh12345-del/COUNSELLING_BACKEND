# Sarvpratham Backend

This is the real database + API for sarvprathameduconsultants.com. It replaces the old
setup where the "Free Enquiry" form and "Schedule a Free Call" widget were just writing
into the visitor's own browser (localStorage) — meaning nobody actually received that
data, and the hardcoded "admin123" password offered no real protection.

What you get instead:
- A PostgreSQL database that actually stores every enquiry and every booked call
- A Node.js/Express API the website talks to
- A real admin login (hashed password + session token, not a hardcoded string)
- Double-booking protection at the database level, so two people can never grab the same call slot
- Basic spam protection (rate limiting) on the public forms

This was built and tested end-to-end (including the actual website pages clicking through
the forms and the admin dashboard) before being handed to you — it works as shipped, but you
will need to follow the setup steps below to point it at your own database and server.

## 1. Requirements

- Node.js 18 or newer
- A PostgreSQL database (you mentioned you already have hosting that supports this)

## 2. Setup

```bash
cd sarvpratham-backend
npm install
cp .env.example .env
```

Open `.env` and fill in:
- `DATABASE_URL` — your PostgreSQL connection string
- `JWT_SECRET` — a long random string (the file tells you how to generate one)
- `ALLOWED_ORIGINS` — your website's real domain(s), so only your site can call this API
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — the login you'll use for the dashboard (only needed once, see step 4)

## 3. Create the database tables

```bash
npm run migrate
```

This runs `schema.sql` against your database. It's safe to run more than once.

## 4. Create your admin account

```bash
npm run create-admin
```

This reads `ADMIN_USERNAME`/`ADMIN_PASSWORD` from `.env`, hashes the password with bcrypt, and
stores the account. After this runs once, you can delete `ADMIN_PASSWORD` from `.env` — it's
only ever read by this one script, never by the running server.

To change the password later, just update `ADMIN_PASSWORD` in `.env` and run `npm run create-admin`
again — it updates the existing account instead of creating a duplicate.

## 5. Run the server

```bash
npm start
```

You should see `Sarvpratham backend listening on port 4000` (or whatever `PORT` you set).

For production, keep this running with a process manager so it survives reboots/crashes,
for example [pm2](https://pm2.keymetrics.io/):

```bash
npm install -g pm2
pm2 start src/server.js --name sarvpratham-backend
pm2 save
```

If your hosting puts the website and this API on the same domain, set up a reverse proxy
(e.g. Nginx) so requests to `https://sarvprathameduconsultants.com/api/...` forward to this
server's port. That's what the frontend's `config.js` assumes by default (`API_BASE_URL = '/api'`).
If the API will live on its own subdomain/port instead, change that one line in `config.js`
on the website to point at it.

## What's in the database

Two tables, plus an admin_users table for login:

**enquiries** — everyone who fills the "Free Enquiry" form: name, phone, email, current class,
stream, course interest, city, message, and a status you can update (New / Contacted /
Enrolled / Not interested).

**bookings** — everyone who books a free call: name, phone, preferred contact method (Phone /
Google Meet / WhatsApp), the date and time slot, stream/course interest, and a status (Confirmed /
Completed / Cancelled / No-show).

Full column definitions are in `schema.sql`, which is also the migration script — comments inline explain each piece.

## API endpoints (for reference)

Public (used by the website forms):
- `POST /api/enquiries` — submit the enquiry form
- `POST /api/bookings` — book a call slot
- `GET /api/bookings/availability?date=YYYY-MM-DD` — which slots are already taken that day

Admin (require a login token):
- `POST /api/admin/login` — get a session token
- `GET /api/admin/stats` — dashboard numbers
- `GET /api/admin/enquiries` — list/search/filter enquiries
- `PATCH /api/admin/enquiries/:id` — update an enquiry's status
- `DELETE /api/admin/enquiries/:id`
- `GET /api/admin/enquiries-export` — download all enquiries as CSV
- `GET /api/admin/bookings` — list bookings
- `PATCH /api/admin/bookings/:id` — update a booking's status
- `DELETE /api/admin/bookings/:id`

## Security notes

- Passwords are hashed with bcrypt — the real password is never stored anywhere.
- Admin sessions expire after 12 hours by default (`JWT_EXPIRES_IN` in `.env`); the dashboard
  will quietly ask to log in again after that.
- The public form endpoints are rate-limited (8 submissions per 15 minutes per visitor) to
  discourage spam scripts, without affecting real visitors.
- All database queries use parameterized statements, so there's no SQL injection risk from
  form input.
- `ALLOWED_ORIGINS` restricts which websites are allowed to call this API — set it to your real
  domain(s) before going live, otherwise any website could submit fake data.

## If something doesn't work

- "Cannot connect to database" → double check `DATABASE_URL` and that your database server
  allows connections from wherever this backend runs.
- Admin login fails right after `create-admin` → make sure `ADMIN_USERNAME` matches exactly
  what you type into the dashboard (it's case-sensitive).
- Forms on the website show "Something went wrong" → open the browser console; if you see a
  CORS error, your real domain isn't in `ALLOWED_ORIGINS` yet.
