// ============================================================
//  register.js
//  Handles the registration form on 01_register.html.
//  Step 1 of the flow: register → OTP → appliance onboarding.
//  Calls POST /auth/register (routes/auth_routes.py). Client-side
//  checks below are just for quick feedback — the backend
//  re-validates everything regardless, so nothing here is relied
//  on for actual security.
// ============================================================

(function () {
  'use strict';

  var fields = {
    full_name:        document.getElementById('full_name'),
    username:         document.getElementById('username'),
    account_number:   document.getElementById('account_number'),
    email:            document.getElementById('email'),
    mobile:           document.getElementById('mobile'),
    password:         document.getElementById('password'),
    confirm_password: document.getElementById('confirm_password')
  };
  var consentCheck = document.getElementById('consent');
  var btnRegister  = document.getElementById('btn-register');
  var formError    = document.getElementById('form-error');

  Object.keys(fields).forEach(function (key) {
    var el = fields[key];
    if (el) el.addEventListener('input', function () {
      clearFieldError(el);
      hideFormError();
    });
  });

  function validateForm() {
    var valid = true;

    if (!fields.full_name.value.trim()) {
      showFieldError(fields.full_name, 'Full name is required.');
      valid = false;
    }
    if (!fields.username.value.trim() || fields.username.value.trim().length < 3) {
      showFieldError(fields.username, 'Username must be at least 3 characters.');
      valid = false;
    }
    if (!fields.account_number.value.trim()) {
      showFieldError(fields.account_number, 'Your electricity account number is required.');
      valid = false;
    }
    if (!fields.email.value.trim() || !isValidEmail(fields.email.value.trim())) {
      showFieldError(fields.email, 'Please enter a valid email address.');
      valid = false;
    }
    if (!fields.password.value || fields.password.value.length < 8) {
      showFieldError(fields.password, 'Password must be at least 8 characters.');
      valid = false;
    }
    if (fields.confirm_password.value !== fields.password.value) {
      showFieldError(fields.confirm_password, 'Passwords do not match.');
      valid = false;
    }
    if (consentCheck && !consentCheck.checked) {
      showFormError('You must agree to the privacy notice to continue.');
      valid = false;
    }

    return valid;
  }

  async function handleRegister() {
    hideFormError();
    if (!validateForm()) return;

    setLoading(true);

    var result = await Api.postJSON('/auth/register', {
      full_name:        fields.full_name.value.trim(),
      username:         fields.username.value.trim(),
      account_number:   fields.account_number.value.trim(),
      email:            fields.email.value.trim().toLowerCase(),
      mobile:           fields.mobile.value.trim(),
      password:         fields.password.value,
      confirm_password: fields.confirm_password.value
    });

    if (!result.data.success) {
      setLoading(false);
      showFormError(result.data.message || 'Registration failed. Please try again.');
      return;
    }

    // Backend has already sent the OTP and set the pending-otp
    // session state — just navigate to the verification screen.
    window.location.href = '/03_otp_login.html';
  }

  if (btnRegister) btnRegister.addEventListener('click', handleRegister);

  // ── helpers ─────────────────────────────────────────────────
  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

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
    if (!btnRegister) return;
    btnRegister.disabled = state;
    btnRegister.textContent = state ? 'Creating account...' : 'Create account';
  }

})();
