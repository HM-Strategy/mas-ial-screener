import os
import re
import logging

logger = logging.getLogger(__name__)

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "recipients.txt")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def load_recipients(path: str = DEFAULT_PATH) -> list[str]:
    if not os.path.isfile(path):
        logger.warning("Recipients file not found at %s. Returning empty list.", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        logger.error("Failed to read recipients file: %s", e)
        return []

    emails = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = stripped.split("#")[0].strip()
        if not stripped:
            continue
        emails.append(stripped)
    logger.info("Loaded %d recipient(s).", len(emails))
    return emails


def save_recipients_local(emails: list[str], path: str = DEFAULT_PATH) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "# Email recipients for the MAS IAL notification email.\n"
                "# One email address per line. Lines starting with # are ignored.\n"
                "# Managed via the Streamlit app (Tab 3: Email Recipients).\n\n"
            )
            for email in emails:
                f.write(email.strip() + "\n")
        logger.info("Saved %d recipient(s) locally.", len(emails))
        return True
    except OSError as e:
        logger.error("Failed to save recipients locally: %s", e)
        return False


def _get_secret(name: str) -> str:
    val = os.getenv(name)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(name, "")
    except Exception:
        return ""


def push_recipients_to_github(emails: list[str], path: str = DEFAULT_PATH) -> tuple[bool, str]:
    token = _get_secret("GITHUB_TOKEN")
    repo_name = _get_secret("GITHUB_REPO")
    repo_path = _get_secret("RECIPIENTS_PATH") or "data/recipients.txt"

    if not token or not repo_name:
        ok = save_recipients_local(emails, path)
        msg = (
            "GitHub not configured — saved locally only."
            if ok
            else "Failed to save recipients locally."
        )
        return ok, msg

    try:
        from github import Github

        g = Github(token)
        repo = g.get_repo(repo_name)
        contents = repo.get_contents(repo_path)

        body = (
            "# Email recipients for the MAS IAL notification email.\n"
            "# One email address per line. Lines starting with # are ignored.\n"
            "# Managed via the Streamlit app (Tab 3: Email Recipients).\n\n"
        )
        body += "\n".join(e.strip() for e in emails) + "\n"

        if contents.decoded_content.decode("utf-8") == body:
            return True, "Recipients unchanged — nothing to push."

        repo.update_file(
            repo_path,
            f"Update email recipients ({len(emails)} address(es))",
            body,
            contents.sha,
        )
        logger.info("Pushed %d recipient(s) to GitHub.", len(emails))
        return True, f"Recipients saved and pushed to repository ({len(emails)} address(es))."
    except Exception as e:
        logger.error("Failed to push recipients to GitHub: %s", e)
        return False, f"Failed to push to GitHub: {e}"
