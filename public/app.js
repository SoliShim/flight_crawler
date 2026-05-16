const form = document.querySelector('#search-form');
const submitButton = document.querySelector('#submit-button');
const statusText = document.querySelector('#status-text');
const resultCount = document.querySelector('#result-count');
const resultsBody = document.querySelector('#results-body');
const downloadLink = document.querySelector('#download-link');
const logOutput = document.querySelector('#log-output');
const toggleLog = document.querySelector('#toggle-log');
const runtimeChip = document.querySelector('#runtime-chip');
const fileWarning = document.querySelector('#file-warning');
const runtimeWarningText = document.querySelector('#runtime-warning-text');
const returnDateField = document.querySelector('#return-date-field');
const inboundHeader = document.querySelector('#inbound-header');

const LOCAL_SERVER = 'http://127.0.0.1:8080';
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const IS_LOCAL_SERVER = LOCAL_HOSTS.has(window.location.hostname);
const IS_FILE_MODE = window.location.protocol === 'file:';
const IS_STATIC_HOSTING = !IS_FILE_MODE && !IS_LOCAL_SERVER;
const API_BASE = IS_FILE_MODE ? LOCAL_SERVER : '';
const query = new URLSearchParams(window.location.search);

function toYYYYMMDD(value) {
  return value.replaceAll('-', '');
}

function toInputDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function todayInputDate() {
  return toInputDate(new Date());
}

function tomorrowInputDate() {
  return toInputDate(addDays(new Date(), 1));
}

function sanitizeInputDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? value : '';
}

function setInitialDates() {
  const today = todayInputDate();
  const defaultDepart = tomorrowInputDate();
  const defaultReturn = toInputDate(addDays(new Date(), 2));
  const queryDepart = sanitizeInputDate(query.get('depart'));
  const queryReturn = sanitizeInputDate(query.get('returnDate'));
  let notice = '';

  form.elements.depart.min = today;
  form.elements.depart.value = queryDepart || defaultDepart;

  if (form.elements.depart.value < today) {
    form.elements.depart.value = defaultDepart;
    notice = 'URL의 출발일이 지난 날짜라 기본 날짜로 조정했습니다.';
  }

  form.elements.returnDate.value = queryReturn || defaultReturn;
  if (form.elements.returnDate.value <= form.elements.depart.value) {
    form.elements.returnDate.value = toInputDate(addDays(new Date(`${form.elements.depart.value}T00:00:00`), 1));
    notice = notice || '복귀일이 출발일보다 늦도록 자동 조정했습니다.';
  }

  syncReturnDateMin();
  return notice;
}

function applyQueryParams() {
  const source = query.get('source');
  if (['naver', 'google', 'trip', 'all'].includes(source)) {
    form.elements.source.value = source;
  }

  const tripType = query.get('tripType') || query.get('trip');
  if (['roundtrip', 'oneway'].includes(tripType)) {
    form.elements.tripType.value = tripType;
  }

  for (const name of ['dep3', 'arr3']) {
    const value = String(query.get(name) || '').trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(value)) {
      form.elements[name].value = value;
    }
  }

  const items = Number(query.get('items'));
  if (Number.isInteger(items) && items >= 1 && items <= 100) {
    form.elements.items.value = String(items);
  }

  const headless = query.get('headless');
  if (headless === 'false') {
    form.elements.headless.checked = false;
  }
}

function validateDepartDate() {
  const depart = form.elements.depart.value;
  const today = todayInputDate();
  const message = depart && depart < today
    ? '출발일은 오늘보다 빠를 수 없습니다.'
    : '';

  form.elements.depart.setCustomValidity(message);
  return !message;
}

function syncReturnDateMin() {
  const depart = form.elements.depart.value;
  const returnDate = form.elements.returnDate;

  returnDate.min = depart || '';
  validateDepartDate();
  validateDateOrder();
}

function validateDateOrder() {
  if (selectedTripType() === 'oneway') {
    form.elements.returnDate.setCustomValidity('');
    return true;
  }

  const depart = form.elements.depart.value;
  const returnDate = form.elements.returnDate.value;
  const message = depart && returnDate && depart >= returnDate
    ? '복귀일은 출발일보다 늦어야 합니다.'
    : '';

  form.elements.returnDate.setCustomValidity(message);
  return !message;
}

