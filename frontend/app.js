'use strict';
const $ = id => document.getElementById(id);
const MAX_BYTES = 10 * 1024 * 1024;
let previewUrl = null;
let busy = false;
let buttonEventCount = 0;
let buttonEventRequestInFlight = false;

function messageFromError(response, data) {
  const detail = data?.detail;
  return typeof detail === 'string' ? detail : `Request failed (HTTP ${response.status})`;
}
function modeOf(data) {
  const hw = data?.hardware || {};
  const isMock = data?.hardware_mode === 'mock' || hw.is_mock === true || hw.mock === true || data?.mock_hardware === true;
  const connected = data?.hardware_connected === true || hw.connected === true;
  return isMock ? 'MOCK' : connected ? 'CONNECTED' : 'DISCONNECTED';
}
function providerOf(data) {
  return data?.recognition_provider || data?.provider || data?.recognition?.provider || 'Unknown';
}
function locationOf(data) {
  return data?.location || 'UNCONFIGURED';
}
async function refreshStatus() {
  $('refresh-status').disabled = true;
  try {
    const response = await fetch('/api/status', {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(messageFromError(response, data));
    const mode = modeOf(data);
    $('camera-status').textContent = data.camera_connected === true
      ? 'Camera connected.'
      : 'Camera unavailable. You can still upload a photo to identify the item.';
    $('hardware-status').textContent = mode;
    const provider = String(providerOf(data));
    $('provider-status').textContent = provider.toUpperCase();
    $('location-status').textContent = String(locationOf(data));
    const mock = provider.toLowerCase().includes('mock');
    $('mock-hint-wrap').hidden = !mock;
    if (!mock) $('hint').value = '';
    $('status-note').textContent = mode === 'MOCK'
      ? 'Mock mode: commands return simulated replies, not physical LED activity.'
      : mode === 'CONNECTED' ? 'Pico is connected. Manual buttons control the physical indicator.'
      : 'No physical Pico connection detected. You may still upload images to inspect recognition and rule results.';
  } catch(error) {
    $('camera-status').textContent = 'Camera unavailable. You can still upload a photo to identify the item.';
    $('hardware-status').textContent = 'UNAVAILABLE';
    $('provider-status').textContent = '—';
    $('location-status').textContent = '—';
    $('status-note').textContent = `Backend status unavailable: ${error.message}`;
  } finally { $('refresh-status').disabled = false; }
}
$('refresh-status').addEventListener('click', refreshStatus);

async function refreshButtonEvents() {
  if (buttonEventRequestInFlight) return;
  buttonEventRequestInFlight = true;
  try {
    const response = await fetch('/api/events', {cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(messageFromError(response, data));
    if (!Array.isArray(data.events)) throw new Error('Invalid button-event response');

    const presses = data.events.filter(event => event === 'EVT BUTTON').length;
    if (presses) {
      buttonEventCount += presses;
      const receivedAt = new Intl.DateTimeFormat(undefined, {
        hour: 'numeric', minute: '2-digit', second: '2-digit'
      }).format(new Date());
      $('button-event-status').textContent =
        `Physical button pressed · ${buttonEventCount} received · Last received ${receivedAt}`;
    } else if (buttonEventCount === 0) {
      $('button-event-status').textContent = 'Waiting for a physical button press.';
    }
  } catch(error) {
    if (buttonEventCount === 0) {
      $('button-event-status').textContent = `Button events unavailable: ${error.message}`;
    }
  } finally {
    buttonEventRequestInFlight = false;
  }
}

function setPhoto(file) {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  $('photo-preview').hidden = true;
  $('preview-overlay').hidden = true;
  $('empty-preview').hidden = false;
  $('selected-file').hidden = true;
  if (!file) return;
  $('file-name').textContent = `${file.name} · ${(file.size/(1024*1024)).toFixed(2)} MB`;
  $('selected-file').hidden = false;
  if (file.type.startsWith('image/') && !/hei[cf]/i.test(file.type)) {
    previewUrl = URL.createObjectURL(file);
    $('photo-preview').src = previewUrl;
    $('photo-preview').hidden = false;
    $('preview-overlay').hidden = false;
    $('empty-preview').hidden = true;
  }
}
$('photo').addEventListener('change', () => { $('scan-error').hidden = true; setPhoto($('photo').files[0]); });
$('clear-photo').addEventListener('click', () => { $('photo').value = ''; setPhoto(null); });
const dropzone = $('dropzone');
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('is-dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('is-dragover'));
dropzone.addEventListener('drop', e => {
  e.preventDefault(); dropzone.classList.remove('is-dragover');
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const dt = new DataTransfer(); dt.items.add(file); $('photo').files = dt.files;
  $('photo').dispatchEvent(new Event('change'));
});

const BIN_ICONS = {RECYCLE:'♻', COMPOST:'❀', LANDFILL:'▤', UNKNOWN:'?'};
function badge(label, extra='') { const el=document.createElement('span'); el.className=`badge ${extra}`; el.textContent=label; $('result-badges').appendChild(el); }
function safeSource(url) {
  try {
    const parsed = new URL(url);
    return ['https:','http:'].includes(parsed.protocol) ? parsed.href : null;
  } catch (_) { return null; }
}
function renderMultiResults(objects) {
  const container = $('multi-results');
  container.replaceChildren();
  for (const result of objects) {
    const card = document.createElement('article');
    card.className = 'multi-result';
    const heading = document.createElement('div');
    heading.className = 'multi-result-heading';
    const item = document.createElement('h3');
    item.textContent = result.item || `Detected item ${result.object_id || ''}`.trim();
    const bin = document.createElement('span');
    bin.className = `badge bin-badge bin-${String(result.bin || 'UNKNOWN').toLowerCase()}`;
    bin.textContent = ['RECYCLE','COMPOST','LANDFILL','UNKNOWN'].includes(result.bin) ? result.bin : 'UNKNOWN';
    heading.append(item, bin);
    const material = document.createElement('p');
    material.className = 'multi-material';
    material.textContent = `Material: ${result.material || 'Unknown'}`;
    const explanation = document.createElement('p');
    explanation.className = 'multi-explanation';
    explanation.textContent = result.message || result.explanation || 'No verified disposal guidance is available.';
    card.append(heading, material, explanation);
    if (result.question) {
      const question = document.createElement('p');
      question.className = 'multi-question';
      question.textContent = `What to check: ${result.question}`;
      card.append(question);
    }
    const source = safeSource(result.source_url);
    if (source) {
      const link = document.createElement('a');
      link.href = source;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'View official guidance ↗';
      card.append(link);
    }
    if (result.rule_checked_date) {
      const checked = document.createElement('small');
      checked.className = 'rule-date';
      checked.textContent = `Rule checked: ${result.rule_checked_date}`;
      card.append(checked);
    }
    container.append(card);
  }
}
function renderResult(data) {
  const recognition = data.recognition || {};
  const rule = data.recommendation || data.rules || {};
  const objects = Array.isArray(data.objects) ? data.objects : [];
  const multi = data.multiple_items === true && objects.length > 1;
  const bin = ['RECYCLE','COMPOST','LANDFILL','UNKNOWN'].includes(rule.bin) ? rule.bin : 'UNKNOWN';
  $('result-empty').hidden = true;
  $('result-content').hidden = multi;
  $('multi-results').hidden = !multi;
  $('result-badges').replaceChildren();
  if (data.mock_recognition === true || recognition.mock === true) badge('MOCK');
  if (rule.demo === true || objects.some(item => item.demo === true)) badge('DEMO','demo');
  if (multi) {
    renderMultiResults(objects);
    const count = Number.isInteger(data.object_count) ? data.object_count : objects.length;
    $('multi-results').prepend(Object.assign(document.createElement('p'), {
      className: 'multi-summary',
      textContent: `${count} items detected. Each item has a separate recommendation; no single bin command was sent.`
    }));
    return;
  }
  const result = objects.length === 1 ? objects[0] : rule;
  $('bin-name').textContent = bin;
  $('bin-icon').textContent = BIN_ICONS[bin];
  $('bin-icon').style.background = ({RECYCLE:'#deeee1',COMPOST:'#fcf0c8',LANDFILL:'#fde4e0',UNKNOWN:'#e6e9ec'})[bin];
  $('bin-icon').style.color = ({RECYCLE:'#2d8047',COMPOST:'#97701c',LANDFILL:'#b75a4a',UNKNOWN:'#606a78'})[bin];
  $('result-item').textContent = result.item || recognition.item || 'Could not identify item';
  $('item-value').textContent = result.item || recognition.item || 'Unknown';
  $('material-value').textContent = result.material || recognition.material || 'Not determined';
  $('result-message').textContent = result.message || result.explanation || rule.message || 'No verified disposal rule is available for this item and location.';
  const question = result.question || recognition.question || (result.needs_clarification || recognition.needs_clarification ? 'Check the item’s packaging or ask your local waste provider.' : null);
  $('clarification').hidden = !question;
  $('clarification-text').textContent = question || '';
  const safeUrl = safeSource(result.source_url || rule.source_url);
  $('source-wrap').hidden = !safeUrl;
  if(safeUrl) $('source-link').href = safeUrl; else $('source-link').removeAttribute('href');
  const checkedDate = result.rule_checked_date;
  $('rule-date-wrap').hidden = !checkedDate;
  $('rule-date').textContent = checkedDate || '';
  const sent = (data.commands_sent || []).join(' → ');
  const replies = (data.pico_replies || []).join(' · ');
  const hw = data.mock_hardware ? 'MOCK Pico' : 'Pico';
  $('hardware-feedback').textContent = data.hardware_error
     ? `${hw} communication error: ${data.hardware_error}`
     : sent ? `${hw}: ${sent} | Replies: ${replies || 'None'}` : 'No hardware commands reported.';
}
$('classify-form').addEventListener('submit', async e => {
  e.preventDefault();
  if (busy) return;
  $('scan-error').hidden = true;
  const file = $('photo').files[0];
  if (!file) { $('scan-error').textContent = 'Choose a photo first.'; $('scan-error').hidden=false; return; }
  if (file.size > MAX_BYTES) { $('scan-error').textContent = 'This photo is over 10 MB. Choose a smaller image.'; $('scan-error').hidden=false; return; }
  busy=true; $('classify-button').disabled=true; $('classify-button-text').textContent='Analyzing your item…';
  const form = new FormData(); form.append('photo',file);
  if (!$('mock-hint-wrap').hidden && $('hint').value.trim()) form.append('hint',$('hint').value.trim());
  try {
    const response = await fetch('/api/classify',{method:'POST',body:form});
    const data = await response.json();
    if(!response.ok) throw new Error(messageFromError(response,data));
    renderResult(data);
    $('result-heading').scrollIntoView({behavior:'smooth',block:'start'});
  } catch(error) {
    $('scan-error').textContent=`Could not classify this photo: ${error.message}`;
    $('scan-error').hidden=false;
  } finally { busy=false; $('classify-button').disabled=false; $('classify-button-text').textContent='Identify & Sort'; }
});
$('scan-again').addEventListener('click', () => { $('photo').value='';setPhoto(null);$('hint').value='';$('result-empty').hidden=false;$('result-content').hidden=true;$('multi-results').hidden=true;$('multi-results').replaceChildren();$('result-badges').replaceChildren();$('scanner-heading').scrollIntoView({behavior:'smooth',block:'start'}); });

document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', async () => {
  const command = button.dataset.command;
  document.querySelectorAll('[data-command]').forEach(b => b.disabled=true);
  $('command-response').textContent=`Sending ${command}…`;
  try {
    const response=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command})});
    const data=await response.json();
    if(!response.ok) throw new Error(messageFromError(response,data));
    $('command-response').textContent=`${data.mock ? '[MOCK] ' : ''}${data.reply || 'No reply'}`;
  } catch(error) { $('command-response').textContent=`ERROR: ${error.message}`; }
  finally { document.querySelectorAll('[data-command]').forEach(b => b.disabled=false); refreshStatus(); }
}));
refreshStatus();
refreshButtonEvents();
setInterval(refreshButtonEvents, 500);
