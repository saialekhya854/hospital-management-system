/**
 * HMS Form Validation Core Utilities
 * File: static/js/modules/validation-core.js
 *
 * Provides reusable validation helpers used across all forms.
 * Import/include BEFORE any form-specific validation script.
 */

const HMS = window.HMS || {};

/* ── Toast Notification ──────────────────────────────── */
HMS.toast = (function () {
  function getContainer() {
    let c = document.getElementById('hms-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'hms-toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  const ICONS = {
    success: '✔',
    danger:  '✖',
    warning: '⚠',
    info:    'ℹ',
  };

  function show(message, type = 'info', duration = 4000) {
    const container = getContainer();
    const el = document.createElement('div');
    el.className = `hms-toast toast-${type}`;
    el.innerHTML = `
      <span class="toast-icon">${ICONS[type] || 'ℹ'}</span>
      <span>${message}</span>
      <button class="toast-close" aria-label="Close">×</button>
    `;

    el.querySelector('.toast-close').addEventListener('click', () => remove(el));
    container.appendChild(el);

    if (duration > 0) setTimeout(() => remove(el), duration);
  }

  function remove(el) {
    el.classList.add('removing');
    setTimeout(() => el.remove(), 230);
  }

  return { show };
})();

/* ── Field Validation Helpers ────────────────────────── */
HMS.validate = (function () {

  /** Mark a field as invalid and show its error message */
  function setError(field, message) {
    field.classList.remove('is-valid');
    field.classList.add('is-invalid');
    let errEl = field.parentElement.querySelector('.hms-error-msg');
    if (!errEl) {
      // Walk up one more level (for input-group wrappers)
      errEl = field.closest('.form-group, .mb-3, .col-md-6, .col-12')
               && field.closest('.form-group, .mb-3, .col-md-6, .col-12')
                       .querySelector('.hms-error-msg');
    }
    if (errEl) {
      errEl.textContent = message;
      errEl.classList.add('visible');
    }
  }

  /** Mark a field as valid and hide its error message */
  function setValid(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    const container = field.closest('.form-group, .mb-3, .col-md-6, .col-12, .input-group');
    if (container) {
      const errEl = container.querySelector('.hms-error-msg');
      if (errEl) errEl.classList.remove('visible');
    }
  }

  /** Clear all validation states */
  function clearField(field) {
    field.classList.remove('is-valid', 'is-invalid');
    const container = field.closest('.form-group, .mb-3, .col-md-6, .col-12');
    if (container) {
      const errEl = container.querySelector('.hms-error-msg');
      if (errEl) errEl.classList.remove('visible');
    }
  }

  /** Rules */
  const RULES = {
    required: (v) => v.trim() !== '',
    email:    (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()),
    phone:    (v) => /^[6-9]\d{9}$/.test(v.trim()),
    minLen:   (v, n) => v.trim().length >= n,
    number:   (v) => !isNaN(v) && v.trim() !== '',
    positive: (v) => !isNaN(v) && parseFloat(v) > 0,
    date:     (v) => v !== '' && !isNaN(Date.parse(v)),
    futureDate: (v) => {
      if (!v) return false;
      return new Date(v) >= new Date(new Date().toDateString());
    },
    pastDate: (v) => {
      if (!v) return false;
      return new Date(v) <= new Date();
    },
    alpha:    (v) => /^[A-Za-z\s'-]+$/.test(v.trim()),
    pin:      (v) => /^\d{6}$/.test(v.trim()),
  };

  /**
   * Validate a single field against a spec object.
   * spec: { required, email, phone, minLen, number, positive, date,
   *          futureDate, pastDate, alpha, pin, match, custom,
   *          messages: { required, email, ... } }
   * Returns true if valid, false otherwise (also marks the field).
   */
  function validateField(field, spec = {}) {
    const val = field.value;
    const msgs = spec.messages || {};

    // Skip optional empty fields
    if (!spec.required && val.trim() === '') {
      clearField(field);
      return true;
    }

    if (spec.required && !RULES.required(val)) {
      setError(field, msgs.required || 'This field is required.');
      return false;
    }
    if (spec.email && !RULES.email(val)) {
      setError(field, msgs.email || 'Enter a valid email address.');
      return false;
    }
    if (spec.phone && !RULES.phone(val)) {
      setError(field, msgs.phone || 'Enter a valid 10-digit Indian mobile number.');
      return false;
    }
    if (spec.minLen && !RULES.minLen(val, spec.minLen)) {
      setError(field, msgs.minLen || `Minimum ${spec.minLen} characters required.`);
      return false;
    }
    if (spec.number && !RULES.number(val)) {
      setError(field, msgs.number || 'Enter a valid number.');
      return false;
    }
    if (spec.positive && !RULES.positive(val)) {
      setError(field, msgs.positive || 'Enter a positive number greater than 0.');
      return false;
    }
    if (spec.date && !RULES.date(val)) {
      setError(field, msgs.date || 'Enter a valid date.');
      return false;
    }
    if (spec.futureDate && !RULES.futureDate(val)) {
      setError(field, msgs.futureDate || 'Date must be today or in the future.');
      return false;
    }
    if (spec.pastDate && !RULES.pastDate(val)) {
      setError(field, msgs.pastDate || 'Date must be in the past or today.');
      return false;
    }
    if (spec.alpha && !RULES.alpha(val)) {
      setError(field, msgs.alpha || 'Only letters and spaces are allowed.');
      return false;
    }
    if (spec.pin && !RULES.pin(val)) {
      setError(field, msgs.pin || 'Enter a valid 6-digit PIN code.');
      return false;
    }
    if (spec.match) {
      const matchField = typeof spec.match === 'string'
        ? document.getElementById(spec.match)
        : spec.match;
      if (matchField && val !== matchField.value) {
        setError(field, msgs.match || 'Values do not match.');
        return false;
      }
    }
    if (spec.custom) {
      const result = spec.custom(val, field);
      if (result !== true) {
        setError(field, typeof result === 'string' ? result : (msgs.custom || 'Invalid value.'));
        return false;
      }
    }

    setValid(field);
    return true;
  }

  /**
   * Validate a whole form given a map of { fieldId: spec }.
   * Returns { valid: bool, errors: [fieldId, ...] }
   */
  function validateForm(specMap) {
    let valid = true;
    const errors = [];
    for (const [id, spec] of Object.entries(specMap)) {
      const field = document.getElementById(id);
      if (!field) continue;
      if (!validateField(field, spec)) {
        valid = false;
        errors.push(id);
      }
    }
    return { valid, errors };
  }

  /**
   * Attach live (blur + input) validation to a field.
   */
  function attachLive(field, spec) {
    field.addEventListener('blur', () => validateField(field, spec));
    field.addEventListener('input', () => {
      if (field.classList.contains('is-invalid')) validateField(field, spec);
    });
  }

  /**
   * Shake a button to indicate failed submission.
   */
  function shakeButton(btn) {
    btn.classList.remove('hms-shake');
    void btn.offsetWidth; // reflow
    btn.classList.add('hms-shake');
    setTimeout(() => btn.classList.remove('hms-shake'), 400);
  }

  /**
   * Insert error span after a field if not already present.
   * Called automatically by form-specific scripts on init.
   */
  function injectErrorSpan(field, message = '') {
    const container = field.closest('.form-group, .mb-3, .col-md-6, .col-12')
                   || field.parentElement;
    if (container && !container.querySelector('.hms-error-msg')) {
      const span = document.createElement('span');
      span.className = 'hms-error-msg';
      span.textContent = message;
      // Insert after input-group or after field itself
      const inputGroup = container.querySelector('.input-group');
      (inputGroup || field).insertAdjacentElement('afterend', span);
    }
  }

  /**
   * Password strength scorer. Returns 0-4.
   */
  function passwordStrength(pw) {
    let s = 0;
    if (pw.length >= 8) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  }

  /**
   * Attach password strength UI to a password field.
   * Requires .hms-pwd-bar > .hms-pwd-fill and .hms-pwd-label elements
   * as siblings in the same container.
   */
  function attachPasswordStrength(fieldId, fillId, labelId) {
    const field = document.getElementById(fieldId);
    const fill  = document.getElementById(fillId);
    const label = document.getElementById(labelId);
    if (!field || !fill) return;

    const LEVELS = [
      { w: '0%',   bg: '#e3e8f0', lbl: '' },
      { w: '25%',  bg: '#e74c3c', lbl: 'Weak' },
      { w: '50%',  bg: '#f39c12', lbl: 'Fair' },
      { w: '75%',  bg: '#3498db', lbl: 'Good' },
      { w: '100%', bg: '#27ae60', lbl: 'Strong' },
    ];

    field.addEventListener('input', function () {
      const s = passwordStrength(this.value);
      fill.style.width      = LEVELS[s].w;
      fill.style.background = LEVELS[s].bg;
      if (label) {
        label.textContent = LEVELS[s].lbl || 'Use 8+ chars with letters & numbers';
        label.style.color = LEVELS[s].bg || '#888';
      }
    });
  }

  /** Toggle password visibility */
  function togglePassword(fieldId, iconEl) {
    const f = document.getElementById(fieldId);
    if (!f) return;
    if (f.type === 'password') {
      f.type = 'text';
      if (iconEl) {
        iconEl.className = iconEl.className
          .replace('bi-eye', 'bi-eye-slash')
          .replace('icofont-eye', 'icofont-eye-blocked');
      }
    } else {
      f.type = 'password';
      if (iconEl) {
        iconEl.className = iconEl.className
          .replace('bi-eye-slash', 'bi-eye')
          .replace('icofont-eye-blocked', 'icofont-eye');
      }
    }
  }

  return {
    setError, setValid, clearField,
    validateField, validateForm,
    attachLive, shakeButton, injectErrorSpan,
    passwordStrength, attachPasswordStrength, togglePassword,
    RULES,
  };
})();

window.HMS = HMS;
