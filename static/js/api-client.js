// ============================================================
//  api-client.js
//  Thin fetch() wrapper for the real Flask backend (routes/*.py).
//  Replaces app-data.js, which was a localStorage-only stand-in
//  used before the backend existed — that file is no longer
//  loaded by any page.
//
//  Every non-GET request includes the CSRF token Flask-WTF
//  requires, read from the <meta name="csrf-token"> tag that
//  page_routes.py's templates already inject into every page's
//  <head>.
// ============================================================

(function (global) {
  'use strict';

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  /**
   * Always resolves — never throws on HTTP error status or on a
   * non-JSON response, so callers can handle failure the same way
   * they handle a validation error: check result.data.success.
   *
   * Returns { ok, status, data }.
   */
  async function apiFetch(url, options) {
    options = options || {};
    var headers = Object.assign({}, options.headers || {});
    var method = (options.method || 'GET').toUpperCase();

    if (method !== 'GET') {
      headers['X-CSRFToken'] = csrfToken();
    }
    // FormData sets its own multipart Content-Type (with boundary) —
    // never override it manually.
    if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    var response;
    try {
      response = await fetch(url, Object.assign({}, options, {
        headers: headers,
        credentials: 'same-origin',
      }));
    } catch (networkError) {
      return { ok: false, status: 0, data: { success: false, message: 'Network error. Please check your connection.' } };
    }

    var data;
    try {
      data = await response.json();
    } catch (parseError) {
      data = { success: false, message: 'Unexpected response from the server.' };
    }

    return { ok: response.ok, status: response.status, data: data };
  }

  function apiGet(url) {
    return apiFetch(url, { method: 'GET' });
  }

  function apiPostJSON(url, payload) {
    return apiFetch(url, { method: 'POST', body: JSON.stringify(payload) });
  }

  function apiPostForm(url, formData) {
    return apiFetch(url, { method: 'POST', body: formData });
  }

  function maskAccount(accountNumber) {
    if (!accountNumber) return '--';
    var digits = accountNumber.replace(/[^0-9]/g, '');
    if (digits.length < 4) return accountNumber;
    return digits.slice(0, 4) + '***' + digits.slice(-3);
  }

  /**
   * Fills any <span id="acct-chip"> on the page from GET /profile/
   * and returns the masked string, so callers that need the value
   * in more than one place (e.g. 06_upload_confirm.html's account
   * number row) don't have to fetch /profile/ a second time.
   * Returns null if the user info couldn't be loaded.
   */
  async function fillAccountChip() {
    var chip = document.getElementById('acct-chip');
    var result = await Api.get('/profile/');
    if (!result.data.success || !result.data.user) return null;
    var masked = maskAccount(result.data.user.account_number);
    if (chip) chip.textContent = masked;
    return masked;
  }

  // ── shared recommendation rules ─────────────────────────────
  // There's no dedicated /recommendations/ backend route — this
  // is deliberately simple, static rule data, so it's built here
  // from data GET /dashboard/ and GET /appliances/ already
  // provide (high_usage_alert, vs_avg_percent, owned appliances)
  // rather than adding a backend route that would just return
  // this same static table.
  var RECOMMENDATION_RULES = [
    {
      applianceMatch: 'Air conditioner',
      title: 'Reduce air conditioner runtime during peak hours',
      body: 'Your usage spikes typically line up with air conditioner use. Reducing runtime by around 1 hour a day, or raising the set temperature by 1°C, can meaningfully lower monthly usage.',
      savingKwh: '10-15'
    },
    {
      applianceMatch: 'Water heater',
      title: 'Check your water heater thermostat setting',
      body: 'Water heaters left on a high thermostat setting draw standby power continuously. Lowering the setting by a few degrees reduces this with little effect on comfort.',
      savingKwh: '5-8'
    },
    {
      applianceMatch: 'Television',
      title: 'Unplug devices left on standby',
      body: 'Televisions and other electronics left plugged in on standby continue to draw a small amount of power throughout the day, which adds up over a month.',
      savingKwh: '2-4'
    },
    {
      applianceMatch: 'Washing machine',
      title: 'Run the washing machine on full loads only',
      body: 'Partial loads use nearly as much energy as full ones. Batching laundry into full loads reduces the number of cycles you run each month.',
      savingKwh: '3-6'
    },
    {
      applianceMatch: 'Electric water pump',
      title: 'Check the water pump for continuous running',
      body: 'A pump that runs longer than expected can indicate a float switch or plumbing issue, and adds up quickly on the bill.',
      savingKwh: '4-9'
    }
  ];

  function buildRecommendations(ownedApplianceNames, highUsageAlert) {
    if (highUsageAlert !== 'Yes') return [];
    return RECOMMENDATION_RULES.filter(function (r) {
      return ownedApplianceNames.indexOf(r.applianceMatch) !== -1;
    });
  }

  global.Api = {
    get: apiGet, postJSON: apiPostJSON, postForm: apiPostForm,
    maskAccount: maskAccount, fillAccountChip: fillAccountChip,
    buildRecommendations: buildRecommendations,
  };

})(window);