function selectedSourceName() {
  const names = {
    naver: '네이버 항공권',
    google: 'Google Flights',
    trip: 'Trip.com',
    all: '전부 검색하기',
  };
  return names[form.elements.source.value] || names.naver;
}

function selectedTripType() {
  return form.elements.tripType.value === 'oneway' ? 'oneway' : 'roundtrip';
}

function selectedTripTypeName() {
  return selectedTripType() === 'oneway' ? '편도' : '왕복';
}

function sourceLabel(source) {
  const labels = {
    naver: '네이버',
    google: 'Google',
    trip: 'Trip.com',
  };
  return labels[source] || source || '-';
}

function updateRuntimeState() {
  const sourceName = selectedSourceName();
  const tripTypeName = selectedTripTypeName();

  if (IS_FILE_MODE) {
    runtimeChip.textContent = '파일 모드';
    runtimeWarningText.textContent = '이 화면은 파일로 열렸습니다. 검색은 로컬 서버가 켜져 있어야 작동합니다.';
    fileWarning.classList.remove('hidden');
    setStatus(`${sourceName} ${tripTypeName} 검색 준비 완료. 검색하려면 로컬 서버가 실행 중이어야 합니다.`);
    return;
  }

  if (IS_STATIC_HOSTING) {
    runtimeChip.textContent = '정적 호스팅';
    runtimeWarningText.textContent = 'GitHub Pages에서는 화면 미리보기만 가능합니다. 실제 검색은 로컬 서버 또는 별도 백엔드가 필요합니다.';
    fileWarning.classList.remove('hidden');
    setStatus('GitHub Pages에서는 크롤러를 실행할 수 없습니다. 로컬 서버에서 검색해 주세요.', true);
    return;
  }

  runtimeChip.textContent = '서버 연결됨';
  fileWarning.classList.add('hidden');
  setStatus(`${sourceName} ${tripTypeName} 검색 준비 완료.`);
}

function syncTripTypeFields() {
  const isOneWay = selectedTripType() === 'oneway';
  form.elements.returnDate.required = !isOneWay;
  form.elements.returnDate.disabled = isOneWay;
  returnDateField.classList.toggle('return-date-disabled', isOneWay);
  inboundHeader.textContent = isOneWay ? '비고' : '오는 편';
  validateDateOrder();
  updateRuntimeState();
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? '수집 중...' : '가격 수집 시작';
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle('error', isError);
}

