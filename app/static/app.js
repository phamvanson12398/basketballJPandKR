const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let P = null;          // dự án đang mở
let tab = 'script';
let pollTimer = null;
let voiceInfo = {voices: [], design: {}};
let LANGS = [];

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
const plain = sc => (sc.chunks || []).join('').replace(/\n/g, '').replace(/[〔〕【】《》]/g, '');
const est = sc => {
  if (sc.duration) return sc.duration;
  const t = plain(sc) || sc.tts || '';
  return Math.max(1, /[\uac00-\ud7a3]/.test(t) ? t.replace(/ /g, '').length / 7.0 : t.length / 6.5);
};

// ------------------------------------------------------------- dự án
let PROJECTS = [];
async function loadList() {
  PROJECTS = await api('/api/projects');
  drawList();
}
function drawList() {
  const q = ($('#projSearch').value || '').trim().toLowerCase();
  const list = PROJECTS.filter(p => !q || (p.title || '').toLowerCase().includes(q));
  const item = p => `<li data-id="${p.id}" class="${P && P.id === p.id ? 'active' : ''}">${esc(p.title || '(chưa có title)')}
      <small>${p.duration}s${p.output ? ' · ✅ đã xuất' : ''}</small></li>`;
  const doing = list.filter(p => !p.output), done = list.filter(p => p.output);
  $('#projList').innerHTML =
    (doing.length ? `<div class="grp">Đang làm (${doing.length})</div>` + doing.map(item).join('') : '') +
    (done.length ? `<div class="grp">Đã xuất (${done.length})</div>` + done.map(item).join('') : '') ||
    '<div class="grp">Chưa có video nào</div>';
  $$('#projList li').forEach(li => li.onclick = () => openProject(li.dataset.id));
}
$('#projSearch').oninput = drawList;

async function openProject(id, keepTab) {
  P = await api(`/api/projects/${id}`);
  showOnly('#proj');
  $('#pTitle').value = P.title || '';
  renderTwinBtns();
  $('#pMeta').textContent = `${P.duration}s mục tiêu · ${P.scenes.length} cảnh`;
  if (!keepTab) setTab(P.output ? 'render' : P.script_approved ? (P.scenes.some(s => s.items?.length) ? 'media' : 'voice') : 'script');
  renderAll();
  loadList();
  showJob(P.job);
  if (P.job.status === 'running') startPoll();
}

function renderTwinBtns() {
  if (!P) return;
  $('#twinBtns').innerHTML = LANGS.filter(l => l.id !== (P.lang || 'ja')).map(l =>
    `<button data-lang="${l.id}" title="Viết lại content cho khán giả nước đó, dùng lại y nguyên ảnh/video">🌐 Tạo bản ${l.vi}</button>`).join('');
  $$('#twinBtns button').forEach(b => b.onclick = async () => {
    if (!P.scenes.length) return alert('Video này chưa có content.');
    if (!confirm(`Tạo thêm 1 video ${b.textContent.replace('🌐 Tạo bản ', '')} từ video này?\nẢnh/video giữ nguyên, Claude viết lại content cho khán giả nước đó.`)) return;
    const r = await api(`/api/projects/${P.id}/twin`, {method: 'POST', json: {lang: b.dataset.lang}});
    await openProject(r.id); setTab('script'); startPoll();
  });
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
// ---- bố cục & chữ trên màn hình
const LAYOUT_NAMES = ['sports', 'news', 'ranking', 'biography', 'general', 'korea'];
function effLayout() {
  if (P.layout && P.layout !== 'auto') return P.layout;
  const g = P.genre || 'sports';
  if (g === 'sports' && P.lang === 'ko' && !['idol', 'kpop'].includes(P.sport)) return 'korea';
  return LAYOUT_NAMES.includes(g) ? g : 'sports';
}
function renderScreenBox() {
  const lay = effLayout(), box = $('#screenBox');
  P.screen = P.screen || {};
  const S = P.screen;
  const sportV = lay === 'sports' && ['sumo', 'soccer'].includes(P.sport) ? P.sport : null;
  box.classList.toggle('hidden', lay === 'sports' && !sportV);
  if (lay === 'sports' && !sportV) return;
  const inp = (k, label, ph = '') => `<div><label>${label}</label><input data-s="${k}" value="${esc(S[k] || '')}" placeholder="${esc(ph)}"></div>`;
  let html = '<h3>🖥️ Chữ trên màn hình (tiêu đề cố định, nhãn…)</h3>';
  if (lay === 'korea') {
    html += `<div class="two">${inp('title1', 'Tiêu đề dòng trên (chữ vàng)', '롯데가 정철원 먼저')}${inp('title2', 'Tiêu đề dòng dưới (chữ đỏ)', '팔아넘긴 진짜 이유')}</div>
      <p class="hint">Hộp số liệu và chia đôi khung (so sánh 2 người): chỉnh ở từng cảnh bên dưới.</p>`;
  } else if (sportV === 'sumo') {
    html += `${inp('basho', 'Nhãn giải đấu ở góc ảnh (để trống nếu không nói về giải cụ thể)', '九州場所 13日目')}
      <p class="hint">Cấp bậc, tên + thành tích, con dấu kỹ thuật thắng: chỉnh ở từng cảnh bên dưới. Cảnh nào để trống thì chỉ có ảnh + sub như bóng chày.</p>`;
  } else if (sportV === 'soccer') {
    html += `<div class="two">${inp('league', 'Nhãn giải đấu ở góc ảnh', 'プレミアリーグ 第10節')}
      <div class="two">${inp('home', 'Đội nhà (viết tắt)', 'COV')}${inp('away', 'Đội khách (viết tắt)', 'SUN')}</div></div>
      <p class="hint">Tỉ số, phút, tên cầu thủ: chỉnh ở từng cảnh. Bảng tỉ số chỉ hiện ở cảnh có điền tỉ số.</p>`;
  } else if (lay === 'news') {
    S.stories = S.stories && S.stories.length ? S.stories : [{headline: P.title || '', subhead: '', source: ''}];
    html += `<div class="two">${inp('band', 'Dải đỏ: quốc gia · ngày', '韓国 ・ 11月19日')}
      <label class="chk" style="margin-top:22px"><input type="checkbox" data-s="breaking" ${S.breaking ? 'checked' : ''}> Hiện nhãn 速報 / 속보 (tin nóng)</label></div>
      <label>Tiêu đề từng tin (điểm tin nhiều tin thì mỗi tin 1 dòng; cảnh nào thuộc tin số mấy chỉnh ở ô "Tin số" của cảnh)</label>`;
    html += S.stories.map((st, i) => `<div class="row" data-st="${i}">
      <div><label>Tin ${i + 1}: tiêu đề</label><input data-f="headline" value="${esc(st.headline || '')}"></div>
      <div><label>Dòng phụ</label><input data-f="subhead" value="${esc(st.subhead || '')}"></div>
      <div><label>Nguồn</label><input data-f="source" value="${esc(st.source || '')}"></div>
      <button data-del="${i}" title="Xóa tin">✕</button></div>`).join('');
    html += '<button id="btnAddStory">＋ Thêm tin</button>';
  } else if (lay === 'ranking' || lay === 'general') {
    html += `<div class="two">${inp('title1', 'Tiêu đề dòng trên (nhỏ)')}${inp('title2', lay === 'ranking' ? 'Tiêu đề dòng dưới (to, vàng)' : 'Dòng dưới (đỏ, có vệt bút dạ vàng)')}</div>`;
  } else if (lay === 'biography') {
    html += inp('title', 'Tiêu đề cố định (VD: 大谷翔平の人生)');
  }
  box.innerHTML = html;
  box.querySelectorAll('[data-s]').forEach(el => el.oninput = el.onchange = () => {
    S[el.dataset.s] = el.type === 'checkbox' ? el.checked : el.value;
  });
  box.querySelectorAll('.row[data-st]').forEach(row => row.querySelectorAll('[data-f]').forEach(el =>
    el.oninput = () => { S.stories[+row.dataset.st][el.dataset.f] = el.value; }));
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => { S.stories.splice(+b.dataset.del, 1); renderScreenBox(); });
  const add = $('#btnAddStory');
  if (add) add.onclick = () => { S.stories.push({headline: '', subhead: '', source: ''}); renderScreenBox(); };
}
function sceneLabelFields(s) {
  const lay = effLayout();
  const f = (k, label, type = 'text', ph = '') => `<div class="lbl"><label>${label}</label>
    <input data-k="${k}" type="${type}" value="${esc(s[k] ?? '')}" placeholder="${esc(ph)}"></div>`;
  if (lay === 'news') return f('story', 'Tin số', 'number', '1');
  if (lay === 'korea')
    return f('stat', 'Hộp số liệu', 'text', '타율 2할 8리 / 1홈런') +
      `<div class="lbl"><label>Chia đôi khung</label><label class="check" style="margin:0"><input type="checkbox" data-k="split" ${s.split ? 'checked' : ''}> So sánh 2 người (2 ảnh cạnh nhau)</label></div>` +
      (s.split ? f('image_query2', 'Từ khóa người thứ 2', 'text', '정철원 두산') : '');
  if (lay === 'ranking') return f('rank', 'Hạng', 'number', 'trống = mở đầu/kết') + f('rank_label', 'Dải tên', 'text', '渡邊雄太 875得点');
  if (lay === 'biography') return f('year', 'Năm', 'text', '2010') + f('chapter', 'Chương', 'text', '第2章・高校時代');
  if (lay === 'sports' && P.sport === 'sumo')
    return f('banzuke', 'Cấp bậc', 'text', '横綱') + f('name', 'Tên võ sĩ', 'text', '大の里') +
           f('record', 'Thành tích', 'text', '11勝1敗') + f('kimarite', 'Con dấu', 'text', 'kỹ thuật thắng, VD: 寄り切り');
  if (lay === 'sports' && P.sport === 'soccer')
    return f('score', 'Tỉ số', 'text', '1-0') + f('minute', 'Phút', 'text', "17'") +
           f('player', 'Cầu thủ', 'text', '坂元達裕') + f('team', 'CLB · số áo', 'text', 'コヴェントリー #7');
  return '';
}

