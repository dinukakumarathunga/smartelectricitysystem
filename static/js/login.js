// ============================================================
//  login.js
//  Handles the login form on 02_login.html.
//  Step 1 of the flow: username/password → OTP → dashboard
//  (or appliance onboarding, if this is the first login —
//  decided server-side by user.first_login_done).
//  Calls POST /auth/login (routes/auth_routes.py).
// ============================================================

(function () {
  'use strict';

  var usernameInput = document.getElementById('username');
  var passwordInput = document.getElementById('password');
  var btnLogin       = document.getElementById('btn-login');
  var formError      = document.getElementById('form-error');

  [usernameInput, passwordInput].forEach(function (el) {
    if (!el) return;
    el.addEventListener('input', function () {
      clearFieldError(el);
      hideFormError();
    });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') handleLogin();
    });
  });

  function validateForm() {
    var valid = true;
    if (!usernameInput.value.trim()) {
      showFieldError(usernameInput, 'Username or account number is required.');
      valid = false;
    }
    if (!passwordInput.value) {
      showFieldError(passwordInput, 'Password is required.');
      valid = false;
    }
    return valid;
  }

  async function handleLogin() {
    hideFormError();
    if (!validateForm()) return;

    setLoading(true);

    var result = await Api.postJSON('/auth/login', {
      username: usernameInput.value.trim(),
      password: passwordInput.value
    });

    if (!result.data.success) {
      setLoading(false);
      showFormError(result.data.message || 'Incorrect username/account number or password.');
      return;
    }

    window.location.href = '/03_otp_login.html';
  }

  if (btnLogin) btnLogin.addEventListener('click', handleLogin);

  // ── helpers ─────────────────────────────────────────────────
  function showFieldError(input, message) {
    input.classList.add('error');
    var errorEl = document.getElementById(input.id + '-error');
    if (errorEl) errorEl.textContent = message;
  }
  function clearFieldError(input) {
    input.classList.remove('error');
    var errorEl = document.getElementById(input.id + '-error');
    if (errorEl) errorEl.textContent = '';
  }
  function showFormError(message) {
    if (formError) { formError.textContent = message; formError.style.display = 'block'; }
  }
  function hideFormError() {
    if (formError) { formError.textContent = ''; formError.style.display = 'none'; }
  }
  function setLoading(state) {
    if (!btnLogin) return;
    btnLogin.disabled = state;
    btnLogin.textContent = state ? 'Signing in...' : 'Continue';
  }

})();
