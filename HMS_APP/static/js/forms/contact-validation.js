/**
 * Public Contact Form Validation
 * File: static/js/forms/contact-validation.js
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('contactForm');
    if (!form) return;

    const fields = {
      name:    form.querySelector('[name="name"]'),
      email:   form.querySelector('[name="email"]'),
      message: form.querySelector('[name="message"]'),
    };

    const SPECS = {
      name: {
        required: true,
        minLen: 3,
        messages: {
          required: 'Your name is required.',
          minLen:   'Name must be at least 3 characters.',
        },
      },
      email: {
        required: true,
        email: true,
        messages: {
          required: 'Email address is required.',
          email:    'Enter a valid email address.',
        },
      },
      message: {
        required: true,
        minLen: 10,
        messages: {
          required: 'Message is required.',
          minLen:   'Message must be at least 10 characters.',
        },
      },
    };

    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld) HMS.validate.attachLive(fld, SPECS[key]);
    });

    form.addEventListener('submit', function (e) {
      let valid = true;
      Object.entries(fields).forEach(([key, fld]) => {
        if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
      });

      if (!valid) {
        e.preventDefault();
        HMS.toast.show('Please fill in all required fields.', 'danger');
        const btn = form.querySelector('[type="submit"]');
        if (btn) HMS.validate.shakeButton(btn);
      }
    });
  });
})();
