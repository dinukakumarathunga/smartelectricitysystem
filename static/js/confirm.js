// ============================================================
//  confirm.js
//  Handles OCR result review on 06_upload_confirm.html.
//  Step 4 of the flow: confirm the extracted values → saved via
//  POST /bill/confirm → becomes what dashboard/prediction/
//  recommendations read from.
//
//  Loads the pending extraction via GET /bill/pending — the data
//  now lives server-side (see routes/bill_routes.py's
//  session['pending_ocr']), not in sessionStorage.
// ============================================================

(function () {
  'use strict';

  var kwhInput    = document.getElementById('kwh-value');
  var lkrInput    = document.getElementById('lkr-value');
  var periodInput = document.getElementById('billing-period');
  var sourceEl    = document.getElementById('source-label');
  var confTagEl   = document.getElementById('confidence-tag');
  var noteText    = document.getElementById('accuracy-note-text');
  var thumbLabel  = document.getElementById('thumb-filename');
  var acctDisplay = document.getElementById('account-number-display');
  var btnConfirm  = document.getElementById('btn-confirm');
  var btnReupload = document.getElementById('btn-reupload');
  var errorMsg    = document.getElementById('confirm-error');

  var pendingSource = 'photo';   // remembered from the loaded OCR result, sent back on confirm

  init();

  async function init() {
    var masked = await Api.fillAccountChip();
    if (acctDisplay) acctDisplay.textContent = masked || '--';

    var result = await Api.get('/bill/pending');

    if (!result.data.success) {
      // Nothing pending (e.g. stale reload, or already confirmed) —
      // send the user back to start a fresh upload.
      window.location.href = '/05_upload_bill.html';
      return;
    }

    populateFields(result.data);
  }

  function populateFields(data) {
    var extracted = data.extracted || {};
    pendingSource = data.source || 'photo';

    if (kwhInput) kwhInput.value = extracted.units_consumed !== null && extracted.units_consumed !== undefined ? extracted.units_consumed : '';
    if (lkrInput) lkrInput.value = extracted.bill_amount_lkr !== null && extracted.bill_amount_lkr !== undefined ? extracted.bill_amount_lkr : '';
    if (periodInput) periodInput.value = extracted.billing_period || '';
    if (sourceEl) sourceEl.textContent = pendingSource === 'sms' ? 'SMS screenshot' : 'Bill photo';
    if (thumbLabel) thumbLabel.textContent = data.filename || 'Uploaded image';

    var conf = data.ocr_confidence || 'Low';
    if (confTagEl) confTagEl.textContent = conf;
    if (noteText) {
      noteText.textContent = conf === 'Low'
        ? ' — automatic reading was unreliable for this image. Please fill in or double-check every field below.'
        : ' — please still double-check the figures before confirming.';
    }
  }

  function validateFields() {
    var kwh = parseFloat(kwhInput.value);
    // 0 is a legitimate value (e.g. a net-metering month that fully
    // offset consumption) — check for missing/invalid, not falsy.
    if (kwhInput.value === '' || isNaN(kwh) || kwh < 0) {
      showError('Units consumed (kWh) is required and must be zero or a positive number.');
      kwhInput.focus();
      return false;
    }
    if (kwh > 9999) {
      showError('Units consumed value seems too high. Please check and correct it.');
      return false;
    }
    if (lkrInput.value !== '') {
      var lkr = parseFloat(lkrInput.value);
      if (isNaN(lkr) || lkr < 0) {
        showError('Bill amount must be zero or a positive number.');
        lkrInput.focus();
        return false;
      }
    }
    if (!periodInput.value.trim()) {
      showError('Billing period is required.');
      periodInput.focus();
      return false;
    }
    return true;
  }

  if (btnConfirm) {
    btnConfirm.addEventListener('click', async function () {
      clearError();
      if (!validateFields()) return;

      setLoading(true);

      var result = await Api.postJSON('/bill/confirm', {
        units_consumed:  parseFloat(kwhInput.value),
        bill_amount_lkr: lkrInput.value !== '' ? parseFloat(lkrInput.value) : null,
        billing_period:  periodInput.value.trim(),
        source:          pendingSource
      });

      if (!result.data.success) {
        setLoading(false);
        showError(result.data.message || 'Could not save bill. Please try again.');
        return;
      }

      btnConfirm.textContent = 'Saved!';
      setTimeout(function () {
        window.location.href = result.data.redirect || '/07_dashboard.html';
      }, 500);
    });
  }

  // Re-upload just navigates back — the backend still has the old
  // pending_ocr in session until the NEXT successful upload
  // overwrites it, which is harmless (nothing reads stale data
  // without the user re-uploading first).
  if (btnReupload) {
    btnReupload.addEventListener('click', function () {
      window.location.href = '/05_upload_bill.html';
    });
  }

  // ── Helpers ─────────────────────────────────────────────────
  function showError(msg) { if (errorMsg) { errorMsg.textContent = msg; errorMsg.style.display = 'block'; } }
  function clearError()   { if (errorMsg) { errorMsg.textContent = '';  errorMsg.style.display = 'none';  } }
  function setLoading(state) {
    if (!btnConfirm) return;
    btnConfirm.disabled = state;
    btnConfirm.style.opacity = state ? '0.7' : '1';
    if (state) btnConfirm.textContent = 'Saving...';
  }

})();
