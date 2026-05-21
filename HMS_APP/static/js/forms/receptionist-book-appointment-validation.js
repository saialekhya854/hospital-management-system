/**
 * Receptionist – Book Appointment Form Validation
 * File: static/js/forms/receptionist-book-appointment-validation.js
 *
 * Validates required fields before the AJAX submit in book_appointment.html.
 * Integrates with the existing bookAppointment() JS function via a
 * exported HMS.validateBookAppt() helper that the template can call.
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  /**
   * Called by the existing "Book Appointment" button handler.
   * Returns true if all required fields are filled, false otherwise.
   */
  HMS.validateBookAppt = function () {
    const selDept   = document.getElementById('selDept');
    const selDoctor = document.getElementById('selDoctor');
    const apptDate  = document.getElementById('apptDate');
    const reason    = document.getElementById('reason');

    const fields = { selDept, selDoctor, apptDate, reason };
    const SPECS = {
      selDept: {
        required: true,
        messages: { required: 'Please select a department.' },
      },
      selDoctor: {
        required: true,
        messages: { required: 'Please select a doctor.' },
      },
      apptDate: {
        required: true,
        date: true,
        futureDate: true,
        messages: {
          required:   'Appointment date is required.',
          date:       'Enter a valid date.',
          futureDate: 'Appointment date must be today or in the future.',
        },
      },
      reason: {
        required: true,
        minLen: 3,
        messages: {
          required: 'Reason for visit is required.',
          minLen:   'Please provide at least 3 characters.',
        },
      },
    };

    // Inject error spans once
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld) HMS.validate.injectErrorSpan(fld);
    });

    let valid = true;
    Object.entries(fields).forEach(([key, fld]) => {
      if (fld && !HMS.validate.validateField(fld, SPECS[key])) valid = false;
    });

    if (!valid) {
      HMS.toast.show('Please fill all required appointment fields.', 'danger');
      const first = document.querySelector('#apptDate.is-invalid, #selDept.is-invalid, #selDoctor.is-invalid, #reason.is-invalid');
      if (first) first.focus();
    }

    return valid;
  };

  // Also set min date on apptDate when DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    const apptDate = document.getElementById('apptDate');
    if (apptDate) {
      apptDate.setAttribute('min', new Date().toISOString().split('T')[0]);
    }

    // Attach live validation to static fields
    const staticFields = {
      apptDate: document.getElementById('apptDate'),
      reason:   document.getElementById('reason'),
    };
    const staticSpecs = {
      apptDate: { required: true, date: true, futureDate: true },
      reason:   { required: true, minLen: 3 },
    };
    Object.entries(staticFields).forEach(([key, fld]) => {
      if (fld) {
        HMS.validate.injectErrorSpan(fld);
        HMS.validate.attachLive(fld, staticSpecs[key]);
      }
    });
  });
})();
