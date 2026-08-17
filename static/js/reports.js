// ============================================================
//  reports.js
//  Powers 10_reports.html.
//  - Year selector + summary line + monthly table, from
//    GET /reports/?year=YYYY (routes/report_routes.py)
//  - "Download report" either triggers print (PDF) or builds a
//    CSV file client-side (Blob download) from whatever data is
//    currently loaded — no server-side export endpoint needed.
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  populateYearOptions();
  loadReport();

  var yearSelect   = document.getElementById('report-year');
  var formatSelect = document.getElementById('report-format');
  var btnExport    = document.getElementById('btn-export');

  var currentBills = [];   // kept for CSV export without re-fetching

  function populateYearOptions() {
    var select = document.getElementById('report-year');
    if (!select) return;
    var currentYear = new Date().getFullYear();
    for (var y = currentYear; y >= currentYear - 3; y--) {
      var opt = document.createElement('option');
      opt.value = String(y);
      opt.textContent = String(y);
      select.appendChild(opt);
    }
  }

  if (yearSelect) yearSelect.addEventListener('change', loadReport);

  async function loadReport() {
    var year = yearSelect ? yearSelect.value : '';
    var url = year ? '/reports/?year=' + encodeURIComponent(year) : '/reports/';

    var result = await Api.get(url);

    if (!result.data.success) {
      showTableEmpty(result.data.message || 'Could not load reports.');
      return;
    }

    currentBills = result.data.bills || [];
    populateSummary(result.data.summary || {});
    populateTable(currentBills);
  }

  function populateSummary(s) {
    var line = document.getElementById('summary-line');
    if (!line) return;

    if (!s.bills_confirmed) {
      line.textContent = 'No confirmed bills for this period.';
      return;
    }

    var parts = [
      s.bills_confirmed + ' bill' + (s.bills_confirmed === 1 ? '' : 's') + ' confirmed',
      'total ' + s.total_kwh + ' kWh',
      s.total_lkr !== null && s.total_lkr !== undefined ? 'total LKR ' + formatLKR(s.total_lkr) : null,
      s.monthly_avg_kwh !== null ? 'average ' + s.monthly_avg_kwh + ' kWh/month' : null,
      s.peak_month ? 'peak month: ' + s.peak_month : null
    ].filter(Boolean);

    line.textContent = parts.join(' · ');
  }

  function populateTable(bills) {
    var tbody = document.getElementById('summary-tbody');
    if (!tbody) return;

    if (bills.length === 0) {
      showTableEmpty('No confirmed bills for this period.');
      return;
    }

    tbody.innerHTML = '';
    bills.forEach(function (b) {
      var pct = b.vs_avg_pct;
      var pctText = (pct !== null && pct !== undefined) ? (pct >= 0 ? '+' : '') + pct + '%' : 'n/a';
      var tagClass = pct > 5 ? 'tag-warning' : (pct < -5 ? 'tag-success' : 'tag-info');

      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (b.billing_period || '--') + '</td>' +
        '<td>' + b.units_consumed + ' kWh</td>' +
        '<td>' + (b.bill_amount_lkr !== null && b.bill_amount_lkr !== undefined ? 'LKR ' + formatLKR(b.bill_amount_lkr) : '--') + '</td>' +
        '<td><span class="tag ' + tagClass + '">' + pctText + '</span></td>';
      tbody.appendChild(tr);
    });
  }

  function showTableEmpty(msg) {
    var line = document.getElementById('summary-line');
    if (line) line.textContent = msg;
    var tbody = document.getElementById('summary-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-faint); padding:24px 6px;">' + msg + '</td></tr>';
  }

  // ── Export ───────────────────────────────────────────────────
  if (btnExport) {
    btnExport.addEventListener('click', function () {
      if (currentBills.length === 0) {
        alert('No confirmed bills in the selected period yet.');
        return;
      }
      if (formatSelect && formatSelect.value === 'csv') {
        exportCsv(currentBills);
      } else {
        window.print();
      }
    });
  }

  function exportCsv(bills) {
    var rows = [['Billing period', 'Units consumed (kWh)', 'Bill amount (LKR)', 'vs. average (%)']];
    bills.forEach(function (b) {
      rows.push([b.billing_period || '', b.units_consumed, b.bill_amount_lkr != null ? b.bill_amount_lkr : '', b.vs_avg_pct != null ? b.vs_avg_pct : '']);
    });
    var csv = rows.map(function (r) { return r.map(escapeCsv).join(','); }).join('\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'smartelec-usage-report.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function escapeCsv(value) {
    var str = String(value);
    return /[",\n]/.test(str) ? '"' + str.replace(/"/g, '""') + '"' : str;
  }

  function formatLKR(amount) {
    return Number(amount).toLocaleString('en-LK', { maximumFractionDigits: 2 });
  }

})();
