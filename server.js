const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');

const express = require('express');

const app = express();
const PORT = Number(process.env.PORT || 8888);
const MAX_PORT_ATTEMPTS = Number(process.env.PORT_ATTEMPTS || 100);
const HOST = process.env.HOST || '127.0.0.1';
const ROOT_DIR = __dirname;
const RESULT_DIR = path.join(ROOT_DIR, 'result');
const PYTHON_BIN = process.env.PYTHON_BIN || path.join(ROOT_DIR, '.venv', 'bin', 'python');
const API_KEY = process.env.API_KEY || '';
const DEFAULT_ALLOWED_ORIGINS = [
  'https://solishim.github.io',
  'http://localhost:8888',
  'http://127.0.0.1:8888',
];
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || DEFAULT_ALLOWED_ORIGINS.join(','))
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);
const ALL_SEARCH_SOURCES = ['naver', 'google', 'trip'];
const SOURCE_LABELS = {
  naver: '네이버 항공권',
  google: 'Google Flights',
  trip: 'Trip.com',
};
const DESTINATION_PRESETS = [
  { code: 'NRT', city: '도쿄', region: '일본' },
  { code: 'KIX', city: '오사카', region: '일본' },
  { code: 'FUK', city: '후쿠오카', region: '일본' },
  { code: 'CTS', city: '삿포로', region: '일본' },
  { code: 'TPE', city: '타이베이', region: '동아시아' },
  { code: 'HKG', city: '홍콩', region: '동아시아' },
  { code: 'KHH', city: '가오슝', region: '동아시아' },
  { code: 'MNL', city: '마닐라', region: '동남아' },
  { code: 'BKK', city: '방콕', region: '동남아' },
  { code: 'DAD', city: '다낭', region: '동남아' },
  { code: 'SGN', city: '호치민', region: '동남아' },
  { code: 'SIN', city: '싱가포르', region: '동남아' },
  { code: 'KUL', city: '쿠알라룸푸르', region: '동남아' },
  { code: 'CEB', city: '세부', region: '동남아' },
  { code: 'GUM', city: '괌', region: '태평양' },
  { code: 'LAX', city: '로스앤젤레스', region: '미주' },
  { code: 'JFK', city: '뉴욕', region: '미주' },
  { code: 'CDG', city: '파리', region: '유럽' },
];

app.use((req, res, next) => {
  const origin = req.get('Origin');
  const originAllowed = !origin || ALLOWED_ORIGINS.includes('*') || ALLOWED_ORIGINS.includes(origin);

  if (originAllowed && origin) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  } else if (ALLOWED_ORIGINS.includes('*')) {
    res.setHeader('Access-Control-Allow-Origin', '*');
  }

  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Flight-Crawler-Key');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');

  if (req.method === 'OPTIONS') {
    res.sendStatus(originAllowed ? 204 : 403);
    return;
  }

  if (!originAllowed) {
    res.status(403).json({ error: '허용되지 않은 출처입니다.' });
    return;
  }

  next();
});

app.use(express.json());
app.use(express.static(path.join(ROOT_DIR, 'public')));
app.use('/result', express.static(RESULT_DIR));

function requireApiKey(req, res, next) {
  if (!API_KEY) {
    next();
    return;
  }

  const providedKey = req.get('X-Flight-Crawler-Key') || '';
  if (providedKey !== API_KEY) {
    res.status(401).json({ error: 'API 키가 올바르지 않습니다.' });
    return;
  }

  next();
}

function normalizeAirport(value, fieldName) {
  const airport = String(value || '').trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(airport)) {
    throw new Error(`${fieldName} 공항 코드는 알파벳 3자리여야 합니다.`);
  }
  return airport;
}

function normalizeDate(value, fieldName) {
  const date = String(value || '').trim();
  if (!/^\d{8}$/.test(date)) {
    throw new Error(`${fieldName} 날짜는 YYYYMMDD 형식이어야 합니다.`);
  }
  return date;
}

