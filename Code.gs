/**
 * FIIB Placement Insights: Google Sheet connector (free).
 *
 * 1. Open your Google Sheet > Extensions > Apps Script. Delete what is there and paste this file.
 * 2. Change TOKEN below to a long random password. Put the same value in the app's SHEETS_TOKEN.
 * 3. Deploy > New deployment > type "Web app". Execute as: Me. Who has access: Anyone.
 * 4. Copy the web app URL (ends in /exec) into the app's SHEETS_WEBAPP_URL.
 *
 * The app creates two tabs by itself: "Assessments" and "Reviews".
 */
const TOKEN = 'CHANGE-ME-to-a-long-random-password';
const SHEETS = ['Assessments', 'Reviews'];

function doPost(e) {
  let req;
  try {
    req = JSON.parse(e.postData.contents);
  } catch (err) {
    return out({ ok: false, error: 'Bad request' });
  }
  if (!req || req.token !== TOKEN) return out({ ok: false, error: 'Wrong token' });
  if (SHEETS.indexOf(req.sheet) < 0) return out({ ok: false, error: 'Unknown sheet' });

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = getSheet(req.sheet);
    if (req.action === 'list') return out({ ok: true, data: listRows(sh) });
    if (req.action === 'add') { addRow(sh, req.record || {}); return out({ ok: true }); }
    if (req.action === 'update') { updateRow(sh, req.id, req.fields || {}); return out({ ok: true }); }
    return out({ ok: false, error: 'Unknown action' });
  } catch (err) {
    return out({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return out({ ok: true, data: 'FIIB Placement Insights connector is running.' });
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function getSheet(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1).setValue('id');
    sh.setFrozenRows(1);
  }
  return sh;
}

function headers(sh) {
  const lc = Math.max(1, sh.getLastColumn());
  return sh.getRange(1, 1, 1, lc).getValues()[0].map(String);
}

function ensureHeaders(sh, keys) {
  const h = headers(sh);
  const missing = keys.filter(function (k) { return h.indexOf(k) < 0; });
  if (missing.length) sh.getRange(1, h.length + 1, 1, missing.length).setValues([missing]);
  return headers(sh);
}

// Strings are stored as plain text (the leading ' stops Sheets turning them into dates or formulas).
function clean(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'boolean' || typeof v === 'number') return v;
  v = String(v);
  if (v.length > 49000) v = v.slice(0, 49000);
  return v === '' ? '' : "'" + v;
}

function addRow(sh, rec) {
  const h = ensureHeaders(sh, Object.keys(rec));
  sh.appendRow(h.map(function (k) { return clean(rec[k]); }));
}

function listRows(sh) {
  const last = sh.getLastRow();
  if (last < 2) return [];
  const h = headers(sh);
  const vals = sh.getRange(2, 1, last - 1, h.length).getValues();
  return vals.map(function (r) {
    const o = {};
    h.forEach(function (k, i) {
      let v = r[i];
      if (v instanceof Date) v = v.toISOString();
      o[k] = v;
    });
    return o;
  });
}

function updateRow(sh, id, fields) {
  const h = ensureHeaders(sh, Object.keys(fields));
  const last = sh.getLastRow();
  if (last < 2) return;
  const ids = sh.getRange(2, 1, last - 1, 1).getValues();
  for (let i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(id)) {
      Object.keys(fields).forEach(function (k) {
        sh.getRange(i + 2, h.indexOf(k) + 1).setValue(clean(fields[k]));
      });
      return;
    }
  }
}