function renderScript() {
  renderSources();
  renderScreenBox();
  $('#pLayout').value = P.layout || 'auto';
  $('#subHint').innerHTML = effLayout() === 'korea'
    ? 'Kiểu Shorts Hàn: mỗi dòng trong ô sub = 1 cụm ngắn hiện giữa ảnh (chữ trắng viền đen). Dùng dấu <code>/</code> để chia nhỏ thêm.'
    : effLayout() === 'sports'
    ? 'Mỗi dòng trong ô sub = 1 lần hiện chữ. Dùng dấu <code>/</code> để xuống dòng. Lần hiện thứ 1, 3, 5... nằm <b>trên</b> khung, lần 2, 4, 6... hiện thêm <b>dưới</b> khung (giống video mẫu).'
    : 'Mỗi dòng trong ô sub = 1 lần hiện chữ (bật ra dưới khung ảnh, tối đa 2 dòng). Dùng dấu <code>/</code> để gợi ý chỗ xuống dòng.';
  const tv = P.video_pct ?? 30;
  $('#pRatio').value = tv; $('#pVidPct').textContent = tv; $('#pImgPct').textContent = 100 - tv;
  $('#pGenre').value = P.genre || 'sports';
  if ($('#pLang').options.length) $('#pLang').value = P.lang || 'ja';
  if ($('#pSport').options.length) $('#pSport').value = P.sport || 'other';
  $('#pAudience').value = P.audience || 'all';
  $('#pSport').classList.toggle('hidden', ['news', 'brand', 'history'].includes(P.genre));
  $('#btnRebalance').textContent = `⚖️ Tự chia lại ${100 - tv}% ảnh / ${tv}% video`;
  ratioBar($('#ratio'));
  $('#btnGen').textContent = P.scenes.length ? '✍️ Viết lại từ đầu' : '✍️ Viết content';
  $('#btnGen').className = P.scenes.length ? 'soft' : 'primary';
  const rt = P.retention;
  const RK = {hook: 'Hook 2 giây đầu', open_loop: 'Câu mồi', pacing: 'Nhịp đảo chiều', density: 'Gọn, không thừa', concreteness: 'Cụ thể', payoff: 'Cái kết'};
  if (rt && rt.after) {
    const avg = d => (Object.values(d || {}).reduce((a, b) => a + b, 0) / Math.max(1, Object.keys(d || {}).length)).toFixed(1);
    $('#retSummary').innerHTML = `<b>✨ Điểm giữ chân: ${avg(rt.before)} → ${avg(rt.after)}/10</b>
      <div class="scores">${Object.keys(RK).map(k => `<span>${RK[k]}: ${rt.before?.[k] ?? '–'} → <b>${rt.after?.[k] ?? '–'}</b></span>`).join('')}</div>
      ${rt.notes ? `<div>${esc(rt.notes)}</div>` : ''}
      ${(rt.hooks || []).length ? `<details><summary>🎣 ${rt.hooks.length} câu mở đầu AI đã thử (bấm để đổi)</summary>
        ${rt.hooks.map((h, i) => `<div class="hook ${i === rt.chosen ? 'on' : ''}"><span class="hs">${h.score ?? ''}</span>
          <span class="ht">${esc((h.chunks || []).join(' ').replace(/\n/g, ''))}</span>
          <span class="muted">${esc(h.why || '')}</span>
          ${i === rt.chosen ? '<b>✓ đang dùng</b>' : `<button class="small" data-hook="${i}">Dùng câu này</button>`}</div>`).join('')}</details>` : ''}`;
  } else $('#retSummary').innerHTML = '';
  $('#retSummary').classList.toggle('hidden', !$('#retSummary').innerHTML);
  $$('#retSummary [data-hook]').forEach(b => b.onclick = async () => {
    P = Object.assign(await api(`/api/projects/${P.id}/hook`, {method: 'POST', json: {index: +b.dataset.hook}}), {job: P.job});
    renderScript();
  });
  const fc = P.fact_check;
  $('#factSummary').innerHTML = fc ? `<b>🔍 Kiểm tra sự thật (${esc(fc.at || '')}):</b> ✅ ${fc.counts?.ok || 0} đúng · 🛠 ${fc.counts?.fixed || 0} đã sửa · ⚠️ ${fc.counts?.unsure || 0} chưa chắc chắn<br>${esc(fc.summary || '')}`
    : (P.scenes.length ? '🔍 Content này <b>chưa được kiểm tra sự thật</b> – bấm “🔍 Kiểm tra sự thật” trước khi duyệt.' : '');
  $('#factSummary').classList.toggle('hidden', !$('#factSummary').innerHTML);
  $('#scenes').innerHTML = P.scenes.map((s, i) => `
    <div class="scene" data-i="${i}">
      <div class="scene-head">
        <span class="sid">#${i + 1}</span>
        <span class="tag ${s.kind}" data-act="kind" title="Bấm để đổi ảnh / video">${s.kind === 'video' ? '🎞 Video' : '🖼 Ảnh'}${s.locked_kind ? ' 🔒' : ''}</span>
        <span class="est">~${est(s).toFixed(1)}s</span>
        ${factBadge(s)}
        <span class="grow"></span>
        <div class="mini">
          <button data-act="up" title="Lên">↑</button><button data-act="down" title="Xuống">↓</button>
          <button data-act="del" title="Xóa cảnh">🗑</button>
        </div>
      </div>
      <textarea class="chunks" data-k="chunks" title="Mỗi dòng = 1 lần hiện chữ, dấu / = xuống dòng">${esc((s.chunks || []).map(c => c.replace(/\n/g, '/')).join('\n'))}</textarea>
      ${s.fact && (s.fact.note || (s.fact.sources || []).length) ? `<details class="fact ${s.fact.status}"><summary>${FACT_LABEL[s.fact.status] || ''} ${esc(s.fact.note || '')}</summary>
        ${(s.fact.sources || []).map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">🔗 ${esc(x.title || x.url)}</a>`).join('')}</details>` : ''}
      ${sceneLabelFields(s) ? `<div class="labels">${sceneLabelFields(s)}</div>` : ''}
      <details class="adv"><summary>Tùy chọn: câu đọc, từ khóa tìm ảnh/video</summary>
        <div class="adv-grid">
          <div class="full"><label>Câu để đọc <span class="opt">(tên người, số viết bằng hiragana/hangul để đọc chuẩn)</span></label>
            <input data-k="tts" value="${esc(s.tts)}"></div>
          <div><label>Từ khóa tìm ảnh</label><input data-k="image_query" value="${esc(s.image_query)}"></div>
          <div><label>Từ khóa tìm video</label><input data-k="video_query" value="${esc(s.video_query)}"></div>
          <div><label>Người trong cảnh <span class="opt">(tên đầy đủ – lọc ảnh/video sai người)</span></label><input data-k="who" value="${esc(s.who || '')}"></div>
          <div><label>Từ khóa dự phòng <span class="opt">(khi từ khóa chính ít kết quả)</span></label><input data-k="query_alt" value="${esc(s.query_alt || '')}"></div>
          <div><label>Đội / số áo lúc đó <span class="opt">(AI xem video nhận người)</span></label><input data-k="uniform" value="${esc(s.uniform || '')}" placeholder="ヤクルト 背番号23"></div>
          <div><label>Tên bình luận viên gọi <span class="opt">(tìm trong phụ đề video)</span></label><input data-k="call" value="${esc(s.call || '')}" placeholder="田畑・タバタ"></div>
          <div><label>Hình minh họa <span class="opt">(1 emoji, VD 🍎 ❤️ 🐐 – để trống = không có)</span></label><input data-k="sticker" value="${esc(s.sticker || '')}" placeholder="🍎"></div>
          <div><label>Vị trí hình minh họa <span class="opt">(tl/tr/bl/br = trên trái / trên phải / dưới trái / dưới phải)</span></label><input data-k="sticker_pos" value="${esc(s.sticker_pos || '')}" placeholder="br"></div>
          <div><label>Độ "hành động" <span class="opt">(0–10, cao → ưu tiên video)</span></label>
            <input data-k="action" type="number" min="0" max="10" value="${s.action ?? 0}"></div>
        </div>
      </details>
    </div>`).join('') || '<div class="panel center muted">Chưa có content. Bấm “✍️ Viết content”.</div>';
  $$('#scenes .scene').forEach(el => {
    const i = +el.dataset.i;
    el.querySelectorAll('[data-k]').forEach(inp => inp.oninput = () => { readScene(el, i); ratioBar($('#ratio')); el.querySelector('.est').textContent = '~' + est(P.scenes[i]).toFixed(1) + 's'; });
    el.querySelectorAll('input[type=checkbox][data-k]').forEach(inp => inp.onchange = () => { readScene(el, i); renderScript(); });
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
    else if (inp.type === 'checkbox') s[k] = inp.checked;
    else if (k === 'action') s.action = +inp.value || 0;
    else if (k === 'story') s.story = inp.value === '' ? null : +inp.value;
    else if (k === 'rank') s.rank = inp.value === '' ? null : +inp.value;
    else s[k] = inp.value;
  });
}
async function saveScript(extra = {}) {
  P = Object.assign(await api(`/api/projects/${P.id}`, {method: 'PUT', json: {title: $('#pTitle').value, scenes: P.scenes, screen: P.screen || {}, ...extra}}), {job: P.job});
  renderAll(); loadList();
}
$('#btnSaveScript').onclick = () => saveScript();
const FACT_LABEL = {ok: '✅ Đúng', fixed: '🛠 Đã sửa', unsure: '⚠️ Chưa chắc', edited: '✏️ Bạn đã sửa – nên kiểm tra lại', unchecked: '❔ Chưa kiểm tra'};
function factBadge(s) {
  if (!s.fact) return '';
  const st = s.fact.status;
  return `<span class="fbadge ${st}" title="${esc(s.fact.note || '')}">${FACT_LABEL[st] || ''}</span>`;
}
$('#btnRet').onclick = async () => { await saveScript(); await runJob(`/api/projects/${P.id}/retention`, {}); };
$('#btnFact').onclick = async () => { await saveScript(); await runJob(`/api/projects/${P.id}/factcheck`, {}); };
$('#btnApprove').onclick = async () => {
  const warn = P.scenes.filter(s => !s.fact || ['unsure', 'edited', 'unchecked'].includes(s.fact.status)).length;
  if (warn && !confirm(`Còn ${warn} cảnh chưa kiểm tra / chưa chắc chắn (⚠️ ✏️ ❔).\nNên bấm “🔍 Kiểm tra sự thật” hoặc tự xem lại các cảnh đó.\n\nVẫn duyệt luôn?`)) return;
  await saveScript({script_approved: true}); setTab('voice');
};
$('#btnAddScene').onclick = () => { P.scenes.push({id: '', chunks: [], tts: '', kind: 'image', action: 0}); renderScript(); };
$('#pRatio').oninput = () => { const v = +$('#pRatio').value; $('#pVidPct').textContent = v; $('#pImgPct').textContent = 100 - v; };
$('#pRatio').onchange = async () => {
  P.video_pct = +$('#pRatio').value;
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {video_pct: P.video_pct}});
  $('#btnRebalance').click();   // chia lại ngay theo tỉ lệ mới
};
$('#pLang').onchange = async () => {
  P.lang = $('#pLang').value;
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {lang: P.lang}});
  if (P.scenes.length && confirm('Đã đổi ngôn ngữ. Viết lại content bằng ngôn ngữ mới luôn không?')) runJob(`/api/projects/${P.id}/script`, {});
};
$('#pAudience').onchange = async () => {
  P.audience = $('#pAudience').value;
  P = Object.assign(await api(`/api/projects/${P.id}`, {method: 'PUT', json: {audience: P.audience}}), {job: P.job});
  notify('👥', P.audience === '35plus' ? 'Khán giả: 35+' : 'Khán giả: mọi lứa tuổi',
    'Áp dụng khi viết lại content, đọc giọng và chọn nhạc nền');
};
$('#pSport').onchange = async () => {
  P.sport = $('#pSport').value;
  await api(`/api/projects/${P.id}`, {method: 'PUT', json: {sport: P.sport}});
  renderScript();
};
$('#pLayout').onchange = async () => {
  P.layout = $('#pLayout').value;
  await saveScript({layout: P.layout});
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
  document.querySelector('.inline-pop')?.removeAttribute('open');
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
        ${c.kind === 'image' ? `<button class="crop-btn" data-crop="${esc(c.file)}" title="Cắt ảnh (bỏ chữ, logo…)">✂️</button>` : ''}
        ${c.cropped_from ? '<span class="cut">đã cắt</span>' : ''}
        ${c.rejected ? '<span class="cut" style="background:#b91c1c" title="Claude thấy ảnh này sai người hoặc không hợp nội dung">AI loại</span>' : ''}
        ${c.kind === 'video' ? `<span class="t">${(+c.start).toFixed(1)}s</span>` : ''}</div>`;
    }).join('');
    const need = s.kind === 'image' ? Math.max(1, Math.round(est(s) / 3)) : 1;
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
    el.querySelectorAll('.crop-btn').forEach(b => b.onclick = e => {
      e.stopPropagation();
      const c = (s.candidates || []).find(x => x.file === b.dataset.crop);
      openCrop(sid, b.dataset.crop, !!(c && c.cropped_from));
    });
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
// ---- khung cắt ảnh
const CROP = {sid: null, file: null, box: null, ratio: null};
async function openCrop(sid, file, isCropped) {
  CROP.sid = sid; CROP.file = file;
  try { const st = await api('/api/settings'); CROP.ratio = 1080 / (+st.media_height || 680); } catch { CROP.ratio = 1080 / 680; }
  if (effLayout() === 'korea') {
    let hk = 1140;
    try { hk = Math.max(700, Math.min(1500, +(await api('/api/settings')).media_height_korea || 1140)); } catch {}
    const sc = P.scenes.find(x => x.id === sid);
    CROP.ratio = sc && sc.split ? 537 / hk : 1080 / hk;   // theo chiều cao khung bố cục Hàn (nửa khung khi chia đôi)
  }
  $('#cropReset').classList.toggle('hidden', !isCropped);
  const img = $('#cropImg');
  img.onload = () => {
    const W = img.clientWidth, H = img.clientHeight;
    // khung mặc định: lớn nhất có thể theo tỉ lệ khung video, nằm giữa ảnh
    let w = W, h = W / CROP.ratio;
    if (h > H) { h = H; w = H * CROP.ratio; }
    CROP.box = {x: (W - w) / 2, y: (H - h) / 2, w, h};
    drawCrop();
  };
  // ảnh đã cắt → mở lại ảnh gốc để cắt lại
  const cand = P.scenes.find(x => x.id === sid)?.candidates?.find(c => c.file === file);
  img.src = `/files/${P.id}/${cand?.cropped_from || file}?v=${Date.now() % 1e7}`;
  $('#cropModal').classList.remove('hidden');
}
function drawCrop() {
  const b = CROP.box, el = $('#cropBox');
  el.style.left = b.x + 'px'; el.style.top = b.y + 'px'; el.style.width = b.w + 'px'; el.style.height = b.h + 'px';
}
(function cropDrag() {
  let mode = null, sx = 0, sy = 0, start = null;
  const stage = $('#cropStage');
  const pt = e => { const r = stage.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  stage.addEventListener('pointerdown', e => {
    if (!CROP.box) return;
    const h = e.target.dataset && e.target.dataset.h;
    if (!h && e.target.id !== 'cropBox') return;
    mode = h || 'move'; [sx, sy] = pt(e); start = {...CROP.box};
    stage.setPointerCapture(e.pointerId); e.preventDefault();
  });
  stage.addEventListener('pointermove', e => {
    if (!mode) return;
    const [x, y] = pt(e), dx = x - sx, dy = y - sy;
    const W = $('#cropImg').clientWidth, H = $('#cropImg').clientHeight, MIN = 40;
    let b = {...start};
    if (mode === 'move') {
      b.x = Math.min(Math.max(0, start.x + dx), W - b.w);
      b.y = Math.min(Math.max(0, start.y + dy), H - b.h);
    } else {
      const left = mode.includes('w'), top = mode.includes('n');
      // điểm neo = góc đối diện
      const ax = left ? start.x + start.w : start.x, ay = top ? start.y + start.h : start.y;
      let w = Math.max(MIN, left ? ax - (start.x + dx) : start.w + dx);
      let h = Math.max(MIN, top ? ay - (start.y + dy) : start.h + dy);
      if ($('#cropLock').checked) { if (w / h > CROP.ratio) w = h * CROP.ratio; else h = w / CROP.ratio; }
      w = Math.min(w, left ? ax : W - ax); h = Math.min(h, top ? ay : H - ay);
      if ($('#cropLock').checked) { if (w / h > CROP.ratio) w = h * CROP.ratio; else h = w / CROP.ratio; }
      b = {x: left ? ax - w : ax, y: top ? ay - h : ay, w, h};
    }
    CROP.box = b; drawCrop();
  });
  const end = () => { mode = null; };
  stage.addEventListener('pointerup', end); stage.addEventListener('pointercancel', end);
})();
$('#cropLock').onchange = () => {
  if (!$('#cropLock').checked || !CROP.box) return;
  const b = CROP.box, cx = b.x + b.w / 2, cy = b.y + b.h / 2;
  let w = b.w, h = w / CROP.ratio;
  if (h > b.h) { h = b.h; w = h * CROP.ratio; }
  CROP.box = {x: cx - w / 2, y: cy - h / 2, w, h}; drawCrop();
};
$('#cropClose').onclick = () => $('#cropModal').classList.add('hidden');
$('#cropModal').onclick = e => { if (e.target.id === 'cropModal') $('#cropModal').classList.add('hidden'); };
$('#cropSave').onclick = async () => {
  const img = $('#cropImg'), W = img.clientWidth, H = img.clientHeight, b = CROP.box;
  P = Object.assign(await api(`/api/projects/${P.id}/scenes/${CROP.sid}/crop`, {method: 'POST',
    json: {file: CROP.file, x: b.x / W, y: b.y / H, w: b.w / W, h: b.h / H}}), {job: P.job});
  $('#cropModal').classList.add('hidden');
  renderMedia();
};
$('#cropReset').onclick = async () => {
  P = Object.assign(await api(`/api/projects/${P.id}/scenes/${CROP.sid}/uncrop`, {method: 'POST', json: {file: CROP.file}}), {job: P.job});
  $('#cropModal').classList.add('hidden');
  renderMedia();
};

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
  const cur = P.bgm?.file ?? '';
  $('#bgmSel').innerHTML = `<option value="__auto__">🎵 Tự chọn theo thể loại (nhạc tool soạn sẵn)</option>
    <option value="">— Không dùng nhạc nền —</option>` +
    list.map(x => `<option value="${esc(x)}">${x.endsWith('(tool).m4a') ? '🎼 ' : '📁 '}${esc(x.replace(' (tool).m4a', ''))}</option>`).join('');
  $('#bgmSel').value = cur;
  const real = cur === '__auto__' ? (P.bgm_resolved || '') : cur;
  $('#bgmPrev').src = real ? `/library/bgm/${encodeURIComponent(real)}` : '';
  $('#bgmHint').textContent = cur === '__auto__'
    ? (real ? `Video này sẽ dùng: ${real.replace(' (tool).m4a', '')}. Nhạc do tool tự soạn, không bản quyền.`
            : 'Nhạc đang được soạn lần đầu (khoảng 2 phút), mở lại tab này sau ít phút.')
    : (list.some(x => x.endsWith('(tool).m4a')) ? '🎼 = nhạc tool tự soạn (không bản quyền) · 📁 = nhạc bạn upload' : '');
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
  const copyRow = (x) => `<div class="cap"><div><div class="ja">${esc(x.text).replace(/\n/g, '<br>')}</div><div class="vi">${esc(x.vi || '')}</div></div>
      <button class="soft small" data-copy="${esc(x.text)}">📋 Copy</button></div>`;
  $('#tkPins').innerHTML = (t.pinned || []).map(copyRow).join('') || '<span class="muted">Bấm “🔁 Tạo bộ khác” để có gợi ý bình luận ghim.</span>';
  $('#tkCovers').innerHTML = (t.covers || []).map(copyRow).join('') || '<span class="muted">Bấm “🔁 Tạo bộ khác” để có gợi ý chữ ảnh bìa.</span>';
  $$('#tkPins [data-copy], #tkCovers [data-copy]').forEach(b => b.onclick = async () => {
    await navigator.clipboard.writeText(b.dataset.copy); b.textContent = '✅ Đã copy'; setTimeout(() => b.textContent = '📋 Copy', 1500);
  });
  const ko = P.lang === 'ko', old = P.audience === '35plus';
  $('#tkTime').innerHTML = old
    ? `${ko ? '🇰🇷' : '🇯🇵'} Khán giả 35+: <b>21:00–23:00</b> (xem sau khi xong việc nhà, đông nhất) · <b>12:00–13:00</b> (nghỉ trưa) · <b>7:00–8:30</b> (đi làm).
       Cuối tuần: <b>9:00–11:00</b> sáng.<br>• Đăng đều 1 khung giờ để người theo dõi quen.
       • Giữ 1 chủ đề kênh (VD “huyền thoại bóng chày Showa–Heisei”) để TikTok học đúng nhóm khán giả.
       • Muốn chắc chắn tới người 35+: dùng <b>TikTok Promote</b> (trả phí ít) chọn độ tuổi 35–44, 45–54, 55+ cho vài video đầu.`
    : `${ko ? '🇰🇷' : '🇯🇵'} <b>18:00–19:00</b> (tan học, tan làm) · <b>21:00–23:00</b> (đông nhất) · <b>12:00–13:00</b> (nghỉ trưa).<br>
       • Đăng đều 1 khung giờ · giữ 1 chủ đề kênh để TikTok học đúng nhóm khán giả.`;
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
  P = Object.assign(await api(`/api/projects/${P.id}`), {job: P.job});
  loadBgm();
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
  box.classList.toggle('done', j.status === 'done');
  $('#jobBar').style.width = Math.round((j.progress || 0) * 100) + '%';
  const lines = j.log || [];
  const last = (lines[lines.length - 1] || '').replace(/^\[[\d:]+\]\s*/, '');
  $('#jobLast').textContent = j.status === 'error' ? '⚠️ ' + (j.error || last) : last || 'Đang chạy...';
  $('#jobLog').textContent = lines.join('\n');
  $('#jobLog').scrollTop = 1e9;
  $$('#proj button.primary, #btnRegen').forEach(b => { b.disabled = j.status === 'running'; });
}
function startPoll() {
  clearInterval(pollTimer);
  const id = P.id;
  watchJob(id);
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

// ------------------------------------------------------------- 🔔 thông báo khi xong việc
const JOB_MSG = {
  script: ['✍️', 'Đã viết xong content', 'Vào bước 1 để đọc & duyệt'],
  tts: ['🎙️', 'Đã đọc xong giọng', 'Vào bước 2 để nghe thử'],
  media: ['🖼️', 'Đã tìm xong ảnh & video', 'Vào bước 3 để xem lại'],
  render: ['🎬', 'Đã xuất xong video!', 'Vào bước 4 để xem & tải video'],
  tiktok: ['#️⃣', 'Đã tạo xong title & hashtag', 'Vào bước 5 để copy đi đăng'],
};
const JOB_TAB = {script: 'script', tts: 'voice', media: 'media', render: 'render', tiktok: 'tiktok'};
const WATCH = new Set();
let watchTimer = null;
function watchJob(pid) {
  WATCH.add(pid);
  if (!watchTimer) watchTimer = setInterval(checkWatch, 2000);
}
async function checkWatch() {
  for (const pid of [...WATCH]) {
    let j;
    try { j = await (await fetch(`/api/projects/${pid}/job`)).json(); } catch { continue; }
    if (j.status === 'running') continue;
    WATCH.delete(pid);
    if (j.status !== 'done' && j.status !== 'error') continue;
    const title = (PROJECTS.find(p => p.id === pid) || (P && P.id === pid ? P : {})).title || 'Video của bạn';
    const m = JOB_MSG[j.name] || ['✅', 'Đã xong', ''];
    if (j.status === 'done') {
      notify(m[0], m[1], `${title} · ${m[2]}`, 'ok', () => openProject(pid).then(() => setTab(JOB_TAB[j.name] || 'script')));
    } else {
      notify('⚠️', 'Có lỗi: ' + m[1].replace('Đã ', '').replace(' xong', ''), `${title} · ${(j.error || '').slice(0, 120)}`, 'err',
             () => openProject(pid));
    }
    loadList();
  }
  if (!WATCH.size) { clearInterval(watchTimer); watchTimer = null; }
}

// tiếng "ting ting" (tự tạo, không cần file)
function chime(ok = true) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    (ok ? [880, 1320] : [440, 330]).forEach((f, i) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = f; o.type = 'sine';
      const t = ctx.currentTime + i * 0.18;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
      o.connect(g).connect(ctx.destination); o.start(t); o.stop(t + 0.55);
    });
    setTimeout(() => ctx.close(), 1500);
  } catch {}
}

