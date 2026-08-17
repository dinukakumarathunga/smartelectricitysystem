// ============================================================
//  recommendations.js
//  Powers 09_recommendations.html.
//  Step 5 (continued): there's no dedicated /recommendations/
//  backend route (see api-client.js's buildRecommendations note)
//  — this composes GET /dashboard/ (for high_usage_alert and
//  vs_avg_percent) with GET /appliances/ (for owned appliances),
//  then applies the shared rule table client-side.
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();
  loadRecommendations();

  async function loadRecommendations() {
    var dashboardResult = await Api.get('/dashboard/');

    if (!dashboardResult.data.success || !dashboardResult.data.current_bill) {
      showEmptyState('Upload at least one bill to generate recommendations.');
      return;
    }

    var bill = dashboardResult.data.current_bill;
    var vsAvgPercent = dashboardResult.data.vs_avg_percent;

    var appliancesResult = await Api.get('/appliances/');
    var appliances = appliancesResult.data.success ? appliancesResult.data.appliances : [];
    var ownedNames = appliances.filter(function (a) { return a.owned; }).map(function (a) { return a.name; });

    var recs = Api.buildRecommendations(ownedNames, bill.high_usage_alert);

    renderBanner(bill.high_usage_alert, vsAvgPercent);
    renderCards(recs, bill.high_usage_alert);
    renderSavings(recs, dashboardResult.data);
    renderApplianceChips(appliances);
  }

  function renderBanner(highUsageAlert, vsAvgPercent) {
    var banner = document.getElementById('banner-message');
    if (!banner) return;

    if (highUsageAlert === 'Yes') {
      var pctText = (vsAvgPercent !== null && vsAvgPercent !== undefined)
        ? (vsAvgPercent >= 0 ? '+' : '') + vsAvgPercent + '%'
        : 'above';
      banner.textContent = 'Your usage this month is ' + pctText + ' vs your average. Suggestions below are filtered to your appliance profile.';
    } else {
      banner.textContent = 'Your usage is within your normal range — no specific suggestions right now, but here is your appliance profile for reference.';
    }
  }

  function renderCards(recs, highUsageAlert) {
    var container = document.getElementById('recs-list');
    if (!container) return;

    if (recs.length === 0) {
      var reason = highUsageAlert === 'No'
        ? 'Your usage is within your normal range, so there are no specific suggestions right now.'
        : "No matching appliances found in your profile for this month's usage pattern — check your appliance profile is up to date.";
      container.innerHTML = '<div class="rec-card"><div class="rec-title">No recommendations right now</div><div class="rec-body">' + reason + '</div></div>';
      return;
    }

    container.innerHTML = '';
    recs.forEach(function (rec) {
      var card = document.createElement('div');
      card.className = 'rec-card';
      card.innerHTML =
        '<div class="rec-title">' + rec.title + '</div>' +
        '<div class="rec-body">' + rec.body + '</div>' +
        '<div class="rec-meta">Estimated saving: ' + rec.savingKwh + ' kWh / month &middot; based on: ' + rec.applianceMatch + ' in your appliance profile</div>';
      container.appendChild(card);
    });
  }

  function renderSavings(recs, dashboardData) {
    var kwhEl = document.getElementById('saving-total-kwh');
    var lkrEl = document.getElementById('saving-total-lkr');
    if (!kwhEl || !lkrEl) return;

    if (recs.length === 0) {
      kwhEl.textContent = '-- kWh';
      lkrEl.textContent = 'no active suggestions to total up right now';
      return;
    }

    var totalKwh = recs.reduce(function (sum, r) {
      var parts = r.savingKwh.split('-');
      var upper = parseFloat(parts[parts.length - 1]);
      return sum + (isNaN(upper) ? 0 : upper);
    }, 0);

    kwhEl.textContent = 'Up to ' + totalKwh + ' kWh';

    var bill = dashboardData.current_bill;
    if (bill && bill.bill_amount_lkr && bill.units_consumed) {
      var perKwh = bill.bill_amount_lkr / bill.units_consumed;
      var lkrSaving = Math.round(perKwh * totalKwh);
      lkrEl.textContent = 'estimated saving next month, around LKR ' + lkrSaving.toLocaleString('en-LK');
    } else {
      lkrEl.textContent = 'estimated saving next month (LKR figure needs a bill amount on file)';
    }
  }

  function renderApplianceChips(appliances) {
    var container = document.getElementById('appliance-chips');
    if (!container) return;
    var owned = appliances.filter(function (a) { return a.owned; });

    if (owned.length === 0) {
      container.innerHTML = '<span style="font-size:.8rem; color:var(--text-muted);">No appliances saved yet.</span>';
      return;
    }
    container.innerHTML = owned.map(function (a) { return '<span class="tag">' + a.name + '</span>'; }).join('');
  }

  function showEmptyState(msg) {
    var container = document.getElementById('recs-list');
    if (container) container.innerHTML = '<div class="rec-card"><div class="rec-title">--</div><div class="rec-body">' + msg + '</div></div>';
    var banner = document.getElementById('banner-message');
    if (banner) banner.textContent = msg;
  }

})();
