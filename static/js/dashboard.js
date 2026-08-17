// ============================================================
//  dashboard.js
//  Powers 07_dashboard.html.
//  Step 4 of the flow: shows the analysed data from confirmed
//  bills — stats, chart, recent uploads, prediction/recommendation
//  previews. Calls GET /dashboard/ (routes/dashboard_routes.py).
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  loadDashboard();

  async function loadDashboard() {
    var result = await Api.get('/dashboard/');
    if (!result.data.success) {
      showPageError(result.data.message || 'Could not load dashboard.');
      return;
    }

    populateStats(result.data);
    renderChart(result.data);
    populateRecentBills(result.data.recent_bills || []);
    populateTopRecommendation(result.data);
  }

  // ── Stat cards ──────────────────────────────────────────────
  function populateStats(data) {
    var bill = data.current_bill;

    if (!bill) {
      setText('stat-kwh', '-- kWh');
      setText('stat-kwh-sub', 'upload your first bill to get started');
      setText('stat-lkr', 'LKR --');
      setText('stat-predict', '-- kWh');
      setText('stat-predict-sub', 'upload a bill to unlock this');
      setText('pred-snapshot-kwh', '-- kWh');
      setText('pred-snapshot-sub', 'upload a bill to unlock this');
      setText('stat-avg', '-- kWh');
      setText('stat-avg-sub', 'not enough history yet');
      return;
    }

    setText('stat-kwh', bill.units_consumed + ' kWh');
    setText('stat-kwh-sub', 'for ' + (bill.billing_period || 'the latest period'));
    setText('stat-lkr', bill.bill_amount_lkr !== null ? 'LKR ' + formatLKR(bill.bill_amount_lkr) : 'LKR --');

    var hasPrediction = bill.predicted_next_kwh !== null && bill.predicted_next_kwh !== undefined;
    setText('stat-predict', hasPrediction ? bill.predicted_next_kwh + ' kWh' : '-- kWh');
    setText('stat-predict-sub', hasPrediction ? '±10-20% accuracy' : 'upload one more bill to unlock this');
    setText('pred-snapshot-kwh', hasPrediction ? bill.predicted_next_kwh + ' kWh' : '-- kWh');
    setText('pred-snapshot-sub', hasPrediction ? 'estimated for next billing period' : 'upload one more bill to unlock this');

    var hasAvg = data.personal_avg_kwh !== null && data.personal_avg_kwh !== undefined;
    setText('stat-avg', hasAvg ? data.personal_avg_kwh + ' kWh' : '-- kWh');
    if (hasAvg && data.vs_avg_percent !== null && data.vs_avg_percent !== undefined) {
      setText('stat-avg-sub', (data.vs_avg_percent >= 0 ? '+' : '') + data.vs_avg_percent + '% vs your average');
    } else {
      setText('stat-avg-sub', 'not enough history yet');
    }
  }

  // ── Chart ────────────────────────────────────────────────────
  function renderChart(data) {
    var canvas = document.getElementById('usageChart');
    var descEl = document.getElementById('chart-desc');
    if (!canvas) return;

    var chartData = data.chart_data || [];
    if (chartData.length === 0) {
      if (descEl) descEl.textContent = 'Your usage chart will appear here once bills have been uploaded.';
      return;
    }

    if (descEl) {
      descEl.textContent = chartData.length < 3
        ? 'The average line becomes meaningful once you have a few more months confirmed.'
        : 'Latest figure was extracted from your most recent bill upload.';
    }

    var labels = chartData.map(function (d) { return (d.period || '--').slice(0, 12); });
    var values = chartData.map(function (d) { return d.kwh; });
    var avg = data.personal_avg_kwh;

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          { label: 'Monthly usage (kWh)', data: values, backgroundColor: '#164c78', borderRadius: 3 },
          { type: 'line', label: 'Your average', data: values.map(function () { return avg; }), borderColor: '#b8860f', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { y: { beginAtZero: true, ticks: { font: { size: 11 } } }, x: { ticks: { font: { size: 11 } } } }
      }
    });
  }

  // ── Recent bills table ───────────────────────────────────────
  function populateRecentBills(bills) {
    var tbody = document.getElementById('recent-bills-tbody');
    if (!tbody) return;

    if (bills.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-faint); padding:24px 6px;">No bills yet. <a href="/05_upload_bill.html">Upload your first bill</a>.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    bills.forEach(function (b) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + (b.billing_period || '--') + '</td>' +
        '<td>' + (b.source === 'sms' ? 'SMS screenshot' : 'Bill photo') + '</td>' +
        '<td>' + b.units_consumed + ' kWh</td>' +
        '<td><span class="tag tag-success">Confirmed</span></td>';
      tbody.appendChild(tr);
    });
  }

  // ── Top recommendation preview ───────────────────────────────
  async function populateTopRecommendation(data) {
    var card = document.getElementById('top-rec-card');
    if (!card) return;

    var bill = data.current_bill;
    if (!bill) {
      card.innerHTML = '<div class="rec-title">--</div><div class="rec-body">Recommendations will appear here once enough usage data has been collected.</div>';
      return;
    }

    var appliancesResult = await Api.get('/appliances/');
    var owned = (appliancesResult.data.success ? appliancesResult.data.appliances : [])
      .filter(function (a) { return a.owned; })
      .map(function (a) { return a.name; });

    var recs = Api.buildRecommendations(owned, bill.high_usage_alert);

    if (recs.length === 0) {
      card.innerHTML = '<div class="rec-title">--</div><div class="rec-body">Your usage is within your normal range — no specific recommendations right now.</div>';
      return;
    }

    var top = recs[0];
    card.innerHTML = '<div class="rec-title">' + top.title + '</div><div class="rec-body">' + top.body + ' Potential saving: ~' + top.savingKwh + ' kWh/month.</div>';
  }

  // ── Helpers ─────────────────────────────────────────────────
  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  function formatLKR(amount) {
    return Number(amount).toLocaleString('en-LK', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }
  function showPageError(msg) {
    console.error('[Dashboard]', msg);
    var banner = document.createElement('div');
    banner.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#fbe9e7;border:1px solid #f0b8ab;color:#b3382c;padding:12px 22px;border-radius:10px;font-size:13px;z-index:9999;';
    banner.textContent = msg;
    document.body.appendChild(banner);
    setTimeout(function () { banner.remove(); }, 4000);
  }

})();
