// ============================================================
//  prediction.js
//  Powers 08_ai_prediction.html.
//  Step 5 of the flow: full AI prediction, driven by
//  GET /predict/ (routes/predict_routes.py — the linear
//  regression in utils/ml_utils.py, plus accuracy tracking).
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  loadPrediction();

  async function loadPrediction() {
    var result = await Api.get('/predict/');

    if (!result.data.success) {
      showEmptyState(result.data.message || 'No prediction data available.');
      return;
    }

    populateStats(result.data);
    renderTrendChart(result.data.trend_data);
  }

  function populateStats(data) {
    setText('pred-kwh-value', data.predicted_kwh + ' kWh');
    setText('pred-lkr-value', data.predicted_lkr !== null && data.predicted_lkr !== undefined ? 'LKR ' + formatLKR(data.predicted_lkr) : 'LKR --');
    setText('pred-confidence-value', data.confidence_pct + '%');
    setText('pred-confidence-sub', 'based on ' + data.months_of_data + ' month' + (data.months_of_data === 1 ? '' : 's') + ' of history');
    setText('stat-months', data.months_of_data + ' confirmed bills');
    setText('stat-peak', data.peak_month || '--');

    var banner = document.getElementById('prediction-banner');
    if (banner && data.high_usage_alert === 'Yes') {
      banner.textContent = 'Your latest bill is above your personal average — see the Recommendations page for ways to bring it down. Predictions carry roughly 10-20% uncertainty.';
    }
  }

  function renderTrendChart(trendData) {
    var canvas = document.getElementById('predChart');
    if (!canvas || !trendData || trendData.length === 0) return;

    var labels = trendData.map(function (d) { return (d.period || '--').slice(0, 12); });
    labels.push('Predicted');

    var actual = trendData.map(function (d) { return d.actual; });
    actual.push(null);

    var predictedSeries = trendData.map(function () { return null; });
    var lastEntry = trendData[trendData.length - 1];
    predictedSeries[predictedSeries.length - 1] = lastEntry.actual;
    predictedSeries.push(lastEntry.predicted);

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: 'Actual usage', data: actual, borderColor: '#164c78', backgroundColor: '#164c78', tension: .25 },
          { label: 'Predicted', data: predictedSeries, borderColor: '#b8860f', borderDash: [6, 4], tension: .25 }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { y: { beginAtZero: true, ticks: { font: { size: 11 } } }, x: { ticks: { font: { size: 11 } } } }
      }
    });
  }

  function showEmptyState(message) {
    var statsGrid = document.getElementById('prediction-stats');
    if (statsGrid) {
      statsGrid.innerHTML =
        '<div style="grid-column:1/-1; text-align:center; padding:36px 20px; color:var(--text-muted); font-size:.85rem; line-height:1.7;">' +
        message + '<br><a href="/05_upload_bill.html" style="font-weight:600;">Upload a bill &rarr;</a></div>';
    }
  }

  // ── Helpers ─────────────────────────────────────────────────
  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }
  function formatLKR(amount) {
    return Number(amount).toLocaleString('en-LK', { maximumFractionDigits: 0 });
  }

})();
