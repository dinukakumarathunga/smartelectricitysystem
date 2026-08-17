// ============================================================
//  appliance_profile.js
//  Powers 11_appliance_profile.html — same appliance grid as
//  onboarding, but for editing later from the Account section.
//  Loads existing selections via GET /appliances/ and saves back
//  via POST /appliances/save — the exact same endpoints
//  appliance_onboard.js uses, since the backend doesn't need a
//  separate "editing" vs "first time" distinction.
// ============================================================

(function () {
  'use strict';

  Api.fillAccountChip();

  var tiles        = document.querySelectorAll('#appliance-grid .appliance-tile');
  var sizeSelect    = document.getElementById('household-size');
  var btnSave       = document.getElementById('btn-save');
  var savedNote     = document.getElementById('save-confirm');
  var updatedDesc   = document.getElementById('last-updated-desc');

  loadExisting();

  async function loadExisting() {
    var result = await Api.get('/appliances/');

    if (!result.data.success) {
      if (updatedDesc) updatedDesc.textContent = 'Could not load your saved appliances. Try refreshing the page.';
      return;
    }

    var appliances = result.data.appliances || [];
    tiles.forEach(function (tile) {
      var match = appliances.find(function (a) { return a.name === tile.dataset.appliance; });
      var checkbox = tile.querySelector('input[type="checkbox"]');
      var owned = !!(match && match.owned);
      checkbox.checked = owned;
      tile.classList.toggle('on', owned);
    });

    if (sizeSelect && result.data.household_size) {
      sizeSelect.value = result.data.household_size;
    }

    if (updatedDesc) {
      updatedDesc.textContent = 'Keep this up to date so your recommendations stay relevant.';
    }
  }

  tiles.forEach(function (tile) {
    var checkbox = tile.querySelector('input[type="checkbox"]');
    tile.addEventListener('click', function (e) {
      e.preventDefault();
      checkbox.checked = !checkbox.checked;
      tile.classList.toggle('on', checkbox.checked);
    });
  });

  if (btnSave) {
    btnSave.addEventListener('click', async function () {
      var appliances = Array.from(tiles).map(function (tile) {
        return { name: tile.dataset.appliance, owned: tile.querySelector('input[type="checkbox"]').checked };
      });

      setLoading(true);

      var result = await Api.postJSON('/appliances/save', {
        appliances: appliances,
        household_size: sizeSelect ? (sizeSelect.value || null) : null
      });

      setLoading(false);

      if (!result.data.success) {
        if (updatedDesc) updatedDesc.textContent = result.data.message || 'Could not save. Please try again.';
        return;
      }

      if (savedNote) {
        savedNote.style.display = 'block';
        setTimeout(function () { savedNote.style.display = 'none'; }, 2500);
      }
    });
  }

  function setLoading(state) {
    if (!btnSave) return;
    btnSave.disabled = state;
    btnSave.textContent = state ? 'Saving...' : 'Save changes';
  }

})();
