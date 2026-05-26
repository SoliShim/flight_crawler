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
const primaryHeader = document.querySelector('#primary-header');
const summaryTitle = document.querySelector('#summary-title');
const bestGrid = document.querySelector('#best-grid');
const apiSettingsForm = document.querySelector('#api-settings-form');
const apiBaseInput = document.querySelector('#api-base-input');
const apiKeyInput = document.querySelector('#api-key-input');
const apiSettingsStatus = document.querySelector('#api-settings-status');
const apiTestButton = document.querySelector('#api-test-button');
const apiClearButton = document.querySelector('#api-clear-button');
const modeTabs = [...document.querySelectorAll('.mode-tab')];
const modeFields = [...document.querySelectorAll('.mode-field')];

const LOCAL_SERVER = 'http://127.0.0.1:8888';
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const IS_LOCAL_SERVER = LOCAL_HOSTS.has(window.location.hostname);
const IS_FILE_MODE = window.location.protocol === 'file:';
const IS_STATIC_HOSTING = !IS_FILE_MODE && !IS_LOCAL_SERVER;
const query = new URLSearchParams(window.location.search);
const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''));
const API_BASE_STORAGE_KEY = 'flightCrawlerApiBase';
const API_KEY_STORAGE_KEY = 'flightCrawlerApiKey';
const MODE_LABELS = {
  route: '노선 최저가',
  explore: '여행지 추천',
  dates: '저렴한 날짜',
};
const SUBMIT_LABELS = {
  route: '노선 최저가 찾기',
  explore: '저렴한 여행지 추천받기',
  dates: '가장 저렴한 날짜 찾기',
};

const queryApiBase = normalizeApiBase(query.get('apiBase') || query.get('api'));
const storedApiBase = normalizeApiBase(localStorage.getItem(API_BASE_STORAGE_KEY));
const fragmentApiKey = String(fragment.get('apiKey') || '').trim();
let apiBase = queryApiBase || storedApiBase || defaultApiBase();
let apiKey = fragmentApiKey || (queryApiBase && queryApiBase !== storedApiBase ? '' : localStorage.getItem(API_KEY_STORAGE_KEY) || '');
let currentMode = ['route', 'explore', 'dates'].includes(query.get('mode')) ? query.get('mode') : 'route';

if (queryApiBase) {
  localStorage.setItem(API_BASE_STORAGE_KEY, queryApiBase);
}

if (fragmentApiKey) {
  localStorage.setItem(API_KEY_STORAGE_KEY, fragmentApiKey);
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
}

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

function sanitizeInputDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? value : '';
}

function displayDate(value) {
  const text = String(value || '');
  if (/^\d{8}$/.test(text)) {
    return `${text.slice(0, 4)}.${text.slice(4, 6)}.${text.slice(6, 8)}`;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text.replaceAll('-', '.');
  }
  return text || '-';
}

function setInitialDates() {
  const today = todayInputDate();
  const defaultDepart = toInputDate(addDays(new Date(), 1));
  const defaultReturn = toInputDate(addDays(new Date(), 4));
  const defaultEnd = toInputDate(addDays(new Date(), 14));
  const queryDepart = sanitizeInputDate(query.get('depart'));
  const queryReturn = sanitizeInputDate(query.get('returnDate'));
  let notice = '';

  for (const input of [form.elements.depart, form.elements.startDate]) {
    input.min = today;
  }

  form.elements.depart.value = queryDepart || defaultDepart;
  form.elements.returnDate.value = queryReturn || defaultReturn;
  form.elements.startDate.value = sanitizeInputDate(query.get('startDate')) || defaultDepart;
  form.elements.endDate.value = sanitizeInputDate(query.get('endDate')) || defaultEnd;

  if (form.elements.depart.value < today || form.elements.startDate.value < today) {
    form.elements.depart.value = defaultDepart;
    form.elements.startDate.value = defaultDepart;
    notice = 'URL의 지난 날짜를 기본 날짜로 조정했습니다.';
  }

  syncDateRules();
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

  for (const [name, min, max] of [
    ['items', 1, 100],
    ['exploreItems', 1, 20],
    ['dateItems', 1, 20],
    ['limit', 1, 20],
    ['durationDays', 1, 30],
    ['maxDates', 1, 31],
  ]) {
    const value = Number(query.get(name));
    if (Number.isInteger(value) && value >= min && value <= max) {
      form.elements[name].value = String(value);
    }
  }

  const destinations = String(query.get('destinations') || '').trim().toUpperCase();
  if (destinations) {
    form.elements.destinations.value = destinations;
  }

  const headless = query.get('headless');
  if (headless === 'false') {
    form.elements.headless.checked = false;
  }
}