// tên tab nhấp nháy khi bạn đang ở tab khác
const BASE_TITLE = document.title;
let flashTimer = null;
function flashTitle(text) {
  clearInterval(flashTimer);
  let on = false;
  flashTimer = setInterval(() => { document.title = (on = !on) ? text : BASE_TITLE; }, 1000);
  document.title = text;
}
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) { clearInterval(flashTimer); document.title = BASE_TITLE; }
});

function notify(icon, title, body, kind = 'ok', onClick = null) {
  chime(kind !== 'err');
  // hộp thông báo trong trang
  const t = document.createElement('div');
  t.className = 'toast ' + kind;
  t.innerHTML = `<span class="ic">${icon}</span><div><b>${esc(title)}</b><small>${esc(body)}</small></div><button class="x" title="Đóng">✕</button>`;
  t.onclick = e => { if (e.target.classList.contains('x')) { t.remove(); return; } t.remove(); onClick && onClick(); };
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), 12000);
  // đang ở tab khác → nhấp nháy tên tab + thông báo của máy
  if (document.hidden) {
    flashTitle(`${kind === 'err' ? '⚠️ Lỗi' : '✅ Xong'}! ${title}`);
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        const n = new Notification(`${icon} ${title}`, {body, tag: 'shorts-maker-' + Date.now()});
        n.onclick = () => { window.focus(); n.close(); onClick && onClick(); };
      } catch {}
    }
  }
}

