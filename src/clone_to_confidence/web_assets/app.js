(() => {
  const $ = (selector) => document.querySelector(selector);
  const form = $('#audit-form');
  const input = $('#repo-path');
  let current = null;
  let lastReport = null;
  let publicMode = false;

  const setNotice = (message = '') => { $('#notice').textContent = message; };
  const setBusy = (busy) => { form.querySelector('button').disabled = busy; $('#demo-button').disabled = busy; };
  const api = async (url, body) => {
    const response = await fetch(url, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : undefined);
    const data = await response.json().catch(() => ({error: 'The dashboard returned an invalid response.'}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  };

  function statusText(summary) {
    if (summary.FAIL) return 'Attention required';
    if (summary.WARN) return 'Review warnings';
    return 'Looks rebuildable';
  }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char])); }
  function render(report) {
    lastReport = report;
    current = report.repository;
    $('#empty-state').classList.add('hidden'); $('#dashboard').classList.remove('hidden');
    const s = report.displaySummary || report.summary; const n = report.score ?? 0;
    $('#meter').style.setProperty('--score', `${n}%`); $('#score').textContent = n;
    $('#overall-status').textContent = statusText(s); $('#last-run').textContent = `Completed ${new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
    $('#pass-count').textContent = s.PASS || 0; $('#fail-count').textContent = s.FAIL || 0; $('#warn-count').textContent = s.WARN || 0; $('#unavailable-count').textContent = s.UNAVAILABLE || 0; $('#score-formula').textContent = report.scoreFormula || 'PASS 100 · WARN 50 · FAIL 0 · unavailable 25';
    $('#checked-repo').textContent = report.repository; $('#run-state').textContent = 'AUDIT COMPLETE';
    $('#checks-grid').innerHTML = report.checks.map((check) => `<article class="check"><div class="check-head"><span class="status status-${escapeHtml(check.status)}">${escapeHtml(check.status)}</span><span class="check-title">${escapeHtml(check.name)}</span></div><p class="check-explanation">${escapeHtml(check.explanation)}</p><details><summary>Evidence & remediation</summary><ul class="evidence-list">${(check.evidence.length ? check.evidence : ['No evidence recorded.']).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>${check.remediation ? `<p>${escapeHtml(check.remediation)}</p>` : '<p>No remediation needed.</p>'}</details></article>`).join('');
    $('#dry-run-button').disabled = publicMode; $('#verify-button').disabled = publicMode; $('#verify-hint').textContent = publicMode ? 'Hosted demo is read-only; verification is available in local mode after an audit.' : 'Audit complete. Verification runs Docker and the documented allowlisted test command.';
    $('#fix-list').innerHTML = '<div class="fix-placeholder">Preview safe fixes to see create-only proposals.</div>'; $('#apply-button').disabled = true;
    window.location.hash = 'results';
  }
  async function runAudit(path, demo = false) {
    setBusy(true); setNotice('Reading deterministic evidence…'); $('#run-state').textContent = 'AUDITING';
    try { const report = demo ? await api('/api/demo') : await api('/api/audit', {path}); if (!publicMode) input.value = report.repository; render(report); setNotice(publicMode ? 'Demo audit complete. Results are from the bundled fixture.' : ''); }
    catch (error) { setNotice(error.message); $('#run-state').textContent = 'ERROR'; }
    finally { setBusy(false); }
  }
  form.addEventListener('submit', (event) => { event.preventDefault(); if (publicMode) return runAudit('', true); runAudit(input.value.trim()); });
  $('#demo-button').addEventListener('click', () => runAudit('', true));
  $('#export-button').addEventListener('click', () => { if (!lastReport) return; const blob = new Blob([JSON.stringify(lastReport, null, 2)], {type: 'application/json'}); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'clone-to-confidence-report.json'; link.click(); URL.revokeObjectURL(link.href); });
  async function loadFixes(dryRun, confirm = false) {
    try { if (publicMode) { setNotice('Hosted demo mode is read-only; safe fixes are disabled.'); return; } const result = await api('/api/fixes', {path: current, dryRun, confirm}); const list = $('#fix-list'); list.innerHTML = result.changes.length ? result.changes.map((item) => `<div class="fix-item"><b>${escapeHtml(item.action.toUpperCase())}</b><span>${escapeHtml(item.path)}</span></div>`).join('') : '<div class="fix-placeholder">No safe deterministic fixes identified.</div>'; $('#apply-button').disabled = !result.changes.length; if (!dryRun) { $('#confirm-box').classList.add('hidden'); setNotice('Safe fixes applied. Run the audit again to refresh evidence.'); } }
    catch (error) { setNotice(error.message); }
  }
  $('#dry-run-button').addEventListener('click', () => loadFixes(true)); $('#apply-button').addEventListener('click', () => $('#confirm-box').classList.remove('hidden')); $('#cancel-button').addEventListener('click', () => $('#confirm-box').classList.add('hidden')); $('#confirm-button').addEventListener('click', () => loadFixes(false, true));
  $('#verify-button').addEventListener('click', async () => { if (!current) { setNotice('Run an audit before requesting verification.'); return; } if (publicMode) { setNotice('Hosted demo mode is read-only; verification is disabled.'); return; } const button = $('#verify-button'); button.disabled = true; setNotice('Running explicit verification; Docker and tests may take a moment…'); try { const result = await api('/api/verify', {path: current}); for (const key of ['docker', 'tests']) { const item = result[key]; $(`#${key}-status`).textContent = item.status; $(`#${key}-dot`).className = `status-dot ${item.status}`; $(`#${key}-evidence`).textContent = item.evidence || 'No evidence returned.'; } setNotice('Verification complete.'); } catch (error) { setNotice(error.message); } finally { button.disabled = false; } });

  async function initialize() {
    try {
      const health = await api('/api/health');
      publicMode = health.mode === 'public-demo';
      document.body.classList.toggle('public-mode', publicMode);
      $('#mode-badge').innerHTML = `<i></i> ${publicMode ? 'HOSTED / READ-ONLY DEMO' : 'LOCAL / DEMO READY'}`;
      if (publicMode) {
        $('#local-path-controls').classList.add('hidden');
        $('#scope-copy').textContent = 'Bundled fixture only · no server files are modified';
        $('#public-mode-note').classList.remove('hidden');
        $('#demo-button').classList.add('primary');
        $('#demo-button').classList.remove('secondary');
        $('#verify').classList.add('public-hidden');
        $('#demo-button').focus();
      }
    } catch (error) {
      setNotice('Dashboard health check failed. Refresh to try again.');
    }
  }
  initialize();
})();
