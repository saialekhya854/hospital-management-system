/**
 * Public Patient Registration Form Validation
 * File: static/js/forms/register-validation.js
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('regForm');
    if (!form) return;

    // ── Field references ─────────────────────────────────
    const fields = {
      fname:   form.querySelector('[name="fname"]'),
      lname:   form.querySelector('[name="lname"]'),
      dob:     form.querySelector('[name="dob"]'),
      gender:  form.querySelector('[name="gender"]'),
      phone:   form.querySelector('[name="phone"]'),
      email:   form.querySelector('[name="email"]'),
      password: document.getElementById('rPwd'),
      confirm:  document.getElementById('rConfirm'),
      terms:    document.getElementById('rTerms'),
    };

    // Inject error spans for each field
    Object.values(fields).forEach(f => {
      if (f && f.type !== 'checkbox') HMS.validate.injectErrorSpan(f);
    });
    // Terms error span
    if (fields.terms) {
      const termsContainer = fields.terms.closest('.form-check') || fields.terms.parentElement;
      if (!termsContainer.querySelector('.hms-error-msg')) {
        const span = document.createElement('span');
        span.className = 'hms-error-msg';
        span.id = 'termsError';
        termsContainer.appendChild(span);
      }
    }

    // ── Validation specs ─────────────────────────────────
    const SPECS = {
      fname: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'First name is required.',
          alpha:    'First name should contain only letters.',
          minLen:   'First name must be at least 2 characters.',
        },
      },
      lname: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'Last name is required.',
          alpha:    'Last name should contain only letters.',
          minLen:   'Last name must be at least 2 characters.',
        },
      },
      dob: {
        required: true,
        date: true,
        pastDate: true,
        messages: {
          required:  'Date of birth is required.',
          date:      'Enter a valid date.',
          pastDate:  'Date of birth cannot be a future date.',
        },
      },
      gender: {
        required: true,
        messages: { required: 'Please select your gender.' },
      },
      phone: {
        required: true,
        phone: true,
        messages: {
          required: 'Phone number is required.',
          phone:    'Enter a valid 10-digit Indian mobile number starting with 6-9.',
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
      password: {
        required: true,
        minLen: 8,
        messages: {
          required: 'Password is required.',
          minLen:   'Password must be at least 8 characters.',
        },
      },
    };

    // ── Live validation ──────────────────────────────────
    if (fields.fname)    HMS.validate.attachLive(fields.fname,    SPECS.fname);
    if (fields.lname)    HMS.validate.attachLive(fields.lname,    SPECS.lname);
    if (fields.dob)      HMS.validate.attachLive(fields.dob,      SPECS.dob);
    if (fields.gender)   HMS.validate.attachLive(fields.gender,   SPECS.gender);
    if (fields.phone)    HMS.validate.attachLive(fields.phone,    SPECS.phone);
    if (fields.email)    HMS.validate.attachLive(fields.email,    SPECS.email);
    if (fields.password) HMS.validate.attachLive(fields.password, SPECS.password);

    // Phone: allow only digits
    if (fields.phone) {
      fields.phone.addEventListener('keypress', function (e) {
        if (!/[0-9]/.test(e.key)) e.preventDefault();
      });
    }

    // Confirm password live check
    if (fields.confirm && fields.password) {
      fields.confirm.addEventListener('input', function () {
        const match = this.value === fields.password.value;
        if (this.value && !match) {
          HMS.validate.setError(this, 'Passwords do not match.');
        } else if (match && this.value) {
          HMS.validate.setValid(this);
        }
      });
      fields.confirm.addEventListener('blur', function () {
        const match = this.value === fields.password.value;
        if (!this.value) {
          HMS.validate.setError(this, 'Please confirm your password.');
        } else if (!match) {
          HMS.validate.setError(this, 'Passwords do not match.');
        } else {
          HMS.validate.setValid(this);
        }
      });
    }

    // Password strength (re-uses existing bars from template)
    HMS.validate.attachPasswordStrength('rPwd', 'pwdFill', 'pwdLabel');

    // ── Submit handler ───────────────────────────────────
    form.addEventListener('submit', function (e) {
      let valid = true;

      const checks = ['fname', 'lname', 'dob', 'gender', 'phone', 'email', 'password'];
      checks.forEach(key => {
        if (fields[key] && !HMS.validate.validateField(fields[key], SPECS[key])) {
          valid = false;
        }
      });

      // Confirm password
      if (fields.confirm) {
        if (!fields.confirm.value.trim()) {
          HMS.validate.setError(fields.confirm, 'Please confirm your password.');
          valid = false;
        } else if (fields.confirm.value !== fields.password.value) {
          HMS.validate.setError(fields.confirm, 'Passwords do not match.');
          valid = false;
        } else {
          HMS.validate.setValid(fields.confirm);
        }
      }

      // Terms checkbox
      if (fields.terms && !fields.terms.checked) {
        const span = document.getElementById('termsError');
        if (span) {
          span.textContent = 'You must accept the terms and conditions.';
          span.classList.add('visible');
        }
        valid = false;
      } else if (fields.terms) {
        const span = document.getElementById('termsError');
        if (span) span.classList.remove('visible');
      }

      if (!valid) {
        e.preventDefault();
        HMS.toast.show('Please fix all highlighted errors before registering.', 'danger');
        const btn = document.getElementById('regBtn');
        if (btn) HMS.validate.shakeButton(btn);
        const firstInvalid = form.querySelector('.is-invalid');
        if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });

    // Clear terms error when checked
    if (fields.terms) {
      fields.terms.addEventListener('change', function () {
        const span = document.getElementById('termsError');
        if (span && this.checked) span.classList.remove('visible');
      });
    }
  });
})();
