// ============================================================
//  security.js
//  Powers 12_security.html.
//  - Change password (POST /profile/change-password)
//  - Registered mobile number + recent login activity
//    (GET /profile/)
//  - "Download my data" (GET /profile/export → client-side
//    Blob download, same pattern as reports.js's CSV export)
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  loadProfile();

  var currentPwInput = document.getElementById('current_password');
  var newPwInput     = document.getElementById('new_password');
  var confirmPwInput = document.getElementById('confirm_password');
  var btnUpdatePw    = document.getElementById('btn-update-password');
  var pwFormError    = document.getElementById('pw-form-error');
  var pwFormSuccess  = document.getElementById('pw-form-success');
  var btnDownload    = document.getElementById('btn-download-data');

  [currentPwInput, newPwInput, confirmPwInput].forEach(function (el) {
    if (el) el.addEventListener('input', clearPwMessages);
  });

  if (btnUpdatePw) btnUpdatePw.addEventListener('click', handlePasswordChange);

  async function loadProfile() {
    var result = await Api.get('/profile/');
    if (!result.data.success) return;

    var mobileEl = document.getElementById('registered-mobile');
    if (mobileEl) {
      var mobile = result.data.user.mobile;
      mobileEl.textContent = mobile ? mobile.replace(/(\d{2})\d+(\d{3})$/, '$1***$2') : 'Not provided';
    }

    populateLoginLog(result.data.login_log || []);
  }

  function populateLoginLog(log) {
    var tbody = document.getElementById('login-log-tbody');
    if (!tbody) return;

    if (log.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-faint); padding:24px 6px;">No login activity recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    log.forEach(function (entry) {
      var dt = new Date(entry.at);
      var dtText = isNaN(dt) ? entry.at : dt.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      var tr = document.createElement('tr');
      var resultClass = entry.result === 'Success' ? 'tag-success' : 'tag-danger';
      tr.innerHTML =
        '<td>' + dtText + '</td>' +
        '<td>' + (entry.device || '--') + '</td>' +
        '<td><span class="tag ' + resultClass + '">' + entry.result + '</span></td>';
      tbody.appendChild(tr);
    });
  }

  async function handlePasswordChange() {
    clearPwMessages();

    var current = currentPwInput ? currentPwInput.value : '';
    var newPw   = newPwInput ? newPwInput.value : '';
    var confirm = confirmPwInput ? confirmPwInput.value : '';

    if (!current) {
      showPwError('Please enter your current password.');
      if (currentPwInput) currentPwInput.focus();
      return;
    }
    if (!newPw || newPw.length < 8) {
      showPwError('New password must be at least 8 characters.');
      if (newPwInput) newPwInput.focus();
      return;
    }
    if (newPw !== confirm) {
      showPwError('New passwords do not match.');
      if (confirmPwInput) confirmPwInput.focus();
      return;
    }
    if (current === newPw) {
      showPwError('New password must be different from your current password.');
      return;
    }

    setPasswordLoading(true);

    var result = await Api.postJSON('/profile/change-password', {
      current_password: current,
      new_password:     newPw,
      confirm_password: confirm
    });

    setPasswordLoading(false);

    if (result.data.success) {
      showPwSuccess('Password updated successfully.');
      if (currentPwInput) currentPwInput.value = '';
      if (newPwInput)     newPwInput.value = '';
      if (confirmPwInput) confirmPwInput.value = '';
    } else {
      showPwError(result.data.message || 'Password change failed. Please try again.');
    }
  }

  // ── Download my data ─────────────────────────────────────────
  if (btnDownload) {
    btnDownload.addEventListener('click', async function () {
      var original = btnDownload.textContent;
      btnDownload.disabled = true;
      btnDownload.textContent = 'Preparing...';

      var result = await Api.get('/profile/export');

      btnDownload.disabled = false;
      btnDownload.textContent = original;

      if (!result.data.success) {
        alert(result.data.message || 'Could not prepare your data export. Please try again.');
        return;
      }

      var blob = new Blob([JSON.stringify(result.data.data, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'smartelec-my-data.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  // ── Helpers ─────────────────────────────────────────────────
  function showPwError(msg) {
    if (pwFormError) { pwFormError.textContent = msg; pwFormError.style.display = 'block'; }
    if (pwFormSuccess) pwFormSuccess.style.display = 'none';
  }
  function showPwSuccess(msg) {
    if (pwFormSuccess) { pwFormSuccess.textContent = msg; pwFormSuccess.style.display = 'block'; }
    if (pwFormError) pwFormError.style.display = 'none';
  }
  function clearPwMessages() {
    if (pwFormError) pwFormError.style.display = 'none';
    if (pwFormSuccess) pwFormSuccess.style.display = 'none';
  }
  function setPasswordLoading(state) {
    if (!btnUpdatePw) return;
    btnUpdatePw.disabled = state;
    btnUpdatePw.style.opacity = state ? '0.7' : '1';
    btnUpdatePw.textContent = state ? 'Updating...' : 'Update password';
  }

})();
