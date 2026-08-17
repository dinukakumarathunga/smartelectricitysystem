// ============================================================
//  upload.js
//  Handles bill/SMS image upload on 05_upload_bill.html.
//  Step 3 of the flow: upload → (server-side OCR) → confirm → dashboard.
//
//  OCR now runs server-side (utils/ocr_utils.py via pytesseract),
//  not in the browser — the old Tesseract.js CDN script and all
//  client-side extraction logic are gone. This file's job is just
//  file selection/validation and posting to POST /bill/upload.
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  renderRecentUploads();

  var dropZone         = document.getElementById('drop-zone');
  var fileInput        = document.getElementById('billFile');
  var btnBrowse         = document.getElementById('btn-browse');
  var btnScan           = document.getElementById('btn-scan');
  var uploadTitle       = document.getElementById('uploadTitle');
  var uploadHint        = document.getElementById('uploadHint');
  var errorMsg          = document.getElementById('upload-error');
  var sourceBill        = document.getElementById('sourceBill');
  var sourceSms         = document.getElementById('sourceSms');
  var sourceBillLabel   = document.getElementById('sourceBillLabel');
  var sourceSmsLabel    = document.getElementById('sourceSmsLabel');

  var selectedFile = null;

  // ── Source toggle ────────────────────────────────────────────
  [sourceBill, sourceSms].forEach(function (radio) {
    if (!radio) return;
    radio.addEventListener('change', function () {
      sourceBillLabel.classList.toggle('on', sourceBill.checked);
      sourceSmsLabel.classList.toggle('on', sourceSms.checked);
    });
  });

  // ── Browse / drop zone ───────────────────────────────────────
  if (btnBrowse) btnBrowse.addEventListener('click', function () { fileInput.click(); });
  if (dropZone) {
    dropZone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--accent, #164c78)';
    });
    dropZone.addEventListener('dragleave', function () { dropZone.style.borderColor = ''; });
    dropZone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropZone.style.borderColor = '';
      if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });
  }
  if (fileInput) {
    fileInput.addEventListener('change', function () {
      if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });
  }

  function handleFile(file) {
    clearError();
    var allowed = ['image/jpeg', 'image/png', 'application/pdf'];
    if (allowed.indexOf(file.type) === -1) {
      showError('Unsupported file type. Please upload a JPEG, PNG, or PDF file.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showError('File is too large. Maximum allowed size is 10 MB.');
      return;
    }
    selectedFile = file;
    uploadTitle.textContent = file.name;
    uploadHint.textContent  = 'File selected - ready to upload and analyse';
  }

  // ── Upload and analyse ───────────────────────────────────────
  if (btnScan) btnScan.addEventListener('click', handleScan);

  async function handleScan() {
    clearError();

    if (!selectedFile) {
      showError('Please select a bill image or SMS screenshot first.');
      return;
    }
    if (!sourceBill.checked && !sourceSms.checked) {
      showError('Please choose whether this is a bill photo or an SMS screenshot.');
      return;
    }

    setLoading(true);

    var formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('source', sourceBill.checked ? 'photo' : 'sms');

    var result = await Api.postForm('/bill/upload', formData);

    setLoading(false);

    if (!result.data.success) {
      showError(result.data.message || 'Could not analyse this image. Please try a clearer photo.');
      return;
    }

    // The backend has already stored the extracted values in the
    // session (see routes/bill_routes.py) — the confirm page loads
    // them itself via GET /bill/pending, so we just navigate there.
    window.location.href = '/06_upload_confirm.html';
  }

  // ── Recent uploads table ─────────────────────────────────────
  async function renderRecentUploads() {
    var tbody = document.getElementById('recent-uploads-tbody');
    if (!tbody) return;

    var result = await Api.get('/bill/');
    var bills = (result.data.success && result.data.bills) ? result.data.bills : [];

    if (bills.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-faint); padding:24px 6px;">No bills uploaded yet. Once you upload a bill or SMS screenshot, it will appear here.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    bills.forEach(function (b) {
      var tr = document.createElement('tr');
      var dateCell = document.createElement('td');
      dateCell.textContent = b.billing_period || '--';
      var sourceCell = document.createElement('td');
      sourceCell.textContent = b.source === 'sms' ? 'SMS screenshot' : 'Bill photo';
      var resultCell = document.createElement('td');
      resultCell.textContent = b.units_consumed + ' kWh';
      var statusCell = document.createElement('td');
      statusCell.innerHTML = '<span class="tag tag-success">Confirmed</span>';
      tr.appendChild(dateCell); tr.appendChild(sourceCell); tr.appendChild(resultCell); tr.appendChild(statusCell);
      tbody.appendChild(tr);
    });
  }

  // ── Helpers ─────────────────────────────────────────────────
  function showError(msg) { if (errorMsg) { errorMsg.textContent = msg; errorMsg.style.display = 'block'; } }
  function clearError()   { if (errorMsg) { errorMsg.textContent = '';  errorMsg.style.display = 'none';  } }
  function setLoading(state) {
    if (!btnScan) return;
    btnScan.disabled      = state;
    btnScan.style.opacity = state ? '0.7' : '1';
    btnScan.textContent   = state ? 'Analysing...' : 'Upload and analyse';
  }

})();
