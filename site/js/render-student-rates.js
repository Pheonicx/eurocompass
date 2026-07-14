import { state } from './state.js';

export function renderStudentRates() {
  const section = document.getElementById('student-section');
  const withStudent = state.banks.filter(b => b.student);

  if (withStudent.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';

  const hasSplit = withStudent.some(b => b.student.buy !== undefined);

  document.getElementById('studentHead').innerHTML = hasSplit
    ? `<tr><th>Bank</th><th class="num">Buy</th><th class="num">Sell</th></tr>`
    : `<tr><th>Bank</th><th class="num">Rate</th></tr>`;

  document.getElementById('studentBody').innerHTML = withStudent.map(b => {
    if (b.student.buy !== undefined) {
      return `<tr>
        <td><div class="bank-cell"><div class="bank-swatch" style="background:${b.color};"></div><span class="bank-name">${b.name}</span></div></td>
        <td class="num">৳${b.student.buy.toFixed(2)}</td>
        <td class="num">৳${b.student.sell.toFixed(2)}</td>
      </tr>`;
    }
    return `<tr>
      <td><div class="bank-cell"><div class="bank-swatch" style="background:${b.color};"></div><span class="bank-name">${b.name}</span></div></td>
      <td class="num" ${hasSplit ? 'colspan="2"' : ''}>৳${b.student.rate.toFixed(2)}</td>
    </tr>`;
  }).join('');
}
