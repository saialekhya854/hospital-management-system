/**
 * Admin – Doctors & Departments Modal Form Validation
 * File: static/js/forms/admin-doctors-validation.js
 *
 * Exports:
 *   HMS.validateDoctorForm()     – called before save in doctor modal
 *   HMS.validateDepartmentForm() – called before save in department modal
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  /* ── Doctor Modal ───────────────────────────────────── */
  HMS.validateDoctorForm = function () {
    const fields = {
      dFName:   document.getElementById('dFName'),
      dLName:   document.getElementById('dLName'),
      dGender:  document.getElementById('dGender'),
      dDept:    document.getElementById('dDept'),
      dContact: document.getElementById('dContact'),
      dEmail:   document.getElementById('dEmail'),
    };

    const SPECS = {
      dFName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'First name is required.',
          alpha:    'First name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      dLName: {
        required: true,
        alpha: true,
        minLen: 2,
        messages: {
          required: 'Last name is required.',
          alpha:    'Last name should contain letters only.',
          minLen:   'At least 2 characters required.',
        },
      },
      dGender: {
        required: true,
        messages: { required: 'Please select gender.' },
      },
      dDept: {
        required: true,
        messages: { required: 'Please select a department.' },
      },
      dContact: {
        required: true,
        phone: true,
        messages: {
          required: 'Contact number is required.',
          phone:    'Enter a valid 10-digit mobile number.',
        },
      },
      dEmail: {
        required: true,
        email: true,
        messages: {
          required: 'Email address is required.',
          email:    'Enter a valid email address.',
        },
      },
    };

    // Inject error spans
    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    let valid = true;
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
    });

    if (!valid) {
      HMS.toast.show('Please fill all required doctor information.', 'danger');
    }

    return valid;
  };

  /* ── Department Modal ───────────────────────────────── */
  HMS.validateDepartmentForm = function () {
    const deptName = document.getElementById('deptName') || document.getElementById('newDeptName');
    if (!deptName) return true;

    HMS.validate.injectErrorSpan(deptName);
    const valid = HMS.validate.validateField(deptName, {
      required: true,
      minLen: 2,
      messages: {
        required: 'Department name is required.',
        minLen:   'Department name must be at least 2 characters.',
      },
    });

    if (!valid) HMS.toast.show('Please enter a department name.', 'warning');
    return valid;
  };

  /* ── Admin Users Modal ──────────────────────────────── */
  HMS.validateUserForm = function () {
    const fields = {
      uName:  document.getElementById('uName'),
      uEmail: document.getElementById('uEmail'),
      uRole:  document.getElementById('uRole'),
    };

    const SPECS = {
      uName: {
        required: true,
        minLen: 3,
        messages: {
          required: 'Full name is required.',
          minLen:   'At least 3 characters required.',
        },
      },
      uEmail: {
        required: true,
        email: true,
        messages: {
          required: 'Email is required.',
          email:    'Enter a valid email address.',
        },
      },
      uRole: {
        required: true,
        messages: { required: 'Please select a role.' },
      },
    };

    Object.values(fields).forEach(f => { if (f) HMS.validate.injectErrorSpan(f); });

    let valid = true;
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
    });

    if (!valid) HMS.toast.show('Please fill all required user information.', 'danger');
    return valid;
  };

  // Live validation on blur for modal fields
  document.addEventListener('DOMContentLoaded', function () {
    const doctorFields = ['dFName', 'dLName', 'dContact', 'dEmail'];
    doctorFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('blur', () => {
          if (id === 'dContact') {
            HMS.validate.validateField(el, { required: true, phone: true });
          } else if (id === 'dEmail') {
            HMS.validate.validateField(el, { required: true, email: true });
          } else {
            HMS.validate.validateField(el, { required: true, minLen: 2, alpha: true });
          }
        });
      }
    });
  });
})();
