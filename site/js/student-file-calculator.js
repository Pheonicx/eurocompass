/**
 * Student File Cost Calculator
 * Displays student file requirements, charges, and total cost calculations
 */

const STUDENT_FILE_INFO = {
  CITY: {
    name: "CITY Bank",
    fileOpeningCharge: 7000, // Estimated
    swiftCharge: 1150, // Estimated
    remittanceCharge: { min: 115, max: 575 }, // Tk variable
    intermediaryCharges: {
      EUR: { amount: 20, currency: "EUR", bdtEstimate: 2700 },
      USD: 15,
      GBP: 25,
      JPY: 10000
    },
    documents: [
      "Admission letter",
      "Living expense documents",
      "Refund policy",
      "Educational certificates",
      "Student ID / VISA",
      "Photographs",
      "Payment proof"
    ],
    contact: "To be confirmed",
    email: "To be confirmed"
  },
  PRIME: {
    name: "PRIME Bank",
    fileOpeningCharge: 6900, // Tk (includes Tk 900 VAT)
    swiftCharge: 1150, // Tk per transaction
    remittanceCharge: { min: 115, max: 575 }, // Tk variable
    intermediaryCharges: {
      EUR: { amount: 17, currency: "EUR", bdtEstimate: 2400 }, // EUR 17-27
      USD: 15, // USD
      GBP: 25, // GBP
      JPY: 10000 // JPY
    },
    documents: [
      "Admission letter (mentioning annual tuition, program structure)",
      "Documents relating to board, lodging, living expenses",
      "Institution refund policy",
      "Educational certificates",
      "VISA (if any) / Mandatory for already resident student abroad",
      "1x student photo + 1x financier photo",
      "Up-to-date results, progression copies, payment vouchers"
    ],
    contact: "01787688680",
    email: "gsn@primebank.com.bd",
    swift: "PRBLBDDHA016",
    website: "www.prime-bank.com.bd"
  },
  BRAC: {
    name: "BRAC Bank",
    fileOpeningCharge: 8625, // Tk (8050 + 575 VAT)
    swiftCharge: 0, // Included in corresponding bank charge
    remittanceCharge: { min: 0, max: 0 }, // Tk
    intermediaryCharges: {
      EUR: { amount: 60, currency: "EUR", bdtEstimate: 8250 },
      USD: 12, // USD
      GBP: 30, // GBP
      AUD: 2500, // BDT
      JPY: 8050, // BDT
      CAD: "NOT AVAILABLE",
      NZD: "NOT AVAILABLE"
    },
    documents: [
      "Offer letter from educational institution",
      "Institution refund policy",
      "Invoice / Cost breakdown",
      "All educational certificates",
      "Main passport (copy)",
      "Student photograph"
    ],
    contact: "01778154800",
    email: "ahmed.zia@bracbank.com",
    branch: "Shatarupa Bhattacharjee, Progati Sarani Branch",
    website: "www.bracbank.com.bd"
  },
  EBL: {
    name: "EBL Bank",
    fileOpeningCharge: 7000, // Estimated
    swiftCharge: 1100, // Estimated
    remittanceCharge: { min: 100, max: 500 },
    intermediaryCharges: {
      EUR: { amount: 20, currency: "EUR", bdtEstimate: 2750 },
      USD: 15,
      GBP: 25,
      JPY: 10000
    },
    documents: [
      "Admission letter",
      "Living expense documents",
      "Refund policy",
      "Educational certificates",
      "Student ID / VISA",
      "Photographs",
      "Payment proof"
    ],
    contact: "To be confirmed",
    email: "To be confirmed"
  }
};

export function initStudentFileCalculator(bankRates) {
  setupBankSelector();
  setupCalculatorInputs(bankRates);
  renderInitialInfo();

  // Update calculator on input change
  document.getElementById('studentCalcEUR').addEventListener('input', () => {
    updateCalculation(bankRates);
  });

  document.getElementById('studentCalcBank').addEventListener('change', () => {
    updateCalculation(bankRates);
  });
}

function setupBankSelector() {
  const buttons = document.querySelectorAll('.student-bank-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderBankInfo(btn.dataset.bank);
    });
  });
}

function setupCalculatorInputs(bankRates) {
  // Update select options with current rates
  const selectElem = document.getElementById('studentCalcBank');
  selectElem.innerHTML = '';

  bankRates.forEach(bank => {
    if (bank.student) {
      const option = document.createElement('option');
      option.value = bank.bank;
      option.textContent = `${bank.bank} (${bank.student.rate?.toFixed(2) || 'N/A'} BDT/EUR)`;
      selectElem.appendChild(option);
    }
  });
}

