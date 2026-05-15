/**
 * Receptionist – Generate Bill & Record Payment Validation
 * File: static/js/forms/receptionist-billing-validation.js
 *
 * Exports:
 *   HMS.validateGenerateBill()  – called before bill generation
 *   HMS.validateRecordPayment() – called before saving a payment
 *
 * Depends on: validation-core.js
 */

(function () {
  'use strict';

  /* ── Generate Bill ──────────────────────────────────── */
  HMS.validateGenerateBill = function () {
    const selPatient     = document.getElementById('selPatient');
    const selAppointment = document.getElementById('selAppointment');
    const paymentDate    = document.getElementById('paymentDate');

    let valid = true;

    // Patient must be selected
    if (selPatient) {
      HMS.validate.injectErrorSpan(selPatient);
      if (!HMS.validate.validateField(selPatient, {
        required: true,
        messages: { required: 'Please select a patient.' },
      })) valid = false;
    }

    // Appointment must be selected (not disabled/empty)
    if (selAppointment && !selAppointment.disabled) {
      HMS.validate.injectErrorSpan(selAppointment);
      if (!HMS.validate.validateField(selAppointment, {
        required: true,
        messages: { required: 'Please select an appointment.' },
      })) valid = false;
    }

    // Payment date required
    if (paymentDate) {
      HMS.validate.injectErrorSpan(paymentDate);
      if (!HMS.validate.validateField(paymentDate, {
        required: true,
        date: true,
        messages: {
          required: 'Payment date is required.',
          date:     'Enter a valid payment date.',
        },
      })) valid = false;
    }

    if (!valid) {
      HMS.toast.show('Please fill all required billing fields.', 'danger');
    }

    return valid;
  };

  /* ── Record Payment ─────────────────────────────────── */
  HMS.validateRecordPayment = function () {
    const payAmount = document.getElementById('payAmount');
    const payMethod = document.getElementById('payMethod');
    const payTxn    = document.getElementById('payTxn');
    const payDate   = document.getElementById('payDate');

    let valid = true;

    if (payAmount) {
      HMS.validate.injectErrorSpan(payAmount);
      if (!HMS.validate.validateField(payAmount, {
        required: true,
        positive: true,
        messages: {
          required: 'Payment amount is required.',
          positive: 'Amount must be greater than 0.',
        },
      })) valid = false;
    }

    if (payMethod) {
      HMS.validate.injectErrorSpan(payMethod);
      if (!HMS.validate.validateField(payMethod, {
        required: true,
        messages: { required: 'Please select a payment method.' },
      })) valid = false;
    }

    // Transaction ID required for Card / UPI
    if (payMethod && payTxn) {
      const method = payMethod.value;
      if (method === 'Card' || method === 'UPI') {
        HMS.validate.injectErrorSpan(payTxn);
        if (!HMS.validate.validateField(payTxn, {
          required: true,
          minLen: 4,
          messages: {
            required: 'Transaction ID is required for Card/UPI payments.',
            minLen:   'Enter a valid transaction ID (min 4 characters).',
          },
        })) valid = false;
      } else {
        HMS.validate.clearField(payTxn);
      }
    }

    if (payDate) {
      HMS.validate.injectErrorSpan(payDate);
      if (!HMS.validate.validateField(payDate, {
        required: true,
        date: true,
        messages: {
          required: 'Payment date is required.',
          date:     'Enter a valid date.',
        },
      })) valid = false;
    }

    if (!valid) {
      HMS.toast.show('Please fix the payment details before saving.', 'danger');
    }

    return valid;
  };

  // Attach live validation when DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    const payMethod = document.getElementById('payMethod');
    const payTxn    = document.getElementById('payTxn');

    // Show/hide transaction ID requirement based on method
    if (payMethod && payTxn) {
      const txnLabel = payTxn.previousElementSibling || payTxn.closest('.mb-3, .form-group');
      payMethod.addEventListener('change', function () {
        const needsTxn = this.value === 'Card' || this.value === 'UPI';
        if (payTxn.closest('.mb-3, .form-group')) {
          payTxn.closest('.mb-3, .form-group').style.display = needsTxn ? '' : '';
        }
        if (!needsTxn) HMS.validate.clearField(payTxn);
        payTxn.placeholder = needsTxn
          ? 'Required for Card/UPI — enter transaction ID'
          : 'Optional for this payment method';
      });
    }
  });
})();