function normalizeSource(value) {
  const source = String(value || 'naver').trim().toLowerCase();
  if (![...ALL_SEARCH_SOURCES, 'all'].includes(source)) {
    throw new Error('검색 플랫폼은 네이버 항공권, Google Flights, Trip.com, 전부 검색하기 중 하나여야 합니다.');
  }
  return source;
}

function normalizeTripType(value) {
  const tripType = String(value || 'roundtrip').trim().toLowerCase();
  if (!['roundtrip', 'oneway'].includes(tripType)) {
    throw new Error('여정 방식은 왕복 또는 편도 중 하나여야 합니다.');
  }
  return tripType;
}

function todayYYYYMMDD() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

function parseYYYYMMDD(value) {
  const text = normalizeDate(value, '날짜');
  return new Date(`${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}T00:00:00`);
}

function formatYYYYMMDD(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

function addDaysYYYYMMDD(value, days) {
  const date = parseYYYYMMDD(value);
  date.setDate(date.getDate() + days);
  return formatYYYYMMDD(date);
}

function daysBetweenYYYYMMDD(start, end) {
  const startDate = parseYYYYMMDD(start);
  const endDate = parseYYYYMMDD(end);
  return Math.round((endDate - startDate) / 86400000);
}

function parseCsvLine(line) {
  const values = [];
  let current = '';
  let quoted = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"' && quoted && next === '"') {
      current += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === ',' && !quoted) {
      values.push(current);
      current = '';
    } else {
      current += char;
    }
  }

  values.push(current);
  return values;
}

function parseCsv(content) {
  const normalized = content.replace(/^\uFEFF/, '').trim();
  if (!normalized) return [];

  const lines = normalized.split(/\r?\n/);
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).filter(Boolean).map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] || '']));
  });
}

function summarizeFailure(logText) {
  const detail = String(logText || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-1)[0] || '';
  return detail.replace(/^[A-Za-z]+Error:\s*/, '');
}

function sourceFilenamePrefix(source) {
  if (source === 'google') return 'google_';
  if (source === 'trip') return 'trip_';
  if (source === 'all') return 'all_';
  return '';
}

function normalizeSearchInput(input) {
  const source = normalizeSource(input.source);
  const tripType = normalizeTripType(input.tripType || input.trip_type);
  const dep3 = normalizeAirport(input.dep3, '출발');
  const arr3 = normalizeAirport(input.arr3, '도착');
  const depart = normalizeDate(input.depart, '출발');
  const returnDate = tripType === 'roundtrip' ? normalizeDate(input.returnDate, '복귀') : '';
  const items = Number(input.items || 10);
  const headless = input.headless !== false;

  if (depart < todayYYYYMMDD()) {
    throw new Error('출발일은 오늘보다 빠를 수 없습니다.');
  }
  if (tripType === 'roundtrip' && depart >= returnDate) {
    throw new Error('복귀일은 출발일보다 늦어야 합니다.');
  }
  if (!Number.isInteger(items) || items < 1 || items > 100) {
    throw new Error('수집 개수는 1부터 100 사이여야 합니다.');
  }

  return {
    source,
    tripType,
    dep3,
    arr3,
    depart,
    returnDate,
    items,
    headless,
  };
}

function destinationLabel(code) {
  const preset = DESTINATION_PRESETS.find((destination) => destination.code === code);
  return preset ? `${preset.city} (${preset.code})` : code;
}

function normalizeDestinationList(value, dep3, limit) {
  const rawItems = Array.isArray(value)
    ? value
    : String(value || '')
      .split(/[\s,]+/)
      .filter(Boolean);
  const candidates = rawItems.length
    ? rawItems
    : DESTINATION_PRESETS.map((destination) => destination.code);
  const normalized = [];

  for (const candidate of candidates) {
    const code = String(candidate || '').trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(code) && code !== dep3 && !normalized.includes(code)) {
      normalized.push(code);
    }
  }

  if (!normalized.length) {
    throw new Error('추천할 도착 공항 후보가 없습니다.');
  }

  return normalized.slice(0, limit);
}

