const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');

const express = require('express');

const app = express();
const PORT = Number(process.env.PORT || 8080);
const HOST = process.env.HOST || '127.0.0.1';
const ROOT_DIR = __dirname;
const RESULT_DIR = path.join(ROOT_DIR, 'result');
const PYTHON_BIN = process.env.PYTHON_BIN || path.join(ROOT_DIR, '.venv', 'bin', 'python');
const API_KEY = process.env.API_KEY || '';
const DEFAULT_ALLOWED_ORIGINS = [
  'https://solishim.github.io',
  'http://localhost:8080',
  'http://127.0.0.1:8080',
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

const server = app.listen(PORT, HOST, () => {
  console.log(`Flight crawler web UI: http://${HOST}:${PORT}`);
});

server.on('error', (error) => {
  console.error(`Failed to start web server: ${error.message}`);
  process.exitCode = 1;
});
