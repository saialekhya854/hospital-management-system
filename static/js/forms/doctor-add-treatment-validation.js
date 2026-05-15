/**
 * Doctor – Add Treatment Form Validation
 * File: static/js/forms/doctor-add-treatment-validation.js
 *
 * Exports:
 *   HMS.validateTreatmentForm()        – main treatment form
 *   HMS.validateNewTreatmentCatalogue() – new treatment catalogue modal
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  /* ── Main Treatment Form ────────────────────────────── */
  HMS.validateTreatmentForm = function () {
    // Patient must be selected (fPatientIdDisplay is readonly but will be set)
    const patientId   = document.getElementById('fPatientIdDisplay');
    const visitDate   = document.getElementById('fVisitDate');
    const treatment   = document.getElementById('fTreatmentSelect');
    const cost        = document.getElementById('fCost');
    const diagnosis   = document.getElementById('fDiagnosis');

    let valid = true;

    // Check patient selected (readonly field)
    if (patientId && !patientId.value.trim()) {
      HMS.toast.show('Please search and select a patient first.', 'warning');
      const searchBox = document.getElementById('manualPatientSearch');
      if (searchBox) searchBox.focus();
      return false;
    }

    // Visit date
    if (visitDate) {
      HMS.validate.injectErrorSpan(visitDate);
      if (!HMS.validate.validateField(visitDate, {
        required: true,
        date: true,
        messages: {
          required: 'Visit date is required.',
          date:     'Enter a valid visit date.',
        },
      })) valid = false;
    }

    // Treatment selection
    if (treatment) {
      HMS.validate.injectErrorSpan(treatment);
      if (!HMS.validate.validateField(treatment, {
        required: true,
        messages: { required: 'Please select a treatment.' },
      })) valid = false;
    }

    // Cost — required and must be >= 0
    if (cost) {
      HMS.validate.injectErrorSpan(cost);
      if (!HMS.validate.validateField(cost, {
        required: true,
        number: true,
        custom: (v) => parseFloat(v) >= 0 ? true : 'Cost must be 0 or more.',
        messages: {
          required: 'Treatment cost is required.',
          number:   'Enter a valid numeric cost.',
        },
      })) valid = false;
    }

    // Diagnosis notes — required
    if (diagnosis) {
      HMS.validate.injectErrorSpan(diagnosis);
      if (!HMS.validate.validateField(diagnosis, {
        required: true,
        minLen: 5,
        messages: {
          required: 'Diagnosis / notes are required.',
          minLen:   'Please provide at least 5 characters for the diagnosis.',
        },
      })) valid = false;
    }

    if (!valid) {
      HMS.toast.show('Please fill all required treatment fields.', 'danger');
    }
    return valid;
  };

  /* ── New Treatment Catalogue Modal ──────────────────── */
  HMS.validateNewTreatmentCatalogue = function () {
    const name     = document.getElementById('newTreatmentName');
    const category = document.getElementById('newTreatmentCategory');
    const cost     = document.getElementById('newTreatmentCost');

    let valid = true;

    if (name) {
      HMS.validate.injectErrorSpan(name);
      if (!HMS.validate.validateField(name, {
        required: true,
        minLen: 2,
        messages: {
          required: 'Treatment name is required.',
          minLen:   'At least 2 characters required.',
        },
      })) valid = false;
    }

    if (category) {
      HMS.validate.injectErrorSpan(category);
      if (!HMS.validate.validateField(category, {
        required: true,
        messages: { required: 'Category is required.' },
      })) valid = false;
    }

    if (cost) {
      HMS.validate.injectErrorSpan(cost);
      if (!HMS.validate.validateField(cost, {
        required: true,
        number: true,
        custom: (v) => parseFloat(v) >= 0 ? true : 'Cost must be 0 or more.',
        messages: {
          required: 'Cost is required.',
          number:   'Enter a valid numeric cost.',
        },
      })) valid = false;
    }

    if (!valid) {
      HMS.toast.show('Please fill all required fields for the new treatment.', 'warning');
    }
    return valid;
  };

  // Attach live validation to key fields
  document.addEventListener('DOMContentLoaded', function () {
    const livePairs = [
      ['fVisitDate',  { required: true, date: true }],
      ['fCost',       { required: true, number: true }],
      ['fDiagnosis',  { required: true, minLen: 5 }],
    ];
    livePairs.forEach(([id, spec]) => {
      const el = document.getElementById(id);
      if (el) {
        HMS.validate.injectErrorSpan(el);
        HMS.validate.attachLive(el, spec);
      }
    });
  });
})();