function normalizeExploreInput(input) {
  const source = normalizeSource(input.source);
  const tripType = normalizeTripType(input.tripType || input.trip_type);
  const dep3 = normalizeAirport(input.dep3, '출발');
  const depart = normalizeDate(input.depart, '출발');
  const returnDate = tripType === 'roundtrip' ? normalizeDate(input.returnDate, '복귀') : '';
  const items = Number(input.items || 3);
  const limit = Number(input.limit || 8);
  const headless = input.headless !== false;

  if (depart < todayYYYYMMDD()) {
    throw new Error('출발일은 오늘보다 빠를 수 없습니다.');
  }
  if (tripType === 'roundtrip' && depart >= returnDate) {
    throw new Error('복귀일은 출발일보다 늦어야 합니다.');
  }
  if (!Number.isInteger(items) || items < 1 || items > 20) {
    throw new Error('목적지별 수집 개수는 1부터 20 사이여야 합니다.');
  }
  if (!Number.isInteger(limit) || limit < 1 || limit > 20) {
    throw new Error('추천 목적지 수는 1부터 20 사이여야 합니다.');
  }

  return {
    source,
    tripType,
    dep3,
    depart,
    returnDate,
    items,
    limit,
    headless,
    destinations: normalizeDestinationList(input.destinations || input.arr3s, dep3, limit),
  };
}

function normalizeDateScanInput(input) {
  const source = normalizeSource(input.source);
  const tripType = normalizeTripType(input.tripType || input.trip_type);
  const dep3 = normalizeAirport(input.dep3, '출발');
  const arr3 = normalizeAirport(input.arr3, '도착');
  const startDate = normalizeDate(input.startDate || input.departStart, '시작');
  const endDate = normalizeDate(input.endDate || input.departEnd, '종료');
  const durationDays = Number(input.durationDays || 3);
  const items = Number(input.items || 3);
  const maxDates = Number(input.maxDates || 14);
  const headless = input.headless !== false;

  if (startDate < todayYYYYMMDD()) {
    throw new Error('시작일은 오늘보다 빠를 수 없습니다.');
  }
  if (startDate > endDate) {
    throw new Error('종료일은 시작일보다 늦거나 같아야 합니다.');
  }
  if (!Number.isInteger(durationDays) || durationDays < 1 || durationDays > 30) {
    throw new Error('여행 기간은 1일부터 30일 사이여야 합니다.');
  }
  if (!Number.isInteger(items) || items < 1 || items > 20) {
    throw new Error('날짜별 수집 개수는 1부터 20 사이여야 합니다.');
  }
  if (!Number.isInteger(maxDates) || maxDates < 1 || maxDates > 31) {
    throw new Error('검사할 날짜 수는 1부터 31 사이여야 합니다.');
  }

  const spanDays = daysBetweenYYYYMMDD(startDate, endDate);
  if (spanDays > 60) {
    throw new Error('날짜 찾기 범위는 최대 60일까지만 한 번에 검사할 수 있습니다.');
  }

  const candidates = [];
  for (let offset = 0; offset <= spanDays && candidates.length < maxDates; offset += 1) {
    const depart = addDaysYYYYMMDD(startDate, offset);
    const returnDate = tripType === 'roundtrip' ? addDaysYYYYMMDD(depart, durationDays) : '';

    if (tripType === 'roundtrip' && returnDate > endDate) {
      continue;
    }

    candidates.push({ depart, returnDate });
  }

  if (!candidates.length) {
    throw new Error('검사할 수 있는 여행 날짜 조합이 없습니다. 기간을 넓히거나 여행 기간을 줄여 주세요.');
  }

  return {
    source,
    tripType,
    dep3,
    arr3,
    startDate,
    endDate,
    durationDays,
    items,
    maxDates,
    headless,
    candidates,
  };
}

