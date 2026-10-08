/* Habit Corps – Oberfläche */

const $ = (id) => document.getElementById(id);
const fmt = (n) => Number(n).toLocaleString("de-AT", { maximumFractionDigits: 2 });
const fmtMult = (m) => "×" + Number(m).toLocaleString("de-AT", { minimumFractionDigits: 1 });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const CHECK_SVG = `<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;

const QUOTES = [
  "Haltung annehmen, Rekrut! Die Missionen warten.",
  "Disziplin schlägt Motivation. Jeden einzelnen Tag.",
  "Kein Habit bleibt zurück!",
  "Wer heute abhakt, wird morgen befördert.",
  "Ein verpasster Tag – und alle Streaks fallen. Bleib wachsam!",
];

let state = null;
let shownXp = 0;
let mascotTimer = null;
let pendingDelete = null;

/* ---------- Server ---------- */
async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || "Unbekannter Fehler");
  return json;
}

async function refresh() {
  state = await api("/api/state");
  render();
}

/* ---------- Darstellung ---------- */
function render() {
  const s = state;
  $("streak").textContent = s.streak;
  setXp(s.month.xp, false);
  $("rank-icon").innerHTML = insigniaSVG(s.rank.index);
  $("rank-name").textContent = s.rank.name;

  // Monatsfortschritt
  $("month-label").textContent = s.month.label;
  $("days-left").textContent = s.month.days_left === 0 ? "letzter Tag" : `noch ${s.month.days_left} Tage`;
  $("progress-fill").style.width = Math.min(100, s.month.percent) + "%";
  $("progress-ticks").innerHTML = s.ranks
    .filter((r) => r.pct)
    .map((r) => `<span style="left:${r.pct}%" title="${esc(r.name)}"></span>`).join("");
  $("xp-text").textContent = fmt(s.month.xp);
  $("max-text").textContent = fmt(s.month.max_xp);
  $("pct-text").textContent = fmt(s.month.percent);
  $("next-rank").innerHTML = s.next_rank
    ? `Noch <b>${fmt(s.next_rank.xp_needed)} XP</b> bis <b>${esc(s.next_rank.name)}</b>`
    : `General wird am Monatsende vergeben: jeden Tag mind. 5 Missionen mit ×3,0.`;
  $("blocked").hidden = !s.blocked;
  $("blocked").textContent = s.blocked ? "🔒 " + s.blocked : "";

  renderLadder();
  renderMissions();
  renderOrders();
  renderWarning();
  setMascotIdle();
}

function setXp(target, animate) {
  if (!animate) { shownXp = target; $("xp").textContent = fmt(target); return; }
  const start = shownXp, t0 = performance.now(), dur = 700;
  const step = (t) => {
    const p = Math.min(1, (t - t0) / dur);
    $("xp").textContent = fmt(Math.round(start + (target - start) * p));
    if (p < 1) requestAnimationFrame(step); else { shownXp = target; $("xp").textContent = fmt(target); }
  };
  requestAnimationFrame(step);
  const chip = document.querySelector(".chip-xp");
  chip.classList.remove("pulse"); void chip.offsetWidth; chip.classList.add("pulse");
}

function renderLadder() {
  const cur = state.rank.index;
  $("ladder").innerHTML = state.ranks.slice().reverse().map((r) => {
    const cls = r.index === cur ? "current" : r.index < cur ? "reached" : "future";
    const xp = r.xp === null ? "Bedingung" : r.pct === 0 ? "Start" : `${r.pct} %`;
    const lock = r.locked_by_prev ? `<span class="lock" title="Benötigt im Vormonat mind. ${esc(state.ranks[r.prev].name)}">🔒</span>` : "";
    return `<li class="${cls}">${insigniaSVG(r.index)}<span class="lname">${esc(r.name)}</span>${lock}<span class="lxp">${xp}</span></li>`;
  }).join("");
}

function renderMissions() {
  const list = $("missions");
  $("empty").hidden = state.habits.length > 0;
  list.innerHTML = state.habits.map((h) => {
    const hint = h.next_step
      ? `<span class="tag hint">noch ${h.next_step.days} ${h.next_step.days === 1 ? "Tag" : "Tage"} bis ${fmtMult(h.next_step.multiplier)}</span>`
      : `<span class="tag hint">Höchster Multiplikator!</span>`;
    const reminder = h.reminder
      ? `<button class="icon-btn" data-act="reminder" data-id="${h.id}">🔔 ${h.reminder}</button>`
      : `<button class="icon-btn" data-act="reminder" data-id="${h.id}">🔕 Erinnerung</button>`;
    const del = pendingDelete === h.id
      ? `<button class="icon-btn danger" data-act="delete-confirm" data-id="${h.id}">Wirklich löschen?</button>`
      : `<button class="icon-btn" data-act="delete" data-id="${h.id}">🗑 Löschen</button>`;
    return `
      <li class="mission ${h.done_today ? "done" : ""}" data-id="${h.id}">
        <button class="check" data-act="done" data-id="${h.id}" ${h.done_today ? "disabled" : ""}
          aria-label="${esc(h.name)} als erledigt markieren">${CHECK_SVG}</button>
        <div class="mission-body">
          <div class="mission-name">${esc(h.name)}</div>
          ${h.goal ? `<div class="mission-goal">${esc(h.goal)}</div>` : ""}
          <div class="tags">
            <span class="tag fire">🔥 ${h.streak} ${h.streak === 1 ? "Tag" : "Tage"}</span>
            <span class="tag mult">${fmtMult(h.done_today ? h.multiplier : h.next_multiplier)}</span>
            ${hint}
          </div>
        </div>
        <div class="mission-tools">${reminder}${del}</div>
      </li>`;
  }).join("");
}

function renderOrders() {
  $("no-orders").hidden = state.orders.length > 0;
  $("orders").innerHTML = state.orders.map((o) => `
    <li class="order">
      <div class="medal">${insigniaSVG(o.rank)}</div>
      <div>
        <div class="order-month">${esc(o.label)}</div>
        <div class="order-meta">${esc(o.rank_name)} · ${fmt(o.xp)} XP (${fmt(o.percent)} %)</div>
      </div>
    </li>`).join("");
}

function renderWarning() {
  const w = $("warning");
  w.className = "warning";
  if (!state.habits.length) { w.hidden = true; return; }
  w.hidden = false;
  if (state.open_today === 0) {
    w.classList.add("ok");
    w.textContent = "✅ Alle Missionen für heute erfüllt. Weggetreten, Soldat!";
  } else if (state.reset_yesterday && state.streak === 0) {
    w.classList.add("lost");
    w.textContent = `💥 Gestern wurde eine Mission verpasst – alle Streaks stehen wieder auf 0. Noch ${state.open_today} offen.`;
  } else {
    w.textContent = `⚠️ Noch ${state.open_today} ${state.open_today === 1 ? "Mission" : "Missionen"} offen. Verpasst du eine, fallen ALLE Streaks auf 0.`;
  }
}

/* ---------- Maskottchen ---------- */
function setMascot(mood, text) {
  const m = $("mascot");
  m.className = "mascot " + (mood ? "mood-" + mood : "");
  if (text) $("bubble").textContent = text;
}

function setMascotIdle() {
  if (mascotTimer) return;   // gerade läuft eine Reaktion
  if (state.reset_yesterday && state.streak === 0 && state.habits.length) {
    setMascot("sad", "Ein Soldat lässt keinen Kameraden zurück … und keine Mission. Neuer Anlauf, heute!");
  } else if (state.habits.length && state.open_today === 0) {
    setMascot("salute", "Alle Missionen erfüllt. Ich bin stolz auf dich, " + state.rank.name + "!");
  } else {
    const day = Number(state.today.slice(-2));
    setMascot("", QUOTES[day % QUOTES.length]);
  }
}

function mascotReact(mood, text, ms = 1600) {
  clearTimeout(mascotTimer);
  setMascot(mood, text);
  mascotTimer = setTimeout(() => { mascotTimer = null; setMascotIdle(); }, ms);
}

/* ---------- Aktionen ---------- */
async function completeHabit(id, button) {
  button.disabled = true;
  const rect = button.getBoundingClientRect();
  try {
    const res = await api(`/api/habits/${id}/done`, {});
    const r = res.result;
    showXpFloat(r.xp, rect);                       // NFR-02: startet sofort
    const before = shownXp;
    state = res.state;
    render();
    shownXp = before;
    setXp(state.month.xp, true);
    mascotReact("salute", `+${fmt(r.xp)} XP! Multiplikator ${fmtMult(r.multiplier)}, Streak ${r.streak}.`);
    if (r.promoted) setTimeout(() => showPromotion(state.rank), 900);
  } catch (e) {
    button.disabled = false;
    toast(e.message);
  }
}

function showXpFloat(xp, rect) {
  const el = document.createElement("div");
  el.className = "xp-float";
  el.textContent = `+${fmt(xp)} XP`;
  el.style.left = rect.left + rect.width / 2 - 40 + "px";
  el.style.top = rect.top - 10 + "px";
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1200);
}

function showPromotion(rank) {
  $("promo-insignia").innerHTML = insigniaSVG(rank.index);
  $("promo-rank").textContent = rank.name;
  $("promo-grade").textContent = "Dienstgrad " + rank.grade;
  $("promo-anecdote").textContent = "📜 " + rank.anecdote;
  const colors = ["#F5B700", "#6B8E23", "#E5483A", "#2E86DE", "#FF9600"];
  $("confetti").innerHTML = Array.from({ length: 40 }, (_, i) =>
    `<i style="left:${Math.random() * 100}%;background:${colors[i % colors.length]};animation-delay:${Math.random() * .5}s"></i>`).join("");
  $("promo").hidden = false;
  mascotReact("salute", `Beförderung zum ${rank.name}! Salut!`, 3000);
}

async function addHabit(ev) {
  ev.preventDefault();
  const err = $("f-error");
  err.hidden = true;
  try {
    const reminder = $("f-reminder").value || null;
    const res = await api("/api/habits", {
      name: $("f-name").value, goal: $("f-goal").value, reminder,
    });
    if (reminder) askNotificationPermission();
    state = res.state;
    closeForm();
    render();
    mascotReact("salute", `Neue Mission „${res.habit.name}“ angenommen!`);
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
}

function openForm() {
  $("habit-form").hidden = false;
  $("open-form").hidden = true;
  $("f-name").focus();
}

function closeForm() {
  $("habit-form").reset();
  $("c-name").textContent = "0";
  $("c-goal").textContent = "0";
  $("f-error").hidden = true;
  $("habit-form").hidden = true;
  $("open-form").hidden = false;
}

function editReminder(id, btn) {
  const h = state.habits.find((x) => x.id === id);
  btn.innerHTML = `<input type="time" value="${h.reminder || ""}"> <span>✓</span>`;
  const input = btn.querySelector("input");
  input.focus();
  const save = async () => {
    try {
      const res = await api(`/api/habits/${id}/reminder`, { reminder: input.value || null });
      if (input.value) askNotificationPermission();
      state = res.state;
      render();
      toast(input.value ? `Erinnerung um ${input.value} gesetzt.` : "Erinnerung entfernt.");
    } catch (e) { toast(e.message); }
  };
  input.addEventListener("change", save);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") save(); if (e.key === "Escape") render(); });
}

async function deleteHabit(id) {
  try {
    const res = await api(`/api/habits/${id}/delete`, {});
    pendingDelete = null;
    state = res.state;
    render();
  } catch (e) { toast(e.message); }
}

/* ---------- Erinnerungen (FR-13 bis FR-15) ---------- */
function askNotificationPermission() {
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
}

function storeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function storeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* egal */ } }

function checkReminders() {
  if (!state) return;
  const now = new Date();
  const hhmm = now.toTimeString().slice(0, 5);
  for (const h of state.habits) {
    if (!h.reminder || h.done_today || hhmm < h.reminder) continue;
    const key = `reminded-${h.id}-${state.today}`;
    if (storeGet(key)) continue;
    storeSet(key, "1");
    const text = `Mission „${h.name}“ ist noch offen. Streak halten, Soldat!`;
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Habit Corps – Antreten!", { body: text });
    }
    toast("🔔 " + text, 6000);
    mascotReact("", text, 6000);
  }
}

/* ---------- Kleinkram ---------- */
let toastTimer = null;
function toast(text, ms = 3000) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), ms);
}

/* ---------- Start ---------- */
document.addEventListener("DOMContentLoaded", () => {
  $("mascot").innerHTML = mascotSVG();
  $("open-form").addEventListener("click", openForm);
  $("cancel-form").addEventListener("click", closeForm);
  $("habit-form").addEventListener("submit", addHabit);
  $("f-name").addEventListener("input", (e) => ($("c-name").textContent = e.target.value.length));
  $("f-goal").addEventListener("input", (e) => ($("c-goal").textContent = e.target.value.length));
  $("promo-close").addEventListener("click", () => ($("promo").hidden = true));

  $("missions").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn || e.target.tagName === "INPUT") return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    if (act === "done") completeHabit(id, btn);
    if (act === "reminder") editReminder(id, btn);
    if (act === "delete") { pendingDelete = id; renderMissions(); setTimeout(() => { if (pendingDelete === id) { pendingDelete = null; renderMissions(); } }, 4000); }
    if (act === "delete-confirm") deleteHabit(id);
  });

  refresh().catch((e) => toast("Server nicht erreichbar: " + e.message, 8000));
  setInterval(checkReminders, 20000);
  setInterval(() => {                                     // Tageswechsel erkennen
    if ($("missions").contains(document.activeElement)) return;
    refresh().catch(() => {});
  }, 60000);
});
