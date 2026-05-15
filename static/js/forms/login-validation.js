/**
 * Login Form Validation
 * File: static/js/forms/login-validation.js
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form     = document.querySelector('form[action="/login"]');
    const emailFld = form && form.querySelector('input[name="email"]');
    const pwdFld   = form && form.querySelector('input[name="password"]');

    if (!form) return;

    // Inject error spans
    HMS.validate.injectErrorSpan(emailFld);
    HMS.validate.injectErrorSpan(pwdFld);

    const SPECS = {
      email: {
        required: true,
        email: true,
        messages: {
          required: 'Email address is required.',
          email:    'Enter a valid email address (e.g. user@example.com).',
        },
      },
      password: {
        required: true,
        minLen: 6,
        messages: {
          required: 'Password is required.',
          minLen:   'Password must be at least 6 characters.',
        },
      },
    };

    // Live validation
    HMS.validate.attachLive(emailFld, SPECS.email);
    HMS.validate.attachLive(pwdFld,   SPECS.password);

    // Submit validation
    form.addEventListener('submit', function (e) {
      let valid = true;

      if (!HMS.validate.validateField(emailFld, SPECS.email)) valid = false;
      if (!HMS.validate.validateField(pwdFld,   SPECS.password)) valid = false;

      if (!valid) {
        e.preventDefault();
        HMS.toast.show('Please fix the errors before submitting.', 'danger');
        const btn = form.querySelector('[type="submit"]');
        if (btn) HMS.validate.shakeButton(btn);
        // Focus first invalid
        const first = form.querySelector('.is-invalid');
        if (first) first.focus();
      }
    });
  });
})();