function buildCrawlerConfig(baseConfig, source) {
  const filenamePrefix = sourceFilenamePrefix(source);
  const { tripType, dep3, arr3, depart, returnDate, items, headless } = baseConfig;
  const datePart = tripType === 'oneway' ? `${depart}-oneway` : `${depart}-${returnDate}`;
  const filename = `${filenamePrefix}${dep3}_TO_${arr3}_${datePart}.csv`;
  const outputPath = path.join(RESULT_DIR, filename);
  const args = [
    path.join(ROOT_DIR, 'main.py'),
    '--source', source,
    '--trip-type', tripType,
    '--from', dep3,
    '--to', arr3,
    '--depart', depart,
    '--items', String(items),
    '--format', 'csv',
    '--output-dir', RESULT_DIR,
  ];

  if (tripType === 'roundtrip') {
    args.push('--return-date', returnDate);
  }

  if (headless) {
    args.push('--headless');
  }

  return {
    source,
    tripType,
    dep3,
    arr3,
    depart,
    returnDate,
    items,
    headless,
    filename,
    outputPath,
    args,
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function parsePriceAmount(value) {
  const text = String(value || '').trim();
  if (!text) return Number.POSITIVE_INFINITY;

  const number = Number(text.replace(/[^\d.]/g, ''));
  return Number.isFinite(number) ? number : Number.POSITIVE_INFINITY;
}

function sortRowsByPrice(rows) {
  return [...rows].sort((left, right) => parsePriceAmount(left.price) - parsePriceAmount(right.price));
}

async function writeCombinedCsv(outputPath, rows) {
  const headers = [
    'price',
    'airline_type',
    'airline',
    'outbound_dep_time',
    'outbound_arr_time',
    'outbound_dep_code',
    'outbound_arr_code',
    'outbound_info',
    'inbound_dep_time',
    'inbound_arr_time',
    'inbound_dep_code',
    'inbound_arr_code',
    'inbound_info',
    'source',
    'trip_type',
    'booking_url',
  ];
  const lines = [
    headers.join(','),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(',')),
  ];
  await fs.writeFile(outputPath, `\uFEFF${lines.join('\n')}\n`, 'utf8');
}

function runCrawler(config) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const child = spawn(PYTHON_BIN, config.args, {
      cwd: ROOT_DIR,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
      },
    });

    let log = '';
    let errorLog = '';
    let settled = false;

    child.stdout.on('data', (data) => {
      log += data.toString();
    });

    child.stderr.on('data', (data) => {
      errorLog += data.toString();
    });

    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      resolve({
        ok: false,
        config,
        error: `크롤러 실행에 실패했습니다: ${error.message}`,
        log,
        errorLog,
        elapsedMs: Date.now() - startedAt,
      });
    });

    child.on('close', async (code) => {
      if (settled) return;
      settled = true;

      if (code !== 0) {
        const failureDetail = summarizeFailure(errorLog) || summarizeFailure(log);
        resolve({
          ok: false,
          config,
          error: failureDetail ? `크롤러가 정상 종료되지 않았습니다: ${failureDetail}` : '크롤러가 정상 종료되지 않았습니다.',
          exitCode: code,
          log,
          errorLog,
          elapsedMs: Date.now() - startedAt,
        });
        return;
      }

      try {
        const csv = await fs.readFile(config.outputPath, 'utf8');
        const rows = parseCsv(csv).map((row) => ({
          ...row,
          source: row.source || config.source,
          trip_type: row.trip_type || config.tripType,
        }));
        resolve({
          ok: true,
          config,
          rows,
          count: rows.length,
          log,
          errorLog,
          elapsedMs: Date.now() - startedAt,
        });
      } catch (error) {
        resolve({
          ok: false,
          config,
          error: `결과 파일을 읽지 못했습니다: ${error.message}`,
          log,
          errorLog,
          elapsedMs: Date.now() - startedAt,
        });
      }
    });
  });
}

