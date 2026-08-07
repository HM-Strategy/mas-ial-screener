# HM Strategy — MAS Investor Alert List Screening Agent

Automated screening and notification agent for the **MAS Investor Alert List (IAL)**.

- **Streamlit app** — bulk client screening against the IAL, individual name search, and an email-recipient manager.
- **Scheduled notifications** — a GitHub Actions workflow runs every 2 days, detects new IAL entries, and emails the configured recipients with a PDF report.
- **Live data** — pulls entries directly from MAS's public search API (no scraping of HTML).

## Features

- **Bulk Client Screening**: upload a CSV/Excel/JSON client list; fuzzy-matches every name (plus associates) against the IAL and flags confidence-scored matches.
- **Individual Name Search**: type-ahead search over IAL entries with alias support; on-demand PDF report.
- **Email Recipients manager**: add/remove who receives the automated alerts (writes back to `data/recipients.txt` in the repo).
- **Automated alerts**: every 2 days the workflow screens the list; if new entries exist, recipients get an email with a PDF of the new entries (silent when there is nothing new).
- **Live data**: reads the MAS Solr-based search API, with a local fallback file if the API is unreachable.

## Project layout

```
app.py                    Streamlit app (3 tabs: Bulk Screening, Name Search, Recipients)
main.py                   CLI orchestrator run by GitHub Actions
scraper.py                MAS IAL API client + fallback loader
matcher.py                Fuzzy/alias matching logic
report.py                 PDF report generation
emailer.py                Resend email delivery
recipients.py             Recipients file loader + GitHub push (PyGithub)
data/recipients.txt       Email recipients (one per line, managed via the app)
data/mas_snapshot.json    Snapshot of known entries (committed, updated by workflow)
data/ial_fallback.json    Offline fallback if API is unreachable
.github/workflows/notify.yml   Cron job (every 2 days, 06:00 SGT)
```

## Local setup

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy the environment file and fill in values
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

### Required secrets (.env for local / GitHub Actions secrets / Streamlit secrets)

| Key | Description |
|---|---|
| `RESEND_API_KEY` | Resend API key (`re_...`) |
| `FROM_EMAIL` | Sender address (use `onboarding@resend.dev` for testing, `info@hmstrategy.com` for production) |
| `app_password` | Password gate for the Streamlit app |
| `GITHUB_TOKEN` | Fine-grained PAT with Contents: read/write on this repo (Tab 3 recipient manager) |
| `GITHUB_REPO` | Repository name: `HM-Strategy/mas-ial-screener` |
| `RECIPIENTS_PATH` | `data/recipients.txt` |

### Run locally

```bash
# Screen IAL and email recipients (--force-email overrides the silence rule for testing)
python main.py --force-email

# Launch the Streamlit app (password required)
streamlit run app.py
```

## Deployment

### 1. Deploy the Streamlit app

1. Go to [Streamlit Cloud](https://streamlit.io/cloud) and create an app from this repo (`main` branch, `app.py`).
2. In the app's **Settings > Secrets**, add all the keys listed above.
3. The app is publicly accessible but password-protected.

### 2. Set GitHub Actions secrets

Repo > Settings > Secrets and variables > Actions > New repository secret:

| Secret | Value |
|---|---|
| `RESEND_API_KEY` | `re_...` from Resend |
| `FROM_EMAIL` | `info@hmstrategy.com` (requires Resend domain verification) |

### 3. Resend domain verification (production)

1. In [Resend](https://resend.com/domains), add `hmstrategy.com`.
2. Add the provided SPF/DKIM DNS records to your domain.
3. Once verified, the cron emails will deliver from `info@hmstrategy.com`.

Until domain verification is complete, the cron still runs and updates the snapshot — it just cannot deliver email.

## How it works

```
GitHub Actions cron (every 2 days)
        |
        v
  main.py
        |
  scraper.py  -----> MAS IAL API (Solr REST endpoint)
        |
  snapshot diff  (new entries vs data/mas_snapshot.json)
        |
  report.py  -----> PDF with new entries
        |
  emailer.py -----> Resend API  -----> email with PDF to all recipients
        |
  snapshot saved
```

**Silence rule**: if no new entries are detected, no email is sent.

## Data sources

The agent reads the MAS Investor Alert List via a public REST API:

```
GET https://www.mas.gov.sg/api/v1/ialsearch
    ?q=date_dt:[2017-01-01T00:00:00Z TO *]
    &rows=1000
    &sort=date_dt desc
```

No API key or authentication required. If the API is unreachable, the agent falls back to `data/ial_fallback.json`.

## License

Internal use — HM Strategy.