function selectedSourceName() {
  const names = {
    naver: '네이버',
    google: 'Google Flights',
    trip: 'Trip.com',
    all: '전부 검색',
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
    all: '전부',
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
  const modeName = MODE_LABELS[currentMode];
  const activeApiBase = currentApiBase();

  if (IS_FILE_MODE) {
    runtimeChip.textContent = '파일 모드';
    runtimeWarningText.textContent = '이 화면은 파일로 열렸습니다. 검색은 로컬 서버 또는 API 서버가 켜져 있어야 작동합니다.';
    fileWarning.classList.remove('hidden');
    setStatus(`${modeName} 준비 완료. ${sourceName} ${tripTypeName} 검색을 실행하려면 API 서버가 필요합니다.`);
    return;
  }

  if (IS_STATIC_HOSTING) {
    if (activeApiBase) {
      runtimeChip.textContent = '원격 API 설정됨';
      runtimeWarningText.textContent = `GitHub Pages 화면에서 ${activeApiBase} API 서버로 검색합니다.`;
      fileWarning.classList.remove('hidden');
      setStatus(`${modeName} 준비 완료. 맥미니 API 서버가 실행 중이어야 합니다.`);
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
  setStatus(`${modeName} 준비 완료. ${sourceName} ${tripTypeName}으로 검색합니다.`);
}

function setMode(mode) {
  currentMode = mode;
  modeTabs.forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  modeFields.forEach((field) => {
    const visible = field.classList.contains(`${mode}-field`);
    field.classList.toggle('is-hidden', !visible);
  });

  submitButton.textContent = SUBMIT_LABELS[mode];
  primaryHeader.textContent = mode === 'explore' ? '여행지' : mode === 'dates' ? '날짜' : '플랫폼';
  summaryTitle.textContent = `${MODE_LABELS[mode]} 결과`;
  downloadLink.classList.add('hidden');
  renderRows([]);
  renderBest([]);
  syncRequiredFields();
  syncDateRules();
  updateRuntimeState();
}

function syncRequiredFields() {
  const isRoute = currentMode === 'route';
  const isExplore = currentMode === 'explore';
  const isDates = currentMode === 'dates';
  const isRoundtrip = selectedTripType() === 'roundtrip';

  form.elements.arr3.required = isRoute || isDates;
  form.elements.depart.required = isRoute || isExplore;
  form.elements.returnDate.required = (isRoute || isExplore) && isRoundtrip;
  form.elements.startDate.required = isDates;
  form.elements.endDate.required = isDates;
  form.elements.returnDate.disabled = !((isRoute || isExplore) && isRoundtrip);
  returnDateField.classList.toggle('return-date-disabled', !isRoundtrip);
  inboundHeader.textContent = isRoundtrip ? '오는 편' : '비고';
}

function syncDateRules() {
  const today = todayInputDate();
  const depart = form.elements.depart.value;
  const startDate = form.elements.startDate.value;

  form.elements.depart.min = today;
  form.elements.startDate.min = today;
  form.elements.returnDate.min = depart || today;
  form.elements.endDate.min = startDate || today;
  validateDates();
}

function validateDates() {
  const today = todayInputDate();
  const tripType = selectedTripType();
  const depart = form.elements.depart.value;
  const returnDate = form.elements.returnDate.value;
  const startDate = form.elements.startDate.value;
  const endDate = form.elements.endDate.value;

  form.elements.depart.setCustomValidity(depart && depart < today ? '출발일은 오늘보다 빠를 수 없습니다.' : '');
  form.elements.startDate.setCustomValidity(startDate && startDate < today ? '시작일은 오늘보다 빠를 수 없습니다.' : '');
  form.elements.returnDate.setCustomValidity(tripType === 'roundtrip' && depart && returnDate && depart >= returnDate ? '복귀일은 출발일보다 늦어야 합니다.' : '');
  form.elements.endDate.setCustomValidity(startDate && endDate && startDate > endDate ? '종료일은 시작일보다 늦거나 같아야 합니다.' : '');

  return form.checkValidity();
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? '수집 중...' : SUBMIT_LABELS[currentMode];
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle('error', isError);
}

function formatPrice(value) {
  if (String(value || '').includes('$')) return value;
  const number = Number(String(value || '').replace(/[^\d.]/g, ''));
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
    resultsBody.innerHTML = '<tr><td colspan="5" class="empty-cell">아직 수집된 결과가 없습니다.</td></tr>';
    return;
  }

  if (currentMode === 'route') {
    resultsBody.innerHTML = rows.map((row) => `
      <tr>
        <td><span class="source-badge">${escapeHtml(sourceLabel(row.source))}</span></td>
        <td class="price">${priceCell(row)}</td>
        <td>${escapeHtml(row.airline || '-')}</td>
        <td class="route">${escapeHtml(routeText(row, 'outbound'))}</td>
        <td class="route">${escapeHtml(routeText(row, 'inbound'))}</td>
      </tr>
    `).join('');
    return;
  }

  resultsBody.innerHTML = rows.map((row) => {
    const primary = currentMode === 'explore'
      ? `${row.destination || row.arr3 || '-'}`
      : `${displayDate(row.depart)}${row.returnDate ? ` - ${displayDate(row.returnDate)}` : ''}`;
    const inbound = row.inbound || row.status || '-';

    return `
      <tr>
        <td><span class="source-badge">${escapeHtml(primary)}</span></td>
        <td class="price">${priceCell(row)}</td>
        <td>${escapeHtml(row.airline || row.status || '-')}</td>
        <td class="route">${escapeHtml(row.outbound || '-')}</td>
        <td class="route">${escapeHtml(inbound)}</td>
      </tr>
    `;
  }).join('');
}

function renderBest(rows) {
  const pricedRows = rows.filter((row) => Number.isFinite(Number(row.priceAmount)) || row.price);
  const bestRows = currentMode === 'route' ? rows.slice(0, 3) : pricedRows.slice(0, 3);

  if (!bestRows.length) {
    bestGrid.innerHTML = '<div class="empty-state">검색 결과가 생기면 가장 저렴한 항공권과 비교 후보가 여기에 표시됩니다.</div>';
    return;
  }

  bestGrid.innerHTML = bestRows.map((row, index) => {
    const title = currentMode === 'route'
      ? `${sourceLabel(row.source)} ${index + 1}위`
      : currentMode === 'explore'
        ? row.destination || row.arr3 || `${index + 1}위`
        : `${displayDate(row.depart)} 출발`;
    const meta = currentMode === 'route'
      ? `${form.elements.dep3.value.toUpperCase()} -> ${form.elements.arr3.value.toUpperCase()}`
      : currentMode === 'explore'
        ? `${form.elements.dep3.value.toUpperCase()} -> ${row.arr3 || ''}`
        : `${form.elements.dep3.value.toUpperCase()} -> ${form.elements.arr3.value.toUpperCase()}`;
    const route = currentMode === 'route' ? routeText(row, 'outbound') : row.outbound;

    return `
      <article class="best-card">
        <span>${escapeHtml(meta)}</span>
        <strong>${escapeHtml(title)}</strong>
        <p class="best-price">${priceCell(row)}</p>
        <small>${escapeHtml(row.airline || route || '-')}</small>
      </article>
    `;
  }).join('');
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

function splitDestinations(value) {
  return String(value || '')
    .toUpperCase()
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildPayload() {
  const base = {
    source: form.elements.source.value,
    tripType: selectedTripType(),
    dep3: form.elements.dep3.value,
    headless: form.elements.headless.checked,
  };

  if (currentMode === 'route') {
    return {
      endpoint: '/api/search',
      payload: {
        ...base,
        arr3: form.elements.arr3.value,
        depart: toYYYYMMDD(form.elements.depart.value),
        returnDate: selectedTripType() === 'roundtrip' ? toYYYYMMDD(form.elements.returnDate.value) : '',
        items: Number(form.elements.items.value),
      },
    };
  }

  if (currentMode === 'explore') {
    return {
      endpoint: '/api/explore',
      payload: {
        ...base,
        depart: toYYYYMMDD(form.elements.depart.value),
        returnDate: selectedTripType() === 'roundtrip' ? toYYYYMMDD(form.elements.returnDate.value) : '',
        destinations: splitDestinations(form.elements.destinations.value),
        limit: Number(form.elements.limit.value),
        items: Number(form.elements.exploreItems.value),
      },
    };
  }

  return {
    endpoint: '/api/cheapest-dates',
    payload: {
      ...base,
      arr3: form.elements.arr3.value,
      startDate: toYYYYMMDD(form.elements.startDate.value),
      endDate: toYYYYMMDD(form.elements.endDate.value),
      durationDays: Number(form.elements.durationDays.value),
      maxDates: Number(form.elements.maxDates.value),
      items: Number(form.elements.dateItems.value),
    },
  };
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
      : `API 서버 연결이 정상입니다. 사용 가능한 소스: ${(data.sources || []).map(sourceLabel).join(', ')}`);
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

  syncRequiredFields();
  if (!validateDates() || !form.reportValidity()) {
    setStatus('입력한 검색 조건을 다시 확인해 주세요.', true);
    return;
  }

  const { endpoint, payload } = buildPayload();
  downloadLink.classList.add('hidden');
  renderRows([]);
  renderBest([]);
  renderLog('');
  setLoading(true);

  const sourceName = selectedSourceName();
  const tripTypeName = selectedTripTypeName();
  const loadingMessages = {
    route: `${sourceName}에서 ${tripTypeName} 항공권을 조회하고 있습니다. 보통 20초 이상 걸립니다.`,
    explore: `여러 여행지 후보를 순서대로 조회하고 있습니다. 후보 수가 많으면 몇 분 걸릴 수 있습니다.`,
    dates: `여러 날짜 후보를 순서대로 조회하고 있습니다. 검사 날짜 수가 많으면 몇 분 걸릴 수 있습니다.`,
  };
  setStatus(loadingMessages[currentMode]);

  try {
    const response = await fetch(`${activeApiBase}${endpoint}`, {
      method: 'POST',
      headers: apiHeaders(true),
      body: JSON.stringify(payload),
    });
    const data = await readJsonResponse(response);

    if (!response.ok) {
      throw new Error(data.error || '검색 요청이 실패했습니다.');
    }

    const rows = data.rows || [];
    renderRows(rows);
    renderBest(rows);
    renderLog(data.log || '');
    downloadLink.href = absoluteDownloadUrl(data.downloadUrl);
    downloadLink.download = data.filename;
    downloadLink.classList.remove('hidden');
    setStatus(`${MODE_LABELS[currentMode]}에서 ${data.count}건 수집 완료. CSV 파일이 result 폴더에 저장되었습니다.`);
  } catch (error) {
    const hint = IS_STATIC_HOSTING
      ? ' 맥미니 API 서버 주소, API 키, Cloudflare Tunnel 상태를 확인해 주세요.'
      : IS_FILE_MODE
        ? ' 로컬 서버를 켠 뒤 다시 시도하거나 자동 실행 파일이 열어준 GitHub Pages 주소를 사용해 주세요.'
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
  input.addEventListener('change', () => {
    syncRequiredFields();
    syncDateRules();
    updateRuntimeState();
  });
}

for (const input of [form.elements.depart, form.elements.returnDate, form.elements.startDate, form.elements.endDate]) {
  input.addEventListener('change', syncDateRules);
}

modeTabs.forEach((tab) => {
  tab.addEventListener('click', () => setMode(tab.dataset.mode));
});

applyQueryParams();
syncApiSettingsUi();
const initialNotice = setInitialDates();
setMode(currentMode);
if (initialNotice) {
  setStatus(initialNotice);
}