function formatRunLog(result) {
  const label = SOURCE_LABELS[result.config.source] || result.config.source;
  const header = `===== ${label} =====`;
  const chunks = [header, result.log];
  if (result.errorLog) chunks.push(result.errorLog);
  if (!result.ok && result.error) chunks.push(result.error);
  return chunks.filter(Boolean).join('\n');
}

async function executeCrawlerSearch(baseConfig) {
  const sources = baseConfig.source === 'all' ? ALL_SEARCH_SOURCES : [baseConfig.source];
  const crawlerConfigs = sources.map((source) => buildCrawlerConfig(baseConfig, source));
  const results = await Promise.all(crawlerConfigs.map((config) => runCrawler(config)));
  const successfulResults = results.filter((result) => result.ok);
  const failedResults = results.filter((result) => !result.ok);
  const rows = sortRowsByPrice(successfulResults.flatMap((result) => result.rows));
  const log = results.map(formatRunLog).join('\n\n');
  const failures = failedResults.map((result) => ({
    source: result.config.source,
    label: SOURCE_LABELS[result.config.source] || result.config.source,
    error: result.error,
  }));

  return {
    ok: Boolean(successfulResults.length),
    rows,
    log,
    failures,
    successfulResults,
  };
}

function cheapestRow(rows) {
  return sortRowsByPrice(rows).find((row) => Number.isFinite(parsePriceAmount(row.price))) || null;
}

function compactRouteText(row, direction) {
  const prefix = direction === 'outbound' ? 'outbound' : 'inbound';
  const depTime = row[`${prefix}_dep_time`] || '';
  const arrTime = row[`${prefix}_arr_time`] || '';
  const depCode = row[`${prefix}_dep_code`] || '';
  const arrCode = row[`${prefix}_arr_code`] || '';
  return [depCode, depTime, '->', arrCode, arrTime].filter(Boolean).join(' ');
}

function summarizeBestRow(row, extra = {}) {
  if (!row) return null;

  return {
    ...extra,
    price: row.price || '',
    priceAmount: parsePriceAmount(row.price),
    source: row.source || '',
    airline: row.airline || '',
    airlineType: row.airline_type || '',
    outbound: compactRouteText(row, 'outbound'),
    inbound: row.trip_type === 'oneway' ? '편도' : compactRouteText(row, 'inbound'),
    tripType: row.trip_type || extra.tripType || '',
    bookingUrl: row.booking_url || '',
  };
}

async function writeSummaryCsv(outputPath, rows) {
  const headers = [
    'rank',
    'destination',
    'arr3',
    'depart',
    'returnDate',
    'price',
    'source',
    'airline',
    'outbound',
    'inbound',
    'bookingUrl',
    'status',
  ];
  const lines = [
    headers.join(','),
    ...rows.map((row, index) => headers.map((header) => {
      if (header === 'rank') return csvEscape(index + 1);
      return csvEscape(row[header]);
    }).join(',')),
  ];
  await fs.writeFile(outputPath, `\uFEFF${lines.join('\n')}\n`, 'utf8');
}

