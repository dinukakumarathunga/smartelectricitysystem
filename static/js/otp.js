// ============================================================
//  otp.js
//  Handles OTP verification on 03_otp_login.html.
//  - Auto-advances between digit boxes
//  - 5-minute countdown (matches OTP_EXPIRY_MINUTES in config.py)
//  - Resend
//  - Calls POST /auth/verify-otp and POST /auth/resend-otp
//    (routes/auth_routes.py). The code itself is now actually
//    emailed/texted by the backend (or logged to the server
//    console in dev mode if no mail/SMS provider is configured —
//    see utils/login_utils.py) — the frontend never sees or
//    displays it, unlike the old localStorage-only prototype.
// ============================================================

(function () {
  'use strict';

  var otpBoxes     = document.querySelectorAll('.otp-box');
  var btnVerify    = document.getElementById('btn-verify');
  var btnResend    = document.getElementById('btn-resend');
  var timerDisplay = document.getElementById('timer-value');
  var formError    = document.getElementById('form-error');
  var statusNote   = document.getElementById('otp-status-note');

  // ── OTP box behaviour ───────────────────────────────────────
  otpBoxes.forEach(function (box, index) {
    box.addEventListener('keypress', function (e) {
      if (!/[0-9]/.test(e.key)) e.preventDefault();
    });

    box.addEventListener('input', function () {
      box.value = box.value.replace(/[^0-9]/g, '').slice(-1);
      if (box.value && index < otpBoxes.length - 1) otpBoxes[index + 1].focus();
      box.classList.toggle('filled', box.value !== '');
      hideFormError();
    });

    box.addEventListener('keydown', function (e) {
      if (e.key === 'Backspace' && !box.value && index > 0) {
        otpBoxes[index - 1].focus();
        otpBoxes[index - 1].value = '';
        otpBoxes[index - 1].classList.remove('filled');
      }
      if (e.key === 'Enter') handleVerify();
    });

    box.addEventListener('paste', function (e) {
      var pasted = (e.clipboardData || window.clipboardData).getData('text');
      var digits = pasted.replace(/[^0-9]/g, '').slice(0, otpBoxes.length);
      if (digits.length === otpBoxes.length) {
        e.preventDefault();
        digits.split('').forEach(function (digit, i) {
          otpBoxes[i].value = digit;
          otpBoxes[i].classList.add('filled');
        });
        otpBoxes[otpBoxes.length - 1].focus();
      }
    });
  });

  if (otpBoxes[0]) otpBoxes[0].focus();

  // ── Countdown timer ─────────────────────────────────────────
  // Mirrors OTP_EXPIRY_MINUTES (config.py) — purely a UI countdown;
  // the backend is the actual source of truth for expiry.
  var timeLeft = 5 * 60;
  var timerInterval;

  function startTimer() {
    clearInterval(timerInterval);
    timeLeft = 5 * 60;
    timerInterval = setInterval(function () {
      timeLeft--;
      var minutes = Math.floor(timeLeft / 60);
      var seconds = timeLeft % 60;
      if (timerDisplay) {
        timerDisplay.textContent = String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
      }
      if (timeLeft <= 0) {
        clearInterval(timerInterval);
        if (timerDisplay) timerDisplay.textContent = '00:00';
        showFormError('Your code may have expired — request a new one below.');
      }
    }, 1000);
  }
  startTimer();

  // ── Get the code from boxes ─────────────────────────────────
  function getOTPCode() {
    return Array.from(otpBoxes).map(function (box) { return box.value; }).join('');
  }

  // ── Verify ───────────────────────────────────────────────────
  async function handleVerify() {
    hideFormError();

    var code = getOTPCode();
    if (code.length < otpBoxes.length) {
      showFormError('Please enter all 6 digits.');
      otpBoxes.forEach(function (box) { if (!box.value) box.style.borderColor = 'var(--danger, #c0392b)'; });
      return;
    }

    setLoading(true);

    var result = await Api.postJSON('/auth/verify-otp', { otp: code });

    if (result.data.success) {
      clearInterval(timerInterval);
      otpBoxes.forEach(function (box) {
        box.style.borderColor = 'var(--success, #10B981)';
        box.style.background  = 'rgba(16,185,129,0.08)';
      });
      if (btnVerify) btnVerify.textContent = 'Verified!';
      setTimeout(function () {
        window.location.href = result.data.redirect || '/07_dashboard.html';
      }, 500);
    } else {
      setLoading(false);
      showFormError(result.data.message || 'Incorrect or expired code. Please try again.');
      otpBoxes.forEach(function (box) {
        box.style.borderColor = 'var(--danger, #c0392b)';
        box.value = '';
        box.classList.remove('filled');
      });
      otpBoxes[0].focus();
    }
  }

  // ── Resend ───────────────────────────────────────────────────
  async function handleResend(e) {
    if (e) e.preventDefault();
    if (btnResend) { btnResend.style.pointerEvents = 'none'; btnResend.style.opacity = '0.5'; }

    var result = await Api.postJSON('/auth/resend-otp', {});

    if (btnResend) { btnResend.style.pointerEvents = 'auto'; btnResend.style.opacity = '1'; }

    if (!result.data.success) {
      showFormError(result.data.message || 'Failed to resend the code. Please log in again.');
      return;
    }

    startTimer();
    otpBoxes.forEach(function (box) { box.value = ''; box.classList.remove('filled'); box.style.borderColor = ''; });
    otpBoxes[0].focus();
    hideFormError();
    if (statusNote) statusNote.textContent = 'A new code was sent to your registered email or phone.';
    if (btnVerify) { btnVerify.disabled = false; btnVerify.style.opacity = '1'; }
  }

  if (btnVerify) btnVerify.addEventListener('click', handleVerify);
  if (btnResend) btnResend.addEventListener('click', handleResend);

  // ── Helpers ─────────────────────────────────────────────────
  function setLoading(state) {
    if (!btnVerify) return;
    btnVerify.disabled = state;
    btnVerify.textContent = state ? 'Verifying...' : 'Verify and continue';
    btnVerify.style.opacity = state ? '0.7' : '1';
  }
  function showFormError(message) {
    if (formError) { formError.textContent = message; formError.style.display = 'block'; formError.style.color = 'var(--danger, #c0392b)'; }
  }
  function hideFormError() {
    if (formError) { formError.textContent = ''; formError.style.display = 'none'; }
  }

})();
