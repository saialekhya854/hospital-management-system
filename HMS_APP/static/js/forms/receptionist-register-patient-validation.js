/**
 * Receptionist – Register Patient Form Validation
 * File: static/js/forms/receptionist-register-patient-validation.js
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('registerForm');
    if (!form) return;

    const fields = {
      fname:  document.getElementById('fname'),
      lname:  document.getElementById('lname'),
      dob:    document.getElementById('dob'),
      gender: document.getElementById('gender'),
      phone:  document.getElementById('phone'),
    };

    const SPECS = {
      fname: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'First name is required.',
          alpha:    'First name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      lname: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'Last name is required.',
          alpha:    'Last name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      dob: {
        required: true,
        date: true,
        pastDate: true,
        messages: {
          required:  'Date of birth is required.',
          date:      'Enter a valid date.',
          pastDate:  'Date of birth cannot be in the future.',
        },
      },
      gender: {
        required: true,
        messages: { required: 'Please select gender.' },
      },
      phone: {
        required: true,
        phone: true,
        messages: {
          required: 'Phone number is required.',
          phone:    'Enter a valid 10-digit mobile number (starts with 6–9).',
        },
      },
    };

    // Inject error spans
    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    // Phone: digits only
    if (fields.phone) {
      fields.phone.addEventListener('keypress', e => {
        if (!/[0-9]/.test(e.key)) e.preventDefault();
      });
      fields.phone.setAttribute('maxlength', '10');
    }

    // Set dob max to today
    if (fields.dob) {
      fields.dob.setAttribute('max', new Date().toISOString().split('T')[0]);
    }

    // Live validation
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld) HMS.validate.attachLive(fld, SPECS[key]);
    });

    // Submit
    form.addEventListener('submit', function (e) {
      let valid = true;
      Object.entries(fields).forEach(([key, fld]) => {
        if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
      });

      if (!valid) {
        e.preventDefault();
        HMS.toast.show('Please fill all required patient details.', 'danger');
        const btn = document.getElementById('submitBtn');
        if (btn) HMS.validate.shakeButton(btn);
        const firstInvalid = form.querySelector('.is-invalid');
        if (firstInvalid) firstInvalid.focus();
      }
    });
  });
})();