function formatPrice(value) {
  if (String(value || '').includes('$')) return value;
  const number = Number(String(value || '').replace(/,/g, ''));
  if (!Number.isFinite(number)) return value || '-';
  return `${number.toLocaleString('ko-KR')}원`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function isExternalUrl(value) {
  return /^https?:\/\//.test(String(value || ''));
}

function priceCell(row) {
  const formattedPrice = escapeHtml(formatPrice(row.price));
  const bookingUrl = row.booking_url || row.bookingUrl || '';

  if (!isExternalUrl(bookingUrl)) {
    return formattedPrice;
  }

  return `<a class="price-link" href="${escapeHtml(bookingUrl)}" target="_blank" rel="noopener noreferrer" title="해당 사이트에서 예매 페이지 열기">${formattedPrice}</a>`;
}

function routeText(row, direction) {
  if (direction === 'inbound' && row.trip_type === 'oneway') {
    return '편도 여정';
  }

  const prefix = direction === 'outbound' ? 'outbound' : 'inbound';
  const depTime = row[`${prefix}_dep_time`] || '-';
  const arrTime = row[`${prefix}_arr_time`] || '-';
  const depCode = row[`${prefix}_dep_code`] || '-';
  const arrCode = row[`${prefix}_arr_code`] || '-';
  const info = row[`${prefix}_info`] || '';
  return `${depCode} ${depTime} -> ${arrCode} ${arrTime}${info ? `\n${info}` : ''}`;
}

function renderRows(rows) {
  resultCount.textContent = `${rows.length}건`;

  if (!rows.length) {
    resultsBody.innerHTML = '<tr><td colspan="5" class="empty-cell">수집된 결과가 없습니다.</td></tr>';
    return;
  }

  resultsBody.innerHTML = rows.map((row) => `
    <tr>
      <td><span class="source-badge">${escapeHtml(sourceLabel(row.source))}</span></td>
      <td class="price">${priceCell(row)}</td>
      <td>${escapeHtml(row.airline || '-')}</td>
      <td class="route">${escapeHtml(routeText(row, 'outbound'))}</td>
      <td class="route">${escapeHtml(routeText(row, 'inbound'))}</td>
    </tr>
  `).join('');
}

function renderLog(log) {
  logOutput.textContent = log || '실행 로그가 없습니다.';
}

function absoluteDownloadUrl(downloadUrl) {
  if (!downloadUrl) return '#';
  if (/^https?:\/\//.test(downloadUrl)) return downloadUrl;
  return `${API_BASE}${downloadUrl}`;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (IS_STATIC_HOSTING) {
    setStatus('GitHub Pages는 정적 호스팅이라 Python 크롤러와 Node 서버를 실행할 수 없습니다. 로컬 서버에서 검색해 주세요.', true);
    return;
  }

  const payload = {
    source: form.elements.source.value,
    tripType: selectedTripType(),
    dep3: form.elements.dep3.value,
    arr3: form.elements.arr3.value,
    depart: toYYYYMMDD(form.elements.depart.value),
    returnDate: selectedTripType() === 'roundtrip' ? toYYYYMMDD(form.elements.returnDate.value) : '',
    items: Number(form.elements.items.value),
    headless: form.elements.headless.checked,
  };

  if (!validateDepartDate()) {
    form.reportValidity();
    setStatus('출발일은 오늘보다 빠를 수 없습니다.', true);
    return;
  }

  if (!validateDateOrder()) {
    form.reportValidity();
    setStatus('복귀일은 출발일보다 늦어야 합니다.', true);
    return;
  }

  downloadLink.classList.add('hidden');
  renderRows([]);
  renderLog('');
  setLoading(true);
  const sourceName = selectedSourceName();
  const tripTypeName = selectedTripTypeName();
  const loadingMessage = payload.source === 'all'
    ? `네이버 항공권, Google Flights, Trip.com ${tripTypeName} 항공권을 동시에 조회하고 있습니다. 보통 30초 이상 걸립니다.`
    : `브라우저를 열어 ${sourceName} ${tripTypeName} 항공권을 조회하고 있습니다. 보통 20초 이상 걸립니다.`;
  setStatus(loadingMessage);

  try {
    const response = await fetch(`${API_BASE}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '검색 요청이 실패했습니다.');
    }

    renderRows(data.rows || []);
    renderLog(data.log || '');
    downloadLink.href = absoluteDownloadUrl(data.downloadUrl);
    downloadLink.download = data.filename;
    downloadLink.classList.remove('hidden');
    const failureText = data.failures?.length
      ? ` 일부 실패: ${data.failures.map((failure) => failure.label).join(', ')}`
      : '';
    setStatus(`${sourceName} ${tripTypeName}에서 ${data.count}건 수집 완료. CSV 파일이 result 폴더에 저장되었습니다.${failureText}`);
  } catch (error) {
    const hint = window.location.protocol === 'file:'
      ? ' 로컬 서버를 켠 뒤 다시 시도하거나 http://127.0.0.1:8080 주소로 열어 주세요.'
      : '';
    setStatus(`${error.message}${hint}`, true);
    renderLog(error.stack || error.message);
  } finally {
    setLoading(false);
  }
});

toggleLog.addEventListener('click', () => {
  const hidden = logOutput.classList.toggle('hidden');
  toggleLog.textContent = hidden ? '보기' : '숨기기';
});

for (const name of ['dep3', 'arr3']) {
  form.elements[name].addEventListener('input', (event) => {
    event.target.value = event.target.value.toUpperCase();
  });
}

for (const input of form.elements.source) {
  input.addEventListener('change', updateRuntimeState);
}

for (const input of form.elements.tripType) {
  input.addEventListener('change', syncTripTypeFields);
}

form.elements.depart.addEventListener('change', syncReturnDateMin);
form.elements.returnDate.addEventListener('change', validateDateOrder);

applyQueryParams();
const initialNotice = setInitialDates();
syncTripTypeFields();
if (initialNotice) {
  setStatus(initialNotice);
}