app.post('/api/search', requireApiKey, async (req, res) => {
  let baseConfig;

  try {
    baseConfig = normalizeSearchInput(req.body || {});
    await fs.mkdir(RESULT_DIR, { recursive: true });
  } catch (error) {
    res.status(400).json({ error: error.message });
    return;
  }

  const startedAt = Date.now();
  const sources = baseConfig.source === 'all' ? ALL_SEARCH_SOURCES : [baseConfig.source];
  const crawlerConfigs = sources.map((source) => buildCrawlerConfig(baseConfig, source));
  const results = await Promise.all(crawlerConfigs.map((config) => runCrawler(config)));
  const successfulResults = results.filter((result) => result.ok);
  const failedResults = results.filter((result) => !result.ok);
  const rows = sortRowsByPrice(successfulResults.flatMap((result) => result.rows));
  const log = results.map(formatRunLog).join('\n\n');
  const failures = failedResults.map((result) => ({
    source: result.config.source,
    label: SOURCE_LABELS[result.config.source] || result.config.source,
    error: result.error,
  }));

  if (!successfulResults.length) {
    res.status(500).json({
      error: failures.map((failure) => `${failure.label}: ${failure.error}`).join(' / ') || '검색 요청이 실패했습니다.',
      failures,
      log,
      elapsedMs: Date.now() - startedAt,
    });
    return;
  }

  const responseConfig = baseConfig.source === 'all'
    ? buildCrawlerConfig(baseConfig, 'all')
    : successfulResults[0].config;

  if (baseConfig.source === 'all') {
    await writeCombinedCsv(responseConfig.outputPath, rows);
  }

  res.json({
    source: baseConfig.source,
    tripType: baseConfig.tripType,
    rows,
    count: rows.length,
    filename: responseConfig.filename,
    downloadUrl: `/result/${encodeURIComponent(responseConfig.filename)}`,
    elapsedMs: Date.now() - startedAt,
    log,
    failures,
  });
});

app.post('/api/explore', requireApiKey, async (req, res) => {
  let input;

  try {
    input = normalizeExploreInput(req.body || {});
    await fs.mkdir(RESULT_DIR, { recursive: true });
  } catch (error) {
    res.status(400).json({ error: error.message });
    return;
  }

  const startedAt = Date.now();
  const summaries = [];
  const logs = [];

  for (const arr3 of input.destinations) {
    const baseConfig = {
      source: input.source,
      tripType: input.tripType,
      dep3: input.dep3,
      arr3,
      depart: input.depart,
      returnDate: input.returnDate,
      items: input.items,
      headless: input.headless,
    };
    const result = await executeCrawlerSearch(baseConfig);
    const best = summarizeBestRow(cheapestRow(result.rows), {
      destination: destinationLabel(arr3),
      arr3,
      depart: input.depart,
      returnDate: input.returnDate,
      tripType: input.tripType,
    });

    logs.push(`===== 추천 후보 ${destinationLabel(arr3)} =====\n${result.log}`);
    summaries.push(best || {
      destination: destinationLabel(arr3),
      arr3,
      depart: input.depart,
      returnDate: input.returnDate,
      price: '',
      priceAmount: Number.POSITIVE_INFINITY,
      source: '',
      airline: '',
      outbound: '',
      inbound: '',
      bookingUrl: '',
      status: result.failures.map((failure) => `${failure.label}: ${failure.error}`).join(' / ') || '가격을 찾지 못했습니다.',
    });
  }

  const rows = summaries
    .sort((left, right) => left.priceAmount - right.priceAmount)
    .map((row) => ({
      ...row,
      status: row.status || '수집 완료',
    }));
  const successfulRows = rows.filter((row) => Number.isFinite(row.priceAmount));
  const datePart = input.tripType === 'oneway' ? `${input.depart}-oneway` : `${input.depart}-${input.returnDate}`;
  const filename = `recommend_${input.dep3}_${datePart}.csv`;
  const outputPath = path.join(RESULT_DIR, filename);

  await writeSummaryCsv(outputPath, rows);

  if (!successfulRows.length) {
    res.status(500).json({
      error: '추천 후보에서 가격을 찾지 못했습니다.',
      rows,
      count: 0,
      filename,
      downloadUrl: `/result/${encodeURIComponent(filename)}`,
      elapsedMs: Date.now() - startedAt,
      log: logs.join('\n\n'),
    });
    return;
  }

  res.json({
    source: input.source,
    tripType: input.tripType,
    dep3: input.dep3,
    rows,
    count: successfulRows.length,
    filename,
    downloadUrl: `/result/${encodeURIComponent(filename)}`,
    elapsedMs: Date.now() - startedAt,
    log: logs.join('\n\n'),
  });
});

