import os
import json
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

from scraper import scrape_mas_ial
from matcher import match_batch
from report import generate_notification_report
from emailer import send_notification_email
from recipients import load_recipients

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

SNAPSHOT_PATH = "data/mas_snapshot.json"
CLIENT_LIST_PATH = "data/client_list.csv"


def load_snapshot() -> set[tuple[str, str]]:
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Snapshot is not a list")
        return {(e["name"], e["date_added"]) for e in data if "name" in e}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Could not load snapshot (%s). Starting fresh.", e)
        return set()


def save_snapshot(entries: list[dict]):
    try:
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        logger.info("Snapshot saved (%d entries).", len(entries))
    except OSError as e:
        logger.error("Failed to save snapshot: %s", e)


def load_clients() -> list[str]:
    if not os.path.isfile(CLIENT_LIST_PATH):
        logger.info("No client list found at %s. Skipping cross-reference.", CLIENT_LIST_PATH)
        return []

    try:
        import pandas as pd
        df = pd.read_csv(CLIENT_LIST_PATH, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(CLIENT_LIST_PATH, encoding="latin-1")
        except Exception as e:
            logger.error("Failed to read client list: %s", e)
            return []
    except Exception as e:
        logger.error("Failed to read client list: %s", e)
        return []

    name_keywords = ["name", "client", "company", "entity", "organisation", "organization"]
    name_col = next(
        (col for col in df.columns if any(kw in col.lower() for kw in name_keywords)),
        df.columns[0],
    )
    names = df[name_col].dropna().astype(str).tolist()
    logger.info("Loaded %d client names (column: %s).", len(names), name_col)
    return names


def main():
    parser = argparse.ArgumentParser(description="MAS IAL Notification Engine")
    parser.add_argument("--force-email", action="store_true",
                        help="Send email even on first run (for testing)")
    args = parser.parse_args()

    logger.info("Starting MAS IAL screening run.")

    current = scrape_mas_ial()
    if not current:
        logger.error("Failed to scrape MAS IAL. Exiting.")
        return

    previous = load_snapshot()
    is_first_run = not previous

    new_entries = [e for e in current if (e["name"], e["date_added"]) not in previous]

    if not new_entries:
        logger.info("No new entries. Silence.")
        save_snapshot(current)
        return

    logger.info("%d new entries found.", len(new_entries))

    if is_first_run and not args.force_email:
        logger.info("First run — populating baseline snapshot. No email sent.")
        save_snapshot(current)
        return

    client_names = load_clients()
    matches = match_batch(client_names, new_entries) if client_names else []

    pdf = generate_notification_report(new_entries, matches)

    recipients = load_recipients()
    if not recipients:
        logger.error("No recipients configured. Cannot send email.")
        return

    success = send_notification_email(recipients, pdf, len(new_entries), len(matches))
    if success:
        logger.info("Email sent to %d recipient(s).", len(recipients))
    else:
        logger.error("Failed to send email.")

    save_snapshot(current)


if __name__ == "__main__":
    main()
