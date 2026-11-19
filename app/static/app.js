const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let P = null;          // dự án đang mở
let tab = 'script';
let pollTimer = null;
let voiceInfo = {voices: [], design: {}};

async function api(url, opt = {}) {
  if (opt.json !== undefined) {
    opt.body = JSON.stringify(opt.json);
    opt.headers = {'Content-Type': 'application/json'};
    delete opt.json;
  }
  const r = await fetch(url, opt);
  const t = await r.text();
  let d; try { d = JSON.parse(t); } catch { d = t; }
  if (!r.ok) { alert('⚠️ ' + (d.detail || t)); throw new Error(d.detail || t); }
  return d;
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const f = path => `/files/${P.id}/${path}?v=${Date.now() % 1e7}`;
const plain = sc => (sc.chunks || []).join('').replace(/\n/g, '');
const est = sc => sc.duration || Math.max(1, (plain(sc) || sc.tts || '').length / 6.5);

// ------------------------------------------------------------- dự án
async function loadList() {
  const list = await api('/api/projects');
  $('#projList').innerHTML = list.map(p =>
    `<li data-id="${p.id}" class="${P && P.id === p.id ? 'active' : ''}">${esc(p.title || '(chưa có title)')}
      <small>${p.duration}s · ${p.output ? '✅ đã xuất' : 'đang làm'}</small></li>`).join('');
  $$('#projList li').forEach(li => li.onclick = () => openProject(li.dataset.id));
}

async function openProject(id, keepTab) {
  P = await api(`/api/projects/${id}`);
  $('#empty').classList.add('hidden'); $('#settings').classList.add('hidden');
  $('#proj').classList.remove('hidden');
  $('#pTitle').value = P.title || '';
  $('#pMeta').textContent = `${P.duration}s mục tiêu · ${P.scenes.length} cảnh`;
  if (!keepTab) setTab(P.output ? 'render' : P.script_approved ? (P.scenes.some(s => s.items?.length) ? 'media' : 'voice') : 'script');
  renderAll();
  loadList();
  showJob(P.job);
  if (P.job.status === 'running') startPoll();
}

function setTab(t) {
  tab = t;
  $$('.tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  $$('section[data-pane]').forEach(s => s.classList.toggle('hidden', s.dataset.pane !== t));
  if (P) renderAll();
}
$$('.tabs button').forEach(b => b.onclick = () => {
  if (b.dataset.tab !== 'script' && !P.script_approved && !confirm('Content chưa được duyệt. Vẫn chuyển bước?')) return;
  setTab(b.dataset.tab);
});

function renderAll() {
  const tabsDone = {script: P.script_approved, voice: P.scenes.length && P.scenes.every(s => s.audio && !s.audio_stale),
    media: P.scenes.length && P.scenes.every(s => s.items?.length), render: !!P.output,
    tiktok: !!P.tiktok?.caption};
  $$('.tabs button').forEach(b => b.classList.toggle('done', !!tabsDone[b.dataset.tab]));
  if (tab === 'script') renderScript();
  if (tab === 'voice') renderVoice();
  if (tab === 'media') renderMedia();
  if (tab === 'render') renderRender();
  if (tab === 'tiktok') renderTiktok();
}

function ratioBar(el) {
  let tot = 0, vid = 0;
  P.scenes.forEach(s => { const d = est(s); tot += d; if (s.kind === 'video') vid += d; });
  if (!tot) { el.innerHTML = ''; return; }
  const vp = Math.round(100 * vid / tot);
  el.innerHTML = `<div class="i" style="width:${100 - vp}%">Ảnh ${100 - vp}%</div><div class="v" style="width:${vp}%">${vp ? 'Video ' + vp + '%' : ''}</div>`;
  const tv = P.video_pct ?? 30;
  el.title = `Tổng ~${tot.toFixed(1)} giây (mục tiêu ${P.duration}s) · Mục tiêu: ảnh ${100 - tv}% / video ${tv}%`;
}

// ------------------------------------------------------------- 1. CONTENT
function renderSources() {
  const el = $('#sources'), src = P.sources || [];
  el.classList.toggle('hidden', !src.length);
  el.innerHTML = '<b>📎 Nguồn tin AI đã dùng (bấm để kiểm tra):</b>' + src.map(s =>
    `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.date || '')} · ${esc(s.title || s.url)}</a>`).join('');
}
function renderScript() {
  renderSources();
  const tv = P.video_pct ?? 30;
  $('#pRatio').value = tv; $('#pVidPct').textContent = tv; $('#pImgPct').textContent = 100 - tv;
  $('#pGenre').value = P.genre || 'sports';
  $('#btnRebalance').textContent = `⚖️ Tự chia lại ${100 - tv}% ảnh / ${tv}% video`;
  ratioBar($('#ratio'));
  $('#btnGen').textContent = P.scenes.length ? '✍️ Viết lại từ đầu' : '✍️ Viết content';
  $('#scenes').innerHTML = P.scenes.map((s, i) => `
    <div class="scene" data-i="${i}">
      <div class="meta">
        <span class="sid">${s.id}</span>
        <span class="tag ${s.kind}" data-act="kind" title="Click để đổi ảnh/video">${s.kind === 'video' ? '🎞 Video' : '🖼 Ảnh'}${s.locked_kind ? ' 🔒' : ''}</span>
        <span class="est">~${est(s).toFixed(1)}s</span>
        <div class="mini">
          <button data-act="up" title="Lên">↑</button><button data-act="down" title="Xuống">↓</button>
          <button data-act="del" title="Xóa">✕</button>
        </div>
      </div>
      <div>
        <label>Sub (mỗi dòng = 1 lần hiện, "/" = xuống dòng)</label>
        <textarea class="chunks" data-k="chunks">${esc((s.chunks || []).map(c => c.replace(/\n/g, '/')).join('\n'))}</textarea>
        <label>Câu để đọc (viết tên/ số bằng hiragana cho đọc chuẩn)</label>
        <input data-k="tts" value="${esc(s.tts)}">
      </div>
      <div>
        <label>Từ khóa tìm ảnh</label><input data-k="image_query" value="${esc(s.image_query)}">
        <label>Từ khóa tìm video</label><input data-k="video_query" value="${esc(s.video_query)}">
        <label>Độ "hành động" (0–10, cao → ưu tiên video)</label><input data-k="action" type="number" min="0" max="10" value="${s.action ?? 0}">
      </div>
    </div>`).join('') || '<p class="muted">Chưa có content. Bấm “Viết content”.</p>';
  $$('#scenes .scene').forEach(el => {
    const i = +el.dataset.i;
    el.querySelectorAll('[data-k]').forEach(inp => inp.oninput = () => { readScene(el, i); ratioBar($('#ratio')); el.querySelector('.est').textContent = '~' + est(P.scenes[i]).toFixed(1) + 's'; });
    el.querySelectorAll('[data-act]').forEach(b => b.onclick = () => {
      const a = b.dataset.act, s = P.scenes;
      if (a === 'kind') { s[i].kind = s[i].kind === 'video' ? 'image' : 'video'; s[i].locked_kind = true; }
      if (a === 'up' && i > 0) [s[i - 1], s[i]] = [s[i], s[i - 1]];
      if (a === 'down' && i < s.length - 1) [s[i + 1], s[i]] = [s[i], s[i + 1]];
      if (a === 'del' && confirm('Xóa cảnh này?')) s.splice(i, 1);
      P.script_approved = false;
      renderScript();
    });
  });
}
function readScene(el, i) {
  const s = P.scenes[i];
  el.querySelectorAll('[data-k]').forEach(inp => {
    const k = inp.dataset.k;
    if (k === 'chunks') s.chunks = inp.value.split('\n').map(x => x.trim()).filter(Boolean).map(x => x.replace(/\s*\/\s*/g, '\n'));
    else if (k === 'action') s.action = +inp.value || 0;
    else s[k] = inp.value;
  });
}
async function saveScript(extra = {}) {
  P = Object.assign(await api(`/api/projects/${P.id}`, {method: 'PUT', json: {title: $('#pTitle').value, scenes: P.scenes, ...extra}}), {job: P.job});
  renderAll(); loadList();
}
$('#btnSaveScript').onclick = () => saveScript();
$('#btnApprove').onclick = async () => { await saveScript({script_approved: true}); setTab('voice'); };
$('#btnAddScene').onclick = () => { P.scenes.push({id: '', chunks: [], tts: '', kind: 'image', action: 0}); renderScript(); };
$('#pRatio').oninput = () => { const v = +$('#pRatio').value; $('#pVidPct').textContent = v; $('#pImgPct').textContent = 100 - v; };
$('#pRatio').onchange = async () => {
  P.video_pct = +$('#pRatio').value;
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {video_pct: P.video_pct}});
  $('#btnRebalance').click();   // chia lại ngay theo tỉ lệ mới
};
$('#pGenre').onchange = async () => {
  P.genre = $('#pGenre').value;
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {genre: P.genre}});
};
$('#btnRebalance').onclick = async () => {
  P.scenes.forEach(s => delete s.locked_kind);
  await saveScript(); P = Object.assign(await api(`/api/projects/${P.id}/rebalance`, {method: 'POST'}), {job: P.job}); renderAll();
};
$('#btnGen').onclick = async () => {
  if (P.scenes.length && !confirm('Viết lại toàn bộ content từ đầu?')) return;
  await runJob(`/api/projects/${P.id}/script`, {});
};
$('#btnRegen').onclick = async () => {
  const fb = $('#feedback').value.trim();
  if (!fb) return alert('Nhập góp ý trước nhé');
  await saveScript();
  await runJob(`/api/projects/${P.id}/script`, {feedback: fb});
};
$('#pTitle').onchange = () => api(`/api/projects/${P.id}`, {method: 'PUT', json: {title: $('#pTitle').value}}).then(loadList);