// nút chuông: xin phép hiện thông báo của máy
function drawNotifyBtn() {
  const b = $('#btnNotify');
  if (!('Notification' in window)) { b.classList.add('hidden'); return; }
  const p = Notification.permission;
  b.classList.toggle('on', p === 'granted');
  b.textContent = p === 'granted' ? '🔔 Thông báo: bật' : p === 'denied' ? '🔕 Thông báo bị chặn' : '🔔 Bật thông báo';
  b.title = p === 'denied'
    ? 'Trình duyệt đang chặn thông báo. Bấm biểu tượng ổ khóa cạnh địa chỉ trang → Thông báo → Cho phép, rồi tải lại trang.'
    : 'Báo khi tool làm xong việc, kể cả khi bạn đang ở tab khác';
}
$('#btnNotify').onclick = async () => {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') await Notification.requestPermission();
  drawNotifyBtn();
  if (Notification.permission === 'granted') notify('🔔', 'Đã bật thông báo', 'Tool sẽ báo mỗi khi làm xong một việc.', 'info');
  else if (Notification.permission === 'denied') alert($('#btnNotify').title);
};
drawNotifyBtn();

// ------------------------------------------------------------- tạo mới, cài đặt
// ---- chip chọn nhanh (ô chọn vẫn còn, chỉ ẩn đi)
var CHIPS = [];
function chipify(id) {
  const sel = $('#' + id);
  if (!sel || sel.dataset.chips) return;
  sel.dataset.chips = '1';
  sel.classList.add('hidden');
  const box = document.createElement('div');
  box.className = 'chips';
  sel.after(box);
  const draw = () => {
    box.innerHTML = [...sel.options].map(o =>
      `<button type="button" class="chip-btn ${o.value === sel.value ? 'on' : ''}" data-v="${esc(o.value)}">${esc(o.textContent)}</button>`).join('');
    box.querySelectorAll('button').forEach(b => b.onclick = () => {
      sel.value = b.dataset.v; sel.dispatchEvent(new Event('change')); refreshChips();
    });
  };
  CHIPS.push(draw); draw();
}
function refreshChips() { CHIPS.forEach(f => f()); }
['newGenre', 'rankN', 'newsDays', 'newsCount', 'newDur'].forEach(chipify);

