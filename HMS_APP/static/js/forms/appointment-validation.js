/**
 * Public Appointment Booking Form Validation
 * File: static/js/forms/appointment-validation.js
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('apptForm');
    if (!form) return;

    const fields = {
      name:       form.querySelector('[name="name"]'),
      phone:      form.querySelector('[name="phone"]'),
      department: form.querySelector('[name="department"]'),
      mode:       form.querySelector('[name="mode"]'),
      date:       form.querySelector('[name="date"]'),
    };

    const SPECS = {
      name: {
        required: true,
        minLen: 3,
        messages: {
          required: 'Full name is required.',
          minLen:   'Name must be at least 3 characters.',
        },
      },
      phone: {
        required: true,
        phone: true,
        messages: {
          required: 'Phone number is required.',
          phone:    'Enter a valid 10-digit mobile number (starts with 6–9).',
        },
      },
      department: {
        required: true,
        messages: { required: 'Please select a department.' },
      },
      mode: {
        required: true,
        messages: { required: 'Please select a consultation mode.' },
      },
      date: {
        required: true,
        date: true,
        futureDate: true,
        messages: {
          required:    'Please select an appointment date.',
          date:        'Enter a valid date.',
          futureDate:  'Appointment date must be today or in the future.',
        },
      },
    };

    // Inject error spans
    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    // Phone digits only
    if (fields.phone) {
      fields.phone.addEventListener('keypress', e => { if (!/[0-9]/.test(e.key)) e.preventDefault(); });
    }

    // Set min date to today
    if (fields.date) {
      const today = new Date().toISOString().split('T')[0];
      fields.date.setAttribute('min', today);
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
        HMS.toast.show('Please fill all required fields correctly.', 'danger');
        const btn = form.querySelector('[type="submit"]');
        if (btn) HMS.validate.shakeButton(btn);
        const firstInvalid = form.querySelector('.is-invalid');
        if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  });
})();