// ------------------------------------------------------------- 2. GIỌNG
async function loadVoices() {
  voiceInfo = await api('/api/voices');
  const v = P?.voice || {};
  $('#voiceSel').innerHTML = '<option value="">— chọn giọng mẫu —</option>' +
    voiceInfo.voices.map(x => `<option ${x.name === v.voice ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  const d = voiceInfo.design, cur = (v.instruct || '').split(',').map(x => x.trim());
  const opt = (id, arr, label) => $(id).innerHTML = arr.map(x => `<option value="${x}" ${cur.includes(x) ? 'selected' : ''}>${x || label}</option>`).join('');
  opt('#dGender', d.gender || [], ''); opt('#dAge', d.age || [], ''); opt('#dPitch', d.pitch || [], ''); opt('#dStyle', d.style || [], '(bình thường)');
  if (!v.instruct) { $('#dAge').value = 'middle-aged'; $('#dPitch').value = 'low pitch'; }
  previewVoice();
}
function previewVoice() {
  const v = voiceInfo.voices.find(x => x.name === $('#voiceSel').value);
  $('#voicePrev').src = v ? `/library/voices/${encodeURIComponent(v.file)}` : '';
}
function renderVoice() {
  const v = P.voice || {};
  $$('input[name=vmode]').forEach(r => r.checked = r.value === (v.mode || 'clone'));
  $$('[data-vmode]').forEach(d => d.classList.toggle('hidden', d.dataset.vmode !== (v.mode || 'clone')));
  $('#autoInstruct').textContent = v.auto_instruct || '(viết content trước để AI đề xuất)';
  $('#speed').value = v.speed || 1; $('#speedVal').textContent = (+$('#speed').value).toFixed(2);
  if (!voiceInfo.voices.length || $('#voiceSel').options.length <= 1) loadVoices(); else $('#voiceSel').value = v.voice || '';
  $('#voiceScenes').innerHTML = P.scenes.map(s => `
    <div class="vrow"><b>${s.id}</b><span class="t">${esc(plain(s))}</span>
      ${s.audio_stale ? '<span class="stale">đã sửa chữ → nên đọc lại</span>' : ''}
      ${s.audio ? `<audio controls preload="none" src="${f(s.audio)}"></audio><span class="muted">${(+s.duration).toFixed(1)}s</span>` : '<span class="muted">chưa đọc</span>'}
      <button data-sid="${s.id}">🎙️ Đọc lại</button></div>`).join('');
  $$('#voiceScenes button').forEach(b => b.onclick = async () => { await saveVoice(); runJob(`/api/projects/${P.id}/tts`, {only: [b.dataset.sid]}); });
}
function voiceFromUI() {
  const mode = $$('input[name=vmode]').find(r => r.checked)?.value || 'clone';
  const instruct = ['#dGender', '#dAge', '#dPitch', '#dStyle'].map(id => $(id).value).filter(Boolean).join(', ');
  return {...P.voice, mode, voice: $('#voiceSel').value, instruct, speed: +$('#speed').value};
}
async function saveVoice() {
  P.voice = voiceFromUI();
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {voice: P.voice}});
}
$$('input[name=vmode]').forEach(r => r.onchange = () => { P.voice = voiceFromUI(); renderVoice(); saveVoice(); });
['#dGender', '#dAge', '#dPitch', '#dStyle'].forEach(id => $(id).onchange = saveVoice);
$('#voiceSel').onchange = () => { previewVoice(); saveVoice(); };
$('#speed').oninput = () => $('#speedVal').textContent = (+$('#speed').value).toFixed(2);
$('#speed').onchange = saveVoice;
$('#btnVoiceUp').onclick = async () => {
  const file = $('#vFile').files[0], name = $('#vName').value.trim();
  if (!file || !name) return alert('Nhập tên và chọn file giọng');
  const fd = new FormData(); fd.append('name', name); fd.append('ref_text', $('#vText').value); fd.append('file', file);
  const r = await api('/api/voices', {method: 'POST', body: fd});
  P.voice.voice = r.name; await loadVoices(); $('#voiceSel').value = r.name; previewVoice(); saveVoice();
};
$('#btnTTS').onclick = async () => { await saveVoice(); runJob(`/api/projects/${P.id}/tts`, {}); };
$('#btnTTSStale').onclick = async () => {
  const only = P.scenes.filter(s => !s.audio || s.audio_stale).map(s => s.id);
  if (!only.length) return alert('Không có cảnh nào cần đọc lại');
  await saveVoice(); runJob(`/api/projects/${P.id}/tts`, {only});
};

// ------------------------------------------------------------- 3. ẢNH & VIDEO
function renderMedia() {
  ratioBar($('#ratio2'));
  $('#mediaScenes').innerHTML = P.scenes.map((s, i) => {
    const items = s.items || [];
    const cands = [...(s.candidates || [])];
    items.forEach(it => { if (!cands.some(c => c.file === it.file && c.start === it.start)) cands.unshift(it); });
    s.candidates = cands;
    const isVid = items[0]?.kind === 'video';
    const sel = new Set(items.map(x => x.kind === 'video' ? x.file + '@' + x.start : x.file));
    let chosen = '';
    if (isVid) {
      const it = items[0];
      chosen = `<div class="chosen"><video controls muted preload="metadata" src="/files/${P.id}/${it.file}#t=${it.start},${(+it.start + est(s)).toFixed(2)}"></video>
        <div class="muted">Đoạn ${(+it.start).toFixed(1)}s → ${(+it.start + est(s)).toFixed(1)}s<br>${it.url && it.url !== 'upload' ? `<a href="${esc(it.url)}" target="_blank">nguồn</a>` : ''}</div></div>`;
    }
    const thumbs = cands.map((c, k) => {
      const key = c.kind === 'video' ? c.file + '@' + c.start : c.file;
      const idx = items.findIndex(x => (x.kind === 'video' ? x.file + '@' + x.start : x.file) === key);
      return `<div class="thumb ${sel.has(key) ? 'sel' : ''}" data-k="${k}">
        <img loading="lazy" src="/files/${P.id}/${c.kind === 'video' ? c.thumb : c.file}">
        ${idx >= 0 ? `<span class="n">${idx + 1}</span>` : ''}
        ${c.kind === 'video' ? `<span class="t">${(+c.start).toFixed(1)}s</span>` : ''}</div>`;
    }).join('');
    const need = s.kind === 'image' ? Math.max(1, Math.round(est(s) / 4.5)) : 1;
    const vres = (s.video_results || []).map(r => `<a data-url="${esc(r.url)}" title="${esc(r.title)}">▶ ${esc(r.title.slice(0, 40))} (${Math.round(r.duration || 0)}s)</a>`).join('');
    return `<div class="mscene" data-i="${i}" data-sid="${s.id}">
      <div class="top"><b>${s.id}</b><span class="tag ${s.kind}" data-act="kind">${s.kind === 'video' ? '🎞 Video' : '🖼 Ảnh'}</span>
        <span class="text">${esc(plain(s))}</span><span class="muted">~${est(s).toFixed(1)}s · ${s.kind === 'image' ? `cần ${need} ảnh (${(est(s) / need).toFixed(1)}s/ảnh)` : '1 đoạn video'}</span></div>
      ${chosen}
      <div class="thumbs">${thumbs || '<span class="muted">Chưa có ảnh/video</span>'}</div>
      <div class="mtools">
        <input class="q" placeholder="Từ khóa khác..." value="${esc(s.kind === 'video' ? s.video_query : s.image_query)}">
        <button data-act="search">🔎 Tìm lại</button>
        ${s.kind === 'video' ? `<input class="url" placeholder="Hoặc dán link YouTube / TikTok / X / Facebook..."><button data-act="url">Dùng link</button>` : ''}
        <label class="btn"><input type="file" class="up hidden" accept="image/*,video/*"><button data-act="upload">⬆ Tải lên</button></label>
      </div>
      ${vres ? `<div class="vres">Video khác: ${vres}</div>` : ''}
    </div>`;
  }).join('');
  $$('#mediaScenes .mscene').forEach(el => {
    const i = +el.dataset.i, sid = el.dataset.sid, s = P.scenes[i];
    el.querySelectorAll('.thumb').forEach(t => t.onclick = async () => {
      P = Object.assign(await api(`/api/projects/${P.id}/scenes/${sid}/pick`, {method: 'POST', json: {index: +t.dataset.k}}), {job: P.job});
      renderMedia();
    });
    el.querySelector('[data-act=kind]').onclick = async () => {
      s.kind = s.kind === 'video' ? 'image' : 'video'; s.locked_kind = true;
      await saveScript(); runJob(`/api/projects/${P.id}/media`, {only: [sid]});
    };
    el.querySelector('[data-act=search]').onclick = async () => {
      const q = el.querySelector('.q').value.trim();
      if (s.kind === 'video') s.video_query = q; else s.image_query = q;
      await saveScript(); runJob(`/api/projects/${P.id}/media`, {only: [sid], query: q});
    };
    const ub = el.querySelector('[data-act=url]');
    if (ub) ub.onclick = () => { const u = el.querySelector('.url').value.trim(); if (u) runJob(`/api/projects/${P.id}/media`, {only: [sid], url: u}); };
    vresBind(el, sid);
    const up = el.querySelector('.up');
    el.querySelector('[data-act=upload]').onclick = e => { e.preventDefault(); up.click(); };
    up.onchange = async () => {
      const fd = new FormData(); fd.append('file', up.files[0]);
      const r = await api(`/api/projects/${P.id}/scenes/${sid}/upload`, {method: 'POST', body: fd});
      if (r.status === 'running') { showJob(r); startPoll(); } else { P = Object.assign(r, {job: P.job}); renderMedia(); }
    };
  });
}
function vresBind(el, sid) {
  el.querySelectorAll('.vres a').forEach(a => a.onclick = () => runJob(`/api/projects/${P.id}/media`, {only: [sid], url: a.dataset.url}));
}
$('#btnMedia').onclick = () => {
  if (P.scenes.some(s => s.items?.length) && !confirm('Tìm lại toàn bộ? Ảnh/video đã chọn sẽ bị thay.')) return;
  if (!P.scenes.every(s => s.audio)) alert('Mẹo: nên đọc giọng trước để tool biết chính xác mỗi cảnh dài bao nhiêu giây.');
  runJob(`/api/projects/${P.id}/media`, {});
};

// ------------------------------------------------------------- 4. XUẤT
async function loadBgm() {
  const list = await api('/api/bgm');
  $('#bgmSel').innerHTML = '<option value="">— không dùng nhạc nền —</option>' + list.map(x => `<option ${x === P.bgm?.file ? 'selected' : ''}>${esc(x)}</option>`).join('');
  $('#bgmPrev').src = P.bgm?.file ? `/library/bgm/${encodeURIComponent(P.bgm.file)}` : '';
}
// ------------------------------------------------------------- 5. TIKTOK
function tkTagsText() { return (P.tiktok?.hashtags || []).filter(t => t.on).map(t => t.tag).join(' '); }
function tkCompose() {
  const t = P.tiktok || {};
  $('#tkFinal').value = (t.caption || '') + '\n\n' + tkTagsText();
  tkCount();
}
function tkCount() {
  const n = [...$('#tkFinal').value].length, tags = (P.tiktok?.hashtags || []).filter(t => t.on).length;
  $('#tkCount').textContent = `${n} ký tự · ${tags} hashtag (TikTok cho tối đa 4000 ký tự)`;
}
function renderTiktok() {
  const t = P.tiktok;
  $('#btnTiktok').textContent = t ? '🔁 Tạo bộ khác' : '✨ Tạo title & hashtag';
  $('#tkBody').classList.toggle('hidden', !t);
  if (!t) return;
  $('#tkCaps').innerHTML = (t.captions || []).map((c, i) => `<div class="cap ${c.ja === t.caption ? 'sel' : ''}" data-i="${i}">
      <div><div class="ja">${esc(c.ja)}</div><div class="vi">${esc(c.vi || '')}</div></div></div>`).join('');
  $$('#tkCaps .cap').forEach(el => el.onclick = () => { t.caption = t.captions[+el.dataset.i].ja; saveTiktok(); renderTiktok(); });
  const groupVi = {big: 'rộng', mid: 'chủ đề', niche: 'cụ thể', discover: 'đề xuất'};
  $('#tkTags').innerHTML = (t.hashtags || []).map((h, i) => `<span class="chip ${h.on ? 'on' : 'off'} ${h.group || ''}" data-i="${i}"
      title="${esc((groupVi[h.group] || '') + (h.vi ? ' · ' + h.vi : ''))}">${esc(h.tag)}<small>${esc(h.vi || '')}</small></span>`).join('');
  $$('#tkTags .chip').forEach(el => el.onclick = () => { const h = t.hashtags[+el.dataset.i]; h.on = !h.on; saveTiktok(); renderTiktok(); });
  tkCompose();
}
async function saveTiktok() { await api(`/api/projects/${P.id}`, {method: 'PUT', json: {tiktok: P.tiktok}}); }
$('#btnTiktok').onclick = () => runJob(`/api/projects/${P.id}/tiktok`, {});
$('#btnAddTag').onclick = () => {
  const v = $('#tkNewTag').value.trim().replace(/\s+/g, '');
  if (!v) return;
  const tag = '#' + v.replace(/^#+/, '');
  if (!P.tiktok.hashtags.some(h => h.tag === tag)) P.tiktok.hashtags.push({tag, group: '', vi: '', on: true});
  $('#tkNewTag').value = ''; saveTiktok(); renderTiktok();
};
$('#tkFinal').oninput = tkCount;
async function copyText(text, btn) {
  try { await navigator.clipboard.writeText(text); }
  catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  const old = btn.textContent; btn.textContent = '✅ Đã copy'; setTimeout(() => btn.textContent = old, 1200);
}
$('#btnCopyAll').onclick = e => copyText($('#tkFinal').value, e.target);
$('#btnCopyCap').onclick = e => copyText($('#tkFinal').value.split('\n\n')[0], e.target);
$('#btnCopyTags').onclick = e => copyText(tkTagsText(), e.target);

function renderRender() {
  loadBgm();
  const vol = Math.round((P.bgm?.volume ?? 0.15) * 100);
  $('#bgmVol').value = vol; $('#bgmVolVal').textContent = vol;
  $('#output').innerHTML = P.output ? `<div class="card"><h3>Video đã xuất</h3>
    <video controls src="${f(P.output)}"></video>
    <a href="/files/${P.id}/${P.output}" download><button class="primary">⬇ Tải video</button></a>
    <span class="muted">File nằm ở: projects/${P.id}/${esc(P.output)}</span></div>` : '';
}
async function saveBgm() {
  P.bgm = {file: $('#bgmSel').value, volume: +$('#bgmVol').value / 100};
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {bgm: P.bgm}});
  $('#bgmPrev').src = P.bgm.file ? `/library/bgm/${encodeURIComponent(P.bgm.file)}` : '';
}
$('#bgmSel').onchange = saveBgm;
$('#bgmVol').oninput = () => { $('#bgmVolVal').textContent = $('#bgmVol').value; $('#bgmPrev').volume = $('#bgmVol').value / 100; };
$('#bgmVol').onchange = saveBgm;
$('#bgmFile').onchange = async () => {
  const fd = new FormData(); fd.append('file', $('#bgmFile').files[0]);
  const r = await api('/api/bgm', {method: 'POST', body: fd});
  P.bgm = {...(P.bgm || {}), file: r.name}; await loadBgm(); $('#bgmSel').value = r.name; saveBgm();
};
$('#btnRender').onclick = async () => { await saveBgm(); runJob(`/api/projects/${P.id}/render`, {}); };

// ------------------------------------------------------------- job
async function runJob(url, body) {
  const j = await api(url, {method: 'POST', json: body});
  showJob(j); startPoll();
}
function showJob(j) {
  const box = $('#jobBox');
  if (!j || j.status === 'idle') { box.classList.add('hidden'); return; }
  box.classList.remove('hidden');
  box.classList.toggle('err', j.status === 'error');
  $('#jobBar').style.width = Math.round((j.progress || 0) * 100) + '%';
  $('#jobLog').textContent = (j.log || []).join('\n');
  $('#jobLog').scrollTop = 1e9;
  $$('button.primary, #btnRegen').forEach(b => { if (b.id !== 'btnCreate') b.disabled = j.status === 'running'; });
}
function startPoll() {
  clearInterval(pollTimer);
  const id = P.id;
  pollTimer = setInterval(async () => {
    if (!P || P.id !== id) return clearInterval(pollTimer);
    const j = await api(`/api/projects/${id}/job`);
    showJob(j);
    if (j.status !== 'running') {
      clearInterval(pollTimer);
      await openProject(id, true);
      if (j.status === 'done' && j.name === 'script') setTab('script');
      if (j.status === 'done' && j.name === 'tiktok') setTab('tiktok');
    }
  }, 1500);
}

// ------------------------------------------------------------- tạo mới, cài đặt
// ---- tin tức
function newsParams() {
  return {region: $('#newsRegion').value, custom_region: $('#newsCustom').value.trim(),
          days: +$('#newsDays').value, category: $('#newsCat').value};
}
function toggleNewsBox() {
  const isNews = $('#newGenre').value === 'news';
  $('#newsBox').classList.toggle('hidden', !isNews);
  $('#newTopic').placeholder = isNews ? 'Để trống = AI tự chọn tin nóng nhất. Hoặc chọn tin đã quét / gõ chủ đề tin.'
    : 'VD: kể chuyện Kawamura Yuki được Grizzlies ký hợp đồng...';
}
async function initNews() {
  const d = await api('/api/news/regions');
  $('#newsRegion').innerHTML = d.regions.map(r => `<option value="${r.id}">${r.vi}</option>`).join('');
  $('#newsCat').innerHTML = d.categories.map(c => `<option value="${c.id}">${c.vi}</option>`).join('');
  try {
    const n = (JSON.parse(localStorage.getItem('shorts_defaults') || '{}')).news;
    if (n) { $('#newsRegion').value = n.region; $('#newsDays').value = n.days; $('#newsCat').value = n.category; $('#newsCustom').value = n.custom_region || ''; }
  } catch {}
  $('#newsCustom').classList.toggle('hidden', $('#newsRegion').value !== 'custom');
}
$('#newGenre').onchange = toggleNewsBox;
$('#newsRegion').onchange = () => $('#newsCustom').classList.toggle('hidden', $('#newsRegion').value !== 'custom');
$('#btnScan').onclick = async () => {
  const b = $('#btnScan'); b.disabled = true; b.textContent = '⏳ Đang quét báo (1–2 phút)...';
  $('#newsList').innerHTML = '';
  try {
    const items = await api('/api/news/suggest', {method: 'POST', json: newsParams()});
    $('#newsList').innerHTML = items.map((n, i) => `<div class="news" data-i="${i}">
      <b>${esc(n.headline_vi)}</b>${esc(n.headline_ja)}<br><small>${esc(n.date || '')} · ${esc(n.source || '')} · 🔥${n.score ?? ''}</small>
      <div>${esc(n.summary_vi || '')}</div></div>`).join('') || '<small>Không tìm thấy tin nào.</small>';
    $$('#newsList .news').forEach(el => el.onclick = () => {
      $$('#newsList .news').forEach(x => x.classList.toggle('sel', x === el));
      const n = items[+el.dataset.i];
      $('#newTopic').value = `${n.headline_ja}\n${n.date || ''} ${n.source || ''}\n${n.url || ''}`;
    });
  } finally { b.disabled = false; b.textContent = '🔎 Quét tin mới nhất'; }
};
initNews().then(toggleNewsBox);

function newRatioLabel() { const v = +$('#newRatio').value; $('#newVidPct').textContent = v; $('#newImgPct').textContent = 100 - v; }
$('#newRatio').oninput = newRatioLabel;
try {  // nhớ lựa chọn lần trước
  const d = JSON.parse(localStorage.getItem('shorts_defaults') || '{}');
  if (d.video_pct !== undefined) $('#newRatio').value = d.video_pct;
  if (d.genre) $('#newGenre').value = d.genre;
} catch {}
newRatioLabel();
$('#newDur').onchange = () => $('#newDurCustom').classList.toggle('hidden', $('#newDur').value !== 'custom');
$('#btnCreate').onclick = async () => {
  const dur = $('#newDur').value === 'custom' ? +$('#newDurCustom').value : +$('#newDur').value;
  if (!dur) return alert('Nhập thời lượng');
  const video_pct = +$('#newRatio').value, genre = $('#newGenre').value;
  const news = genre === 'news' ? newsParams() : null;
  try { localStorage.setItem('shorts_defaults', JSON.stringify({video_pct, genre, news})); } catch {}
  const p = await api('/api/projects', {method: 'POST', json: {title: $('#newTitle').value, topic: $('#newTopic').value, duration: dur, genre, video_pct, news}});
  $('#newsList').innerHTML = '';
  $('#newTitle').value = ''; $('#newTopic').value = '';
  await openProject(p.id);
  setTab('script');
  runJob(`/api/projects/${p.id}/script`, {});
};
$('#btnDelete').onclick = async () => {
  if (!confirm('Xóa video này (cả file đã tải)?')) return;
  await api(`/api/projects/${P.id}`, {method: 'DELETE'});
  P = null; $('#proj').classList.add('hidden'); $('#empty').classList.remove('hidden'); loadList();
};
$('#lnkSettings').onclick = async e => {
  e.preventDefault();
  const s = await api('/api/settings');
  $('#sModel').value = s.claude_model;
  $$('.src').forEach(c => c.checked = (s.image_sources || []).includes(c.value));
  $('#sEnc').value = s.video_encoder; $('#sSize').value = s.subtitle_size; $('#sMediaH').value = s.media_height; $('#sGap').value = s.sub_gap; $('#sFont').value = s.subtitle_font;
  $('#sHL').checked = s.use_claude_for_highlight; $('#sZoom').checked = !!s.image_zoom; $('#sSteps').value = s.tts_num_step;
  $('#proj').classList.add('hidden'); $('#empty').classList.add('hidden'); $('#settings').classList.remove('hidden');
  $('#checkOut').textContent = 'Đang kiểm tra...';
  const c = await api('/api/check');
  $('#checkOut').textContent = [
    `FFmpeg: ${c.ffmpeg ? '✅' : '❌ chưa cài'}`, `Claude CLI: ${c.claude ? '✅' : '❌ chưa cài'}`,
    `Font sub: ${c.font ? '✅' : '❌ chạy install.bat lại'}`, `OmniVoice: ${c.omnivoice ? '✅' : '❌ chưa cài'}`,
    `GPU NVIDIA: ${c.cuda ? '✅ ' + c.gpu : '❌ không thấy (giọng đọc sẽ rất chậm)'}`].join('\n');
};
$('#btnSaveSettings').onclick = async () => {
  await api('/api/settings', {method: 'PUT', json: {claude_model: $('#sModel').value.trim(),
    image_sources: $$('.src').filter(c => c.checked).map(c => c.value), video_encoder: $('#sEnc').value, subtitle_size: +$('#sSize').value, media_height: +$('#sMediaH').value, sub_gap: +$('#sGap').value,
    subtitle_font: $('#sFont').value.trim(), use_claude_for_highlight: $('#sHL').checked, image_zoom: $('#sZoom').checked, tts_num_step: +$('#sSteps').value}});
  alert('Đã lưu');
};
$('#btnCloseSettings').onclick = () => { $('#settings').classList.add('hidden'); P ? $('#proj').classList.remove('hidden') : $('#empty').classList.remove('hidden'); };

loadList();
api('/api/check').then(c => $('#checkBadge').textContent = (c.ffmpeg && c.claude && c.omnivoice && c.cuda) ? '✅ sẵn sàng' : '⚠️ xem cài đặt');