// ---- tin tức
function newsParams() {
  return {region: $('#newsRegion').value, custom_region: $('#newsCustom').value.trim(),
          days: +$('#newsDays').value, category: $('#newsCat').value, lang: $('#newLang').value,
          count: +$('#newsCount').value};
}
function toggleNewsBox() {
  refreshChips();
  $('#rankBox').classList.toggle('hidden', $('#newGenre').value !== 'ranking');
  $('#sportBox').classList.toggle('hidden', ['news', 'brand', 'history'].includes($('#newGenre').value));
  const isNews = $('#newGenre').value === 'news';
  $('#newsBox').classList.toggle('hidden', !isNews);
  $('#newTopic').placeholder = isNews ? 'Để trống = AI tự chọn tin nóng nhất. Hoặc chọn tin đã quét / gõ chủ đề tin.'
    : 'VD: kể chuyện Kawamura Yuki được Grizzlies ký hợp đồng...';
}
async function initNews() {
  const d = await api('/api/news/regions');
  $('#newsRegion').innerHTML = d.regions.map(r => `<option value="${r.id}">${r.vi}</option>`).join('');
  $('#newsCat').innerHTML = d.categories.map(c => `<option value="${c.id}">${c.vi}</option>`).join('');
  LANGS = d.langs;
  const sportOpts = d.sports.map(s => `<option value="${s.id}">${s.vi}</option>`).join('');
  $('#newSport').innerHTML = sportOpts; $('#pSport').innerHTML = sportOpts;
  try { const ds = JSON.parse(localStorage.getItem('shorts_defaults') || '{}').sport; $('#newSport').value = ds || 'basketball'; } catch { $('#newSport').value = 'basketball'; }
  if (P) $('#pSport').value = P.sport || 'other';
  chipify('newSport');
  const langOpts = d.langs.map(l => `<option value="${l.id}">${l.vi}</option>`).join('');
  $('#newLang').innerHTML = langOpts; $('#pLang').innerHTML = langOpts; $('#ideaLang').innerHTML = langOpts;
  if (P) renderTwinBtns();
  try { const dl = JSON.parse(localStorage.getItem('shorts_defaults') || '{}').lang; if (dl) $('#newLang').value = dl; } catch {}
  chipify('newLang');
  if (P) $('#pLang').value = P.lang || 'ja';
  try {
    const n = (JSON.parse(localStorage.getItem('shorts_defaults') || '{}')).news;
    if (n) { $('#newsRegion').value = n.region; $('#newsDays').value = n.days; $('#newsCat').value = n.category; $('#newsCustom').value = n.custom_region || ''; }
  } catch {}
  $('#newsCustom').classList.toggle('hidden', $('#newsRegion').value !== 'custom');
}
$('#newGenre').onchange = toggleNewsBox;
$('#newsCount').onchange = () => {
  const n = +$('#newsCount').value;
  $('#newsHint').textContent = n > 1 ? `Điểm tin: bấm chọn tối đa ${n} tin ở trên, hoặc để trống → AI tự chọn ${n} tin nóng nhất.`
    : 'Chọn 1 tin ở trên, hoặc để trống chủ đề → AI tự chọn tin nóng nhất.';
};
$('#newsRegion').onchange = () => $('#newsCustom').classList.toggle('hidden', $('#newsRegion').value !== 'custom');
$('#btnScan').onclick = async () => {
  const b = $('#btnScan'); b.disabled = true; b.textContent = '⏳ Đang quét báo (1–2 phút)...';
  $('#newsList').innerHTML = '';
  try {
    const items = await api('/api/news/suggest', {method: 'POST', json: newsParams()});
    notify('📰', `Đã quét xong ${items.length} tin`, 'Bấm chọn tin để làm video', 'ok', () => openCreate());
    $('#newsList').innerHTML = items.map((n, i) => `<div class="news" data-i="${i}">
      <b>${esc(n.headline_vi)}</b>${esc(n.headline || n.headline_ja)}<br><small>${esc(n.date || '')} · ${esc(n.source || '')} · 🔥${n.score ?? ''}</small>
      <div>${esc(n.summary_vi || '')}</div></div>`).join('') || '<small>Không tìm thấy tin nào.</small>';
    $$('#newsList .news').forEach(el => el.onclick = () => {
      const multi = +$('#newsCount').value > 1;
      if (multi) el.classList.toggle('sel');
      else $$('#newsList .news').forEach(x => x.classList.toggle('sel', x === el));
      const picked = $$('#newsList .news.sel').map(x => items[+x.dataset.i]);
      $('#newTopic').value = picked.map((n, k) => (multi ? `${k + 1}. ` : '') +
        `${n.headline || n.headline_ja}\n${n.date || ''} ${n.source || ''}\n${n.url || ''}`).join('\n');
    });
  } finally { b.disabled = false; b.textContent = '🔎 Quét tin mới nhất'; }
};
initNews().then(() => { toggleNewsBox(); refreshChips(); });

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
  const video_pct = +$('#newRatio').value, genre = $('#newGenre').value, lang = $('#newLang').value;
  const news = genre === 'news' ? newsParams() : null;
  try { localStorage.setItem('shorts_defaults', JSON.stringify({video_pct, genre, news, lang})); } catch {}
  const ranking_n = genre === 'ranking' ? +$('#rankN').value : null;
  const sport = ['news', 'brand', 'history'].includes(genre) ? 'other' : $('#newSport').value;
  try { const d0 = JSON.parse(localStorage.getItem('shorts_defaults') || '{}'); d0.sport = $('#newSport').value; localStorage.setItem('shorts_defaults', JSON.stringify(d0)); } catch {}
  const p = await api('/api/projects', {method: 'POST', json: {title: $('#newTitle').value, topic: $('#newTopic').value, duration: dur, genre, video_pct, news, lang, ranking_n, sport, audience: $('#newAudience').value}});
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
// ------------------------------------------------------------- gợi ý ý tưởng
const GENRE_VI = {sports: '⚾ Thể thao', biography: '👤 Tiểu sử', brand: '🏢 Thương hiệu', history: '🏯 Lịch sử', news: '📰 Tin tức', ranking: '🏆 Top', general: '💡 Chủ đề chung'};
function showOnly(id) {
  const changed = $(id).classList.contains('hidden');
  ['#empty', '#proj', '#settings', '#ideas', '#create'].forEach(x => $(x).classList.toggle('hidden', x !== id));
  if (changed) window.scrollTo(0, 0);   // chỉ cuộn lên đầu khi đổi màn hình
}
function openCreate() {
  showOnly('#create'); toggleNewsBox(); refreshChips();
  $$('#projList li').forEach(li => li.classList.remove('active'));
}
$('#btnNew').onclick = openCreate;
$('#btnNewEmpty').onclick = openCreate;
$('#btnIdeasEmpty').onclick = () => $('#btnIdeasOpen').click();
$('#btnCreateCancel').onclick = () => showOnly(P ? '#proj' : '#empty');
$('#btnIdeasOpen').onclick = () => {
  showOnly('#ideas');
  $('#ideaLang').value = $('#newLang').value;
  try { const s = JSON.parse(localStorage.getItem('shorts_ideas') || 'null'); if (s && !$('#ideaList').innerHTML) renderIdeas(s); } catch {}
};
$('#btnIdeasClose').onclick = () => showOnly(P ? '#proj' : '#empty');
$$('.presets a').forEach(a => a.onclick = () => { $('#ideaNiche').value = a.dataset.n; });
function renderIdeas(list) {
  $('#ideaList').innerHTML = list.map((x, i) => `<div class="idea">
    <div class="body">
      <div class="t">${esc(x.title)}</div><div class="vi">${esc(x.title_vi || '')}</div>
      <div class="why">💬 ${esc(x.why_vi || '')}</div>
      <div class="meta"><span class="badge">${GENRE_VI[x.genre] || x.genre}${x.genre === 'ranking' && x.ranking_n ? ' ' + x.ranking_n : ''}</span>
        ${x.timely ? '<span class="badge hot">🔥 đang hot</span>' : '<span class="badge">♻️ không lỗi thời</span>'}
        điểm ${x.score ?? '-'}/10</div>
    </div>
    <button class="primary" data-i="${i}">🎬 Làm video này</button></div>`).join('') || '<p class="muted">Không có gợi ý nào.</p>';
  $$('#ideaList button[data-i]').forEach(b => b.onclick = () => {
    const x = list[+b.dataset.i];
    $('#newLang').value = $('#ideaLang').value;
    $('#newGenre').value = x.genre; toggleNewsBox();
    if (x.genre === 'ranking' && x.ranking_n) {
      const n = String(x.ranking_n); if ([...$('#rankN').options].some(o => o.value === n)) $('#rankN').value = n;
    }
    $('#newTitle').value = x.title; $('#newTopic').value = x.topic || '';
    const niche = $('#ideaNiche').value.toLowerCase();
    const sp = /m-1|hài|お笑い|芸人|漫才|コント/.test(niche) ? 'owarai' : /k-pop|kpop|케이팝|bts|blackpink/.test(niche) ? 'kpop' : /idol|アイドル|akb|乃木坂|nogizaka/.test(niche) ? 'idol' : /sumo|相撲/.test(niche) ? 'sumo' : /bóng chày|野球|npb|kbo|mlb/.test(niche) ? 'baseball'
      : /bóng đá|サッカー|league|k league/.test(niche) && !/b\.league/.test(niche) ? 'soccer' : /bóng rổ|バスケ|nba/.test(niche) ? 'basketball' : null;
    if (sp) $('#newSport').value = sp;
    openCreate();
    $('#newTitle').focus();
  });
}
$('#btnIdeas').onclick = async () => {
  const b = $('#btnIdeas'); b.disabled = true; b.textContent = '⏳ Claude đang tra cứu (1–2 phút)...';
  try {
    const list = await api('/api/ideas', {method: 'POST', json: {lang: $('#ideaLang').value, niche: $('#ideaNiche').value,
      genre: $('#ideaGenre').value, count: +$('#ideaCount').value, audience: $('#ideaAudience').value}});
    try { localStorage.setItem('shorts_ideas', JSON.stringify(list)); } catch {}
    notify('💡', `Đã có ${list.length} ý tưởng`, 'Bấm “Làm video này” ở ý tưởng bạn thích', 'ok', () => showOnly('#ideas'));
    renderIdeas(list);
  } finally { b.disabled = false; b.textContent = '✨ Gợi ý ngay'; }
};

