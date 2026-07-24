"""License-delivery email. Uses SMTP when configured; otherwise logs to stdout
so local/dev runs and tests never try to send real mail.

Configure with:
    FF_SMTP_HOST, FF_SMTP_PORT, FF_SMTP_USER, FF_SMTP_PASS, FF_SMTP_FROM
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_license_email(to: str, key: str, tier: str) -> bool:
    body = (
        f"Thanks for buying FileForge {tier.title()}!\n\n"
        f"Your license key:\n\n    {key}\n\n"
        "Activate it by setting the environment variable:\n\n"
        f"    export FILEFORGE_LICENSE=\"{key}\"\n\n"
        "Then run `fileforge license --status` to confirm. Keep this key safe.\n"
    )
    host = os.environ.get("FF_SMTP_HOST")
    if not host:
        # Dev/test fallback: don't fail fulfillment just because mail isn't set up.
        print(f"[emailer:noop] would send {tier} key to {to}: {key}")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Your FileForge {tier.title()} license key"
    msg["From"] = os.environ.get("FF_SMTP_FROM", os.environ.get("FF_SMTP_USER", "no-reply@fileforge.local"))
    msg["To"] = to
    msg.set_content(body)

    port = int(os.environ.get("FF_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as s:  # pragma: no cover - network
        s.starttls()
        user, pw = os.environ.get("FF_SMTP_USER"), os.environ.get("FF_SMTP_PASS")
        if user and pw:
            s.login(user, pw)
        s.send_message(msg)
    return True
