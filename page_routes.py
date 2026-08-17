# ============================================================
#  page_routes.py
#  Serves the 12 HTML templates. No business logic lives here —
#  that's routes/auth_routes.py, routes/bill_routes.py, etc.
#  (built next). This file only decides WHICH page a request
#  is allowed to see, using the session keys those route files
#  will set:
#
#    session['user_id']       — set on successful OTP verification
#    session['otp_verified']  — set on successful OTP verification
#    session['pending_otp']   — set when an OTP has just been sent,
#                                 required to reach 03_otp_login.html
#    session['pending_ocr']   — set after a successful bill/SMS
#                                 upload, required to reach
#                                 06_upload_confirm.html
#
#  Route paths deliberately match the exact filenames the
#  frontend already navigates to (window.location.href =
#  '05_upload_bill.html', etc. in the JS files) so none of the
#  already-built JS needs to change just to run under Flask.
# ============================================================

from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

page_bp = Blueprint('pages', __name__)


# ── guards ────────────────────────────────────────────────────
def login_required(view):
    """Redirects to the login page unless a verified session exists."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not (session.get('user_id') and session.get('otp_verified')):
            return redirect(url_for('pages.login'))
        return view(*args, **kwargs)
    return wrapped


def otp_pending_required(view):
    """
    03_otp_login.html only makes sense right after a register/login
    call has just sent a code — bounce back to login otherwise
    (e.g. someone bookmarks the OTP page directly).
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('pending_otp'):
            return redirect(url_for('pages.login'))
        return view(*args, **kwargs)
    return wrapped


def ocr_pending_required(view):
    """06_upload_confirm.html needs a just-uploaded result to review."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('pending_ocr'):
            return redirect(url_for('pages.upload_bill'))
        return view(*args, **kwargs)
    return wrapped


# ── entry point ──────────────────────────────────────────────
@page_bp.route('/')
def index():
    if session.get('user_id') and session.get('otp_verified'):
        return redirect(url_for('pages.dashboard'))
    return redirect(url_for('pages.register'))


# ── 1. register → login + OTP ───────────────────────────────
@page_bp.route('/01_register.html')
def register():
    return render_template('01_register.html')


@page_bp.route('/02_login.html')
def login():
    return render_template('02_login.html')


@page_bp.route('/03_otp_login.html')
@otp_pending_required
def otp_login():
    return render_template('03_otp_login.html')


# ── 2. first login → appliance onboarding ───────────────────
@page_bp.route('/04_appliance_onboarding.html')
@login_required
def appliance_onboarding():
    return render_template('04_appliance_onboarding.html')


# ── 3 & 4. upload bill/SMS → analyse → confirm → dashboard ──
@page_bp.route('/05_upload_bill.html')
@login_required
def upload_bill():
    return render_template('05_upload_bill.html')


@page_bp.route('/06_upload_confirm.html')
@login_required
@ocr_pending_required
def upload_confirm():
    return render_template('06_upload_confirm.html')


@page_bp.route('/07_dashboard.html')
@login_required
def dashboard():
    return render_template('07_dashboard.html')


# ── 5. AI prediction & recommendations ───────────────────────
@page_bp.route('/08_ai_prediction.html')
@login_required
def ai_prediction():
    return render_template('08_ai_prediction.html')


@page_bp.route('/09_recommendations.html')
@login_required
def recommendations():
    return render_template('09_recommendations.html')


# ── account / data pages ─────────────────────────────────────
@page_bp.route('/10_reports.html')
@login_required
def reports():
    return render_template('10_reports.html')


@page_bp.route('/11_appliance_profile.html')
@login_required
def appliance_profile():
    return render_template('11_appliance_profile.html')


@page_bp.route('/12_security.html')
@login_required
def security():
    return render_template('12_security.html')
