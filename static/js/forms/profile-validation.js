/**
 * Profile Form Validation (Patient & Doctor)
 * File: static/js/forms/profile-validation.js
 *
 * Exports:
 *   HMS.validatePatientProfile() – patient profile save
 *   HMS.validateDoctorProfile()  – doctor profile save
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  /* ── Patient Profile ────────────────────────────────── */
  HMS.validatePatientProfile = function () {
    const fields = {
      pfFName: document.getElementById('pfFName'),
      pfLName: document.getElementById('pfLName'),
      pfPhone: document.getElementById('pfPhone'),
    };

    const SPECS = {
      pfFName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'First name is required.',
          alpha:    'First name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      pfLName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'Last name is required.',
          alpha:    'Last name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      pfPhone: {
        required: false, // optional but validate format if provided
        phone: true,
        messages: {
          phone: 'Enter a valid 10-digit mobile number.',
        },
      },
    };

    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    let valid = true;
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
    });

    if (!valid) HMS.toast.show('Please fix the profile errors before saving.', 'danger');
    return valid;
  };

  /* ── Doctor Profile ─────────────────────────────────── */
  HMS.validateDoctorProfile = function () {
    const fields = {
      pfFName:  document.getElementById('pfFName'),
      pfLName:  document.getElementById('pfLName'),
      pfPhone:  document.getElementById('pfPhone'),
    };

    const SPECS = {
      pfFName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'First name is required.',
          alpha:    'First name should contain letters only.',
        },
      },
      pfLName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'Last name is required.',
          alpha:    'Last name should contain letters only.',
        },
      },
      pfPhone: {
        required: false,
        phone: true,
        messages: {
          phone: 'Enter a valid 10-digit mobile number.',
        },
      },
    };

    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    let valid = true;
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
    });

    if (!valid) HMS.toast.show('Please fix the errors before saving your profile.', 'danger');
    return valid;
  };

  // Attach live validation on profile fields
  document.addEventListener('DOMContentLoaded', function () {
    ['pfFName', 'pfLName'].forEach(id => {
      const el = document.getElementById(id);
      if (el && !el.disabled) {
        HMS.validate.injectErrorSpan(el);
        HMS.validate.attachLive(el, { required: true, alpha: true, minLen: 2 });
      }
    });

    const pfPhone = document.getElementById('pfPhone');
    if (pfPhone && !pfPhone.disabled) {
      HMS.validate.injectErrorSpan(pfPhone);
      HMS.validate.attachLive(pfPhone, { required: false, phone: true });
      pfPhone.addEventListener('keypress', e => {
        if (!/[0-9]/.test(e.key)) e.preventDefault();
      });
    }
  });
})();