function renderInitialInfo() {
  renderBankInfo('EBL');
}

function renderBankInfo(bankCode) {
  const info = STUDENT_FILE_INFO[bankCode];
  if (!info) return;

  const container = document.getElementById('studentFileInfo');

  const documentsHTML = info.documents
    .map(doc => `<li>✓ ${doc}</li>`)
    .join('');

  const chargesHTML = Object.entries(info.intermediaryCharges)
    .map(([curr, charge]) => {
      if (typeof charge === 'string') {
        return `<div class="charge-item"><span>${curr}</span><span>${charge}</span></div>`;
      }
      const amount = charge.amount || charge;
      const currency = charge.currency || curr;
      return `<div class="charge-item"><span>${currency}</span><span>${amount}</span></div>`;
    })
    .join('');

  container.innerHTML = `
    <div class="bank-info-grid">
      <div class="bank-info-section">
        <h4>Required Documents</h4>
        <ul class="document-list">
          ${documentsHTML}
        </ul>
      </div>

      <div class="bank-info-section">
        <h4>Charges & Fees</h4>
        <div class="charges-list">
          <div class="charge-item"><span>File Opening</span><span>৳${info.fileOpeningCharge.toLocaleString()}</span></div>
          ${info.swiftCharge > 0 ? `<div class="charge-item"><span>SWIFT/FTT</span><span>৳${info.swiftCharge}</span></div>` : ''}
          ${info.remittanceCharge.max > 0 ? `<div class="charge-item"><span>Remittance</span><span>৳${info.remittanceCharge.min}–${info.remittanceCharge.max}</span></div>` : ''}
          <div class="charge-divider"></div>
          <h5>Intermediary Bank Charges (per transaction)</h5>
          ${chargesHTML}
        </div>
      </div>

      <div class="bank-info-section">
        <h4>Contact Information</h4>
        <div class="contact-info">
          ${info.branch ? `<p><strong>Branch:</strong> ${info.branch}</p>` : ''}
          ${info.contact ? `<p><strong>Phone:</strong> ${info.contact}</p>` : ''}
          ${info.email ? `<p><strong>Email:</strong> ${info.email}</p>` : ''}
          ${info.swift ? `<p><strong>SWIFT:</strong> ${info.swift}</p>` : ''}
          ${info.website ? `<p><strong>Website:</strong> ${info.website}</p>` : ''}
        </div>
      </div>
    </div>
  `;
}

function updateCalculation(bankRates) {
  const eurAmount = parseFloat(document.getElementById('studentCalcEUR').value) || 0;
  const bankCode = document.getElementById('studentCalcBank').value;

  // Find the bank rate
  const bankData = bankRates.find(b => b.bank === bankCode);
  if (!bankData || !bankData.student) {
    document.getElementById('calcTotal').textContent = 'Bank not found';
    return;
  }

  const info = STUDENT_FILE_INFO[bankCode];
  const studentRate = bankData.student.rate || bankData.sell;

  // Calculate components
  const bdtAmount = eurAmount * studentRate;
  const fileCharge = info.fileOpeningCharge;
  const intermediaryEUR = info.intermediaryCharges.EUR?.amount || 0;
  const intermediaryBDT = (info.intermediaryCharges.EUR?.bdtEstimate || 0) * (eurAmount / 1000); // Scale by EUR amount

  const totalBDT = bdtAmount + fileCharge + intermediaryBDT;

  // Update display
  document.getElementById('calcEUR').textContent = `€${eurAmount.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
  document.getElementById('calcRate').textContent = `${studentRate.toFixed(4)} BDT/EUR`;
  document.getElementById('calcBDT').textContent = `৳${bdtAmount.toLocaleString('en-US', {maximumFractionDigits: 0})}`;
  document.getElementById('calcFileCharge').textContent = `৳${fileCharge.toLocaleString()}`;
  document.getElementById('calcIntermediaryCharge').textContent = `${intermediaryEUR} EUR (≈ ৳${intermediaryBDT.toLocaleString('en-US', {maximumFractionDigits: 0})})`;
  document.getElementById('calcTotal').textContent = `৳${totalBDT.toLocaleString('en-US', {maximumFractionDigits: 0})}`;
}
