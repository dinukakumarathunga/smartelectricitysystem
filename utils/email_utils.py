# ============================================================
#  utils/email_utils.py
#  Sends transactional email (currently just OTP codes) via
#  smtplib directly — no Flask-Mail dependency needed since
#  everything it'd give us (SMTP config) is already read
#  straight from app.config here.
#
#  If MAIL_USERNAME/MAIL_PASSWORD aren't set (e.g. local dev
#  before you've configured a real mailbox), this falls back to
#  logging the email to the console instead of failing — mirrors
#  the "demo mode" OTP note that used to live in otp.js before
#  the backend existed.
# ============================================================

import smtplib
from email.mime.text import MIMEText

from flask import current_app


def send_email(to_address, subject, body):
    cfg = current_app.config

    if not cfg.get('MAIL_USERNAME') or not cfg.get('MAIL_PASSWORD'):
        print(
        '[DEV EMAIL — no SMTP credentials configured]\n'
        f'To: {to_address}\nSubject: {subject}\n{body}'
    )
    return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = cfg.get('MAIL_DEFAULT_SENDER') or cfg['MAIL_USERNAME']
    msg['To'] = to_address

    with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT']) as server:
        if cfg.get('MAIL_USE_TLS'):
            server.starttls()
        server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        server.sendmail(msg['From'], [to_address], msg.as_string())