app.post('/api/cheapest-dates', requireApiKey, async (req, res) => {
  let input;

  try {
    input = normalizeDateScanInput(req.body || {});
    await fs.mkdir(RESULT_DIR, { recursive: true });
  } catch (error) {
    res.status(400).json({ error: error.message });
    return;
  }

  const startedAt = Date.now();
  const summaries = [];
  const logs = [];

  for (const candidate of input.candidates) {
    const baseConfig = {
      source: input.source,
      tripType: input.tripType,
      dep3: input.dep3,
      arr3: input.arr3,
      depart: candidate.depart,
      returnDate: candidate.returnDate,
      items: input.items,
      headless: input.headless,
    };
    const result = await executeCrawlerSearch(baseConfig);
    const best = summarizeBestRow(cheapestRow(result.rows), {
      destination: destinationLabel(input.arr3),
      arr3: input.arr3,
      depart: candidate.depart,
      returnDate: candidate.returnDate,
      tripType: input.tripType,
    });

    logs.push(`===== 날짜 후보 ${candidate.depart}${candidate.returnDate ? `-${candidate.returnDate}` : ''} =====\n${result.log}`);
    summaries.push(best || {
      destination: destinationLabel(input.arr3),
      arr3: input.arr3,
      depart: candidate.depart,
      returnDate: candidate.returnDate,
      price: '',
      priceAmount: Number.POSITIVE_INFINITY,
      source: '',
      airline: '',
      outbound: '',
      inbound: '',
      bookingUrl: '',
      status: result.failures.map((failure) => `${failure.label}: ${failure.error}`).join(' / ') || '가격을 찾지 못했습니다.',
    });
  }

  const rows = summaries
    .sort((left, right) => left.priceAmount - right.priceAmount)
    .map((row) => ({
      ...row,
      status: row.status || '수집 완료',
    }));
  const successfulRows = rows.filter((row) => Number.isFinite(row.priceAmount));
  const filename = `dates_${input.dep3}_TO_${input.arr3}_${input.startDate}-${input.endDate}.csv`;
  const outputPath = path.join(RESULT_DIR, filename);

  await writeSummaryCsv(outputPath, rows);

  if (!successfulRows.length) {
    res.status(500).json({
      error: '날짜 후보에서 가격을 찾지 못했습니다.',
      rows,
      count: 0,
      filename,
      downloadUrl: `/result/${encodeURIComponent(filename)}`,
      elapsedMs: Date.now() - startedAt,
      log: logs.join('\n\n'),
    });
    return;
  }

  res.json({
    source: input.source,
    tripType: input.tripType,
    dep3: input.dep3,
    arr3: input.arr3,
    rows,
    count: successfulRows.length,
    filename,
    downloadUrl: `/result/${encodeURIComponent(filename)}`,
    elapsedMs: Date.now() - startedAt,
    log: logs.join('\n\n'),
  });
});

app.get('/api/destinations', (req, res) => {
  res.json({
    destinations: DESTINATION_PRESETS,
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    ok: true,
    service: 'flight-crawler-api',
    apiKeyRequired: Boolean(API_KEY),
    sources: ALL_SEARCH_SOURCES,
  });
});

app.use((req, res) => {
  res.sendFile(path.join(ROOT_DIR, 'public', 'index.html'));
});

function listen(port, remainingAttempts = MAX_PORT_ATTEMPTS) {
  const server = app.listen(port, HOST, () => {
    console.log(`Flight crawler web UI: http://${HOST}:${port}`);
  });

  server.on('error', (error) => {
    if (error.code === 'EADDRINUSE' && remainingAttempts > 1) {
      const nextPort = port + 1;
      console.warn(`${HOST}:${port} 포트가 사용 중이라 ${nextPort} 포트로 다시 시도합니다.`);
      listen(nextPort, remainingAttempts - 1);
      return;
    }

    console.error(`Failed to start web server: ${error.message}`);
    process.exitCode = 1;
  });
}

listen(PORT);
