// ============================================================
//  appliance_onboard.js
//  Handles first-login appliance setup on 04_appliance_onboarding.html.
//  Step 2 of the flow: appliance profile → upload first bill.
//  Calls POST /appliances/save (routes/appliance_routes.py), which
//  also flips user.first_login_done to True server-side — that's
//  what stops future logins from being routed back here.
// ============================================================

(function () {
  'use strict';

  var tiles       = document.querySelectorAll('#appliance-grid .appliance-tile');
  var sizeSelect  = document.getElementById('household-size');
  var btnContinue = document.getElementById('btn-continue');
  var btnSkip     = document.getElementById('btn-skip');
  var formError   = document.getElementById('form-error');

  tiles.forEach(function (tile) {
    var checkbox = tile.querySelector('input[type="checkbox"]');
    tile.addEventListener('click', function (e) {
      e.preventDefault();
      checkbox.checked = !checkbox.checked;
      tile.classList.toggle('on', checkbox.checked);
    });
  });

  function buildPayload() {
    return Array.from(tiles).map(function (tile) {
      return {
        name:  tile.dataset.appliance,
        owned: tile.querySelector('input[type="checkbox"]').checked
      };
    });
  }

  async function handleSave(allowEmpty) {
    var appliances = buildPayload();
    var owned = appliances.filter(function (a) { return a.owned; });

    if (!allowEmpty && owned.length === 0) {
      showFormError('Please select at least one appliance you own, or use "Skip for now".');
      return;
    }

    setLoading(true);

    var result = await Api.postJSON('/appliances/save', {
      appliances: appliances,
      household_size: sizeSelect ? (sizeSelect.value || null) : null
    });

    if (!result.data.success) {
      setLoading(false);
      showFormError(result.data.message || 'Could not save your appliance profile. Please try again.');
      return;
    }

    window.location.href = '/05_upload_bill.html';
  }

  if (btnContinue) btnContinue.addEventListener('click', function () { handleSave(false); });
  if (btnSkip) btnSkip.addEventListener('click', function (e) {
    e.preventDefault();
    handleSave(true);
  });

  function showFormError(message) {
    if (formError) { formError.textContent = message; formError.style.display = 'block'; }
  }
  function setLoading(state) {
    if (btnContinue) { btnContinue.disabled = state; btnContinue.textContent = state ? 'Saving...' : 'Save and continue'; }
    if (btnSkip) { btnSkip.style.pointerEvents = state ? 'none' : 'auto'; btnSkip.style.opacity = state ? '0.5' : '1'; }
  }

})();
