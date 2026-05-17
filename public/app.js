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
const apiSettingsForm = document.querySelector('#api-settings-form');
const apiBaseInput = document.querySelector('#api-base-input');
const apiKeyInput = document.querySelector('#api-key-input');
const apiSettingsStatus = document.querySelector('#api-settings-status');
const apiTestButton = document.querySelector('#api-test-button');
const apiClearButton = document.querySelector('#api-clear-button');

const LOCAL_SERVER = 'http://127.0.0.1:8080';
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const IS_LOCAL_SERVER = LOCAL_HOSTS.has(window.location.hostname);
const IS_FILE_MODE = window.location.protocol === 'file:';
const IS_STATIC_HOSTING = !IS_FILE_MODE && !IS_LOCAL_SERVER;
const query = new URLSearchParams(window.location.search);
const API_BASE_STORAGE_KEY = 'flightCrawlerApiBase';
const API_KEY_STORAGE_KEY = 'flightCrawlerApiKey';

let apiBase = normalizeApiBase(query.get('api') || localStorage.getItem(API_BASE_STORAGE_KEY) || defaultApiBase());
let apiKey = localStorage.getItem(API_KEY_STORAGE_KEY) || '';

function defaultApiBase() {
  if (IS_FILE_MODE) return LOCAL_SERVER;
  return '';
}

function normalizeApiBase(value) {
  const text = String(value || '').trim().replace(/\/+$/, '');
  if (!text) return '';

  try {
    const url = new URL(text);
    return ['http:', 'https:'].includes(url.protocol) ? url.toString().replace(/\/+$/, '') : '';
  } catch {
    return '';
  }
}

function currentApiBase() {
  return apiBase || defaultApiBase();
}

function apiHeaders(includeJson = false) {
  const headers = {};
  if (includeJson) headers['Content-Type'] = 'application/json';
  if (apiKey) headers['X-Flight-Crawler-Key'] = apiKey;
  return headers;
}

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

function syncApiSettingsUi() {
  apiBaseInput.value = apiBase;
  apiKeyInput.value = apiKey;

  if (IS_LOCAL_SERVER) {
    apiSettingsStatus.textContent = '현재 서버 사용';
  } else if (currentApiBase()) {
    apiSettingsStatus.textContent = apiKey ? '저장됨' : 'API 키 확인 필요';
  } else {
    apiSettingsStatus.textContent = '설정 필요';
  }
}

function updateRuntimeState() {
  const sourceName = selectedSourceName();
  const tripTypeName = selectedTripTypeName();
  const activeApiBase = currentApiBase();

  if (IS_FILE_MODE) {
    runtimeChip.textContent = '파일 모드';
    runtimeWarningText.textContent = '이 화면은 파일로 열렸습니다. 검색은 로컬 서버 또는 API 서버가 켜져 있어야 작동합니다.';
    fileWarning.classList.remove('hidden');
    setStatus(`${sourceName} ${tripTypeName} 검색 준비 완료. 검색하려면 API 서버가 실행 중이어야 합니다.`);
    return;
  }

  if (IS_STATIC_HOSTING) {
    if (activeApiBase) {
      runtimeChip.textContent = '원격 API 설정됨';
      runtimeWarningText.textContent = `GitHub Pages 화면에서 ${activeApiBase} API 서버로 검색합니다.`;
      fileWarning.classList.remove('hidden');
      setStatus(`${sourceName} ${tripTypeName} 검색 준비 완료. 맥미니 API 서버가 실행 중이어야 합니다.`);
      return;
    }

    runtimeChip.textContent = 'API 설정 필요';
    runtimeWarningText.textContent = 'GitHub Pages에서 검색하려면 맥미니 API 서버 주소와 API 키를 저장해야 합니다.';
    fileWarning.classList.remove('hidden');
    setStatus('API 서버 주소를 저장한 뒤 검색해 주세요.', true);
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
  return `${currentApiBase()}${downloadUrl}`;
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

apiSettingsForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const nextApiBase = normalizeApiBase(apiBaseInput.value);

  if (apiBaseInput.value.trim() && !nextApiBase) {
    apiBaseInput.setCustomValidity('https://로 시작하는 API 서버 주소를 입력해 주세요.');
    apiBaseInput.reportValidity();
    return;
  }

  apiBaseInput.setCustomValidity('');
  apiBase = nextApiBase;
  apiKey = apiKeyInput.value.trim();

  if (apiBase) {
    localStorage.setItem(API_BASE_STORAGE_KEY, apiBase);
  } else {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
  }

  if (apiKey) {
    localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
  } else {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }

  syncApiSettingsUi();
  updateRuntimeState();
  setStatus('API 서버 설정을 저장했습니다.');
});

apiClearButton.addEventListener('click', () => {
  apiBase = defaultApiBase();
  apiKey = '';
  localStorage.removeItem(API_BASE_STORAGE_KEY);
  localStorage.removeItem(API_KEY_STORAGE_KEY);
  syncApiSettingsUi();
  updateRuntimeState();
  setStatus('API 서버 설정을 삭제했습니다.');
});

apiTestButton.addEventListener('click', async () => {
  const activeApiBase = currentApiBase();
  if ((IS_STATIC_HOSTING || IS_FILE_MODE) && !activeApiBase) {
    setStatus('API 서버 주소를 저장한 뒤 연결 확인을 실행해 주세요.', true);
    return;
  }

  apiTestButton.disabled = true;
  apiTestButton.textContent = '확인 중...';
  setStatus('API 서버 연결을 확인하고 있습니다.');

  try {
    const response = await fetch(`${activeApiBase}/api/health`, {
      headers: apiHeaders(),
    });
    const data = await readJsonResponse(response);

    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'API 서버 연결 확인에 실패했습니다.');
    }

    setStatus(data.apiKeyRequired && !apiKey
      ? 'API 서버는 연결됐지만 검색하려면 API 키가 필요합니다.'
      : 'API 서버 연결이 정상입니다.');
  } catch (error) {
    setStatus(`${error.message} Cloudflare Tunnel 주소와 맥미니 서버 실행 상태를 확인해 주세요.`, true);
  } finally {
    apiTestButton.disabled = false;
    apiTestButton.textContent = '연결 확인';
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const activeApiBase = currentApiBase();
  if ((IS_STATIC_HOSTING || IS_FILE_MODE) && !activeApiBase) {
    setStatus('API 서버 주소를 저장한 뒤 검색해 주세요.', true);
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
    const response = await fetch(`${activeApiBase}/api/search`, {
      method: 'POST',
      headers: apiHeaders(true),
      body: JSON.stringify(payload),
    });
    const data = await readJsonResponse(response);

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
    const hint = IS_STATIC_HOSTING
      ? ' 맥미니 API 서버 주소, API 키, Cloudflare Tunnel 상태를 확인해 주세요.'
      : IS_FILE_MODE
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
syncApiSettingsUi();
const initialNotice = setInitialDates();
syncTripTypeFields();
if (initialNotice) {
  setStatus(initialNotice);
}