$('#lnkSettings').onclick = async e => {
  e.preventDefault();
  const s = await api('/api/settings');
  $('#sModel').value = s.claude_model;
  let srcOn = s.sources_v2 ? (s.image_sources || []) : [...(s.image_sources || []), 'naver', 'news'];
  if (!s.sources_v3) srcOn = [...srcOn, 'google'];
  $$('.src').forEach(c => c.checked = srcOn.includes(c.value));
  $('#sEnc').value = s.video_encoder; $('#sSize').value = s.subtitle_size; $('#sMediaH').value = s.media_height; $('#sMediaHK').value = s.media_height_korea; $('#sGap').value = s.sub_gap; $('#sFont').value = s.subtitle_font;
  $('#sHL').checked = s.use_claude_for_highlight; $('#sFB').checked = s.facebook_video !== false; $('#sVerify').checked = s.verify_person_video !== false; $('#sPick').checked = s.smart_image_pick !== false; $('#sFact').checked = s.fact_check !== false; $('#sRet').checked = s.retention_edit !== false; $('#sZoom').checked = !!s.image_zoom; $('#sSteps').value = s.tts_num_step;
  showOnly('#settings');
  loadRefs();
  $('#checkOut').textContent = 'Đang kiểm tra...';
  const c = await api('/api/check');
  $('#checkOut').textContent = [
    `FFmpeg: ${c.ffmpeg ? '✅' : '❌ chưa cài'}`, `Claude CLI: ${c.claude ? '✅' : '❌ chưa cài'}`,
    `Font sub: ${c.font ? '✅' : '❌ chạy install.bat lại'}`, `OmniVoice: ${c.omnivoice ? '✅' : '❌ chưa cài'}`,
    `GPU NVIDIA: ${c.cuda ? '✅ ' + c.gpu : '❌ không thấy (giọng đọc sẽ rất chậm)'}`].join('\n');
};
$('#btnSaveSettings').onclick = async () => {
  await api('/api/settings', {method: 'PUT', json: {claude_model: $('#sModel').value.trim(),
    image_sources: $$('.src').filter(c => c.checked).map(c => c.value), sources_v2: true, sources_v3: true, video_encoder: $('#sEnc').value, subtitle_size: +$('#sSize').value, media_height: +$('#sMediaH').value, media_height_korea: +$('#sMediaHK').value, sub_gap: +$('#sGap').value,
    subtitle_font: $('#sFont').value.trim(), use_claude_for_highlight: $('#sHL').checked, facebook_video: $('#sFB').checked, verify_person_video: $('#sVerify').checked, smart_image_pick: $('#sPick').checked, fact_check: $('#sFact').checked, retention_edit: $('#sRet').checked, image_zoom: $('#sZoom').checked, tts_num_step: +$('#sSteps').value}});
  alert('Đã lưu');
};
// ---- thư viện kịch bản mẫu
async function loadRefs() {
  const list = await api('/api/refs');
  $('#refList').innerHTML = list.length ? list.map(r => `<details class="ref"><summary><b>${esc(r.title)}</b>
      <span class="muted">· ${r.lang === 'ko' ? '🇰🇷' : '🇯🇵'} ${GENRE_VI[r.genre] || r.genre}${r.views ? ' · ' + esc(r.views) + ' view' : ''} · ${r.text.length} chữ</span>
      <button class="ghost small" data-del="${r.id}" title="Xóa">🗑</button></summary>
      ${r.note ? `<p class="hint">${esc(r.note)}</p>` : ''}<p class="ref-text">${esc(r.text)}</p></details>`).join('')
    : '<p class="muted">Chưa có kịch bản mẫu.</p>';
  $$('#refList [data-del]').forEach(b => b.onclick = async e => {
    e.preventDefault();
    if (!confirm('Xóa kịch bản mẫu này?')) return;
    await api('/api/refs/' + b.dataset.del, {method: 'DELETE'}); loadRefs();
  });
}
$('#refAdd').onclick = async () => {
  const text = $('#refText').value.trim();
  if (text.length < 40) return alert('Kịch bản quá ngắn');
  await api('/api/refs', {method: 'POST', json: {title: $('#refTitle').value.trim(), views: $('#refViews').value.trim(),
    lang: $('#refLang').value, genre: $('#refGenre').value, text}});
  $('#refTitle').value = $('#refViews').value = $('#refText').value = '';
  loadRefs();
};
$('#btnGVerify').onclick = async e => {
  e.preventDefault();
  await api('/api/google/verify', {method: 'POST'});
  alert('Cửa sổ Google (chính là cửa sổ tool dùng để tìm ảnh) sẽ hiện lên.\n• Nếu Google hỏi “Tôi không phải robot” → tích vào, thấy kết quả ảnh là xong, cửa sổ tự ẩn đi.\n• Nếu không bị hỏi → cửa sổ hiện 2–3 giây rồi tự ẩn: Google đang chạy tốt.\nĐừng đóng cửa sổ đó bằng dấu ✕ nhé (tool vẫn đang dùng).');
};
$('#btnCloseSettings').onclick = () => showOnly(P ? '#proj' : '#empty');

loadList();
api('/api/check').then(c => $('#checkBadge').textContent = (c.ffmpeg && c.claude && c.omnivoice && c.cuda) ? '✅ sẵn sàng' : '⚠️ xem cài đặt');
