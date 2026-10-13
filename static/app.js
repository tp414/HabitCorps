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
let demoMode = false;

/* ---------- Server ---------- */
async function api(path, body) {
  const headers = { "Content-Type": "application/json" };
  if (demoMode) headers["X-Demo"] = "1";       // Demo: Server nutzt demo_data.json
  const res = await fetch(path, body === undefined ? { headers } : {
    method: "POST",
    headers,
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
    : s.rank.index === 13
      ? `Höchster Rang erreicht. Salut, General!`
      : `General wird am Monatsende vergeben: jeden Tag mind. 5 Missionen mit ×3,0.`;
  $("blocked").hidden = !s.blocked;
  $("blocked").textContent = s.blocked ? "🔒 " + s.blocked : "";

  renderDemo();
  maybeStartTour();
  renderForecast();
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

function renderForecast() {
  const f = state.forecast;
  $("forecast-card").hidden = !f;
  if (!f) return;
  const pct = (x) => Math.round(x * 100);
  $("fc-icon").innerHTML = insigniaSVG(f.likely.index);
  $("fc-rank").textContent = f.likely.name;
  $("fc-sub").textContent = `wahrscheinlichster Rang · ${pct(f.likely.p)} %`;

  const rows = f.probabilities.filter((x) => x.p >= 0.01).sort((x, y) => y.index - x.index);
  $("fc-bars").innerHTML = rows.map((x) => `
    <li class="${x.index === f.likely.index ? "top" : ""}">
      ${insigniaSVG(x.index)}
      <span class="fc-name">${esc(x.name)}</span>
      <span class="fc-bar"><span style="width:${Math.max(2, pct(x.p))}%"></span></span>
      <span class="fc-pct">${x.p < 0.01 ? "<1" : pct(x.p)} %</span>
    </li>`).join("");

  const basis = f.history_days
    ? `An <b>${f.full_days} von ${f.history_days}</b> Tagen alle Missionen geschafft → Chance pro Tag <b>${pct(f.p)} %</b>.`
    : `Noch kein Verlauf – Startannahme <b>${pct(f.p)} %</b> pro Tag.`;
  const safe = `Mit ≥ 50 % mindestens: <b>${esc(f.safe.name)}</b>.`;
  const best = f.best_case ? ` Ohne Fehltag ab heute: <b>${esc(f.best_case.name)}</b>.` : "";
  $("fc-foot").innerHTML = `${basis} ${safe}${best} Erwartet: ${fmt(Math.round(f.expected_xp))} XP.`;
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
let mascotKey = "";
function setMascot(mood, text) {
  const m = $("mascot");
  const rank = state ? state.rank.index : 0;
  const key = rank + "|" + mood;
  if (key !== mascotKey) {               // nur neu zeichnen, wenn sich etwas ändert
    m.innerHTML = mascotSVG(rank, mood);
    mascotKey = key;
  }
  m.className = "mascot " + (mood ? "mood-" + mood : "");
  $("mascot-name").textContent = "Kuno · " + RANK_NAMES[rank];
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

function showPromotion(rank, kicker = "BEFÖRDERUNG!", sub = null) {
  $("promo-kicker").textContent = kicker;
  $("promo-mascot").innerHTML = mascotSVG(rank.index, "salute");
  $("promo-insignia").innerHTML = insigniaSVG(rank.index);
  $("promo-rank").textContent = rank.name;
  $("promo-grade").textContent = sub || "Dienstgrad " + rank.grade;
  $("promo-anecdote").textContent = "📜 " + rank.anecdote;
  const colors = ["#F5B700", "#6B8E23", "#E5483A", "#2E86DE", "#FF9600"];
  $("confetti").innerHTML = Array.from({ length: 40 }, (_, i) =>
    `<i style="left:${Math.random() * 100}%;background:${colors[i % colors.length]};animation-delay:${Math.random() * .5}s"></i>`).join("");
  $("promo").hidden = false;
  mascotReact("salute", kicker === "BEFÖRDERUNG!" ? `Beförderung zum ${rank.name}! Salut!` : `Orden als ${rank.name}! Salut!`, 3000);
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
    fireReminder(h);
  }
}

function fireReminder(h) {
  const text = `Mission „${h.name}“ ist noch offen. Streak halten, Soldat!`;
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("Habit Corps – Antreten!", { body: text });
  }
  toast("🔔 " + text, 6000);
  mascotReact("", text, 6000);
}

/* ---------- Tutorial mit Kuno (FR-33) ---------- */
// Jeder Schritt: Ziel-Element (CSS-Selektor, null = Bildschirmmitte), Titel, Text, Kunos Stimmung.
// "alt" ist ein Ersatz-Ziel, falls das eigentliche Element gerade nicht sichtbar ist.
const TOUR = [
  { target: null, mood: "salute", title: "Melde mich zum Dienst!",
    text: `Ich bin <b>Kuno</b>, dein Ausbilder. Hier trainieren wir Gewohnheiten – Tag für Tag, Rang für Rang.
           Ich zeige dir in ein paar Schritten, wie alles funktioniert. Du kannst jederzeit überspringen.` },
  { target: "#open-form", title: "Missionen anlegen",
    text: `Jede Gewohnheit ist eine <b>Mission</b>. Gib ihr einen Namen, optional ein Ziel und eine
           <b>Erinnerungszeit</b> – dann melde ich mich, wenn sie noch offen ist (solange die App geöffnet ist).` },
  { target: "#missions", alt: "#empty", title: "Abhaken",
    text: `Erledigt? Klick auf den runden Knopf. Das geht <b>einmal pro Tag</b> pro Mission.
           Jede Erledigung bringt <b>10 XP</b> – und ich salutiere.` },
  { target: ".chip-streak", title: "Streak – aber Vorsicht!",
    text: `Die Flamme zählt, wie viele Tage du am Stück durchhältst.
           Aber: Verpasst du <b>auch nur eine</b> Mission an einem Tag, fallen <b>alle</b> Streaks auf 0.
           Mehr Missionen heißt mehr XP – aber auch mehr Risiko.` },
  { target: ".rules", title: "Multiplikatoren",
    text: `Je länger dein Streak, desto mehr XP pro Mission: <b>×1,5</b> ab 7 Tagen, <b>×2</b> ab 14 und
           <b>×3</b> ab 30 Tagen. Durchhalten lohnt sich also doppelt und dreifach.` },
  { target: "#month-card", title: "Monats-XP",
    text: `Hier sammelst du XP für den laufenden Monat. Der Balken zeigt, wie nah du am Maximum bist
           und wie viel bis zur nächsten Beförderung fehlt. <b>Jeden Monat</b> startest du wieder als Private –
           deine Streaks bleiben aber erhalten.` },
  { target: "#ladder-card", title: "14 Ränge der US Army",
    text: `Vom Private bis zum General. Mit jedem Rang bekomme ich eine neue Uniform und werde fitter.
           Die obersten drei Ränge verlangen, dass du im <b>Vormonat</b> schon weit oben warst.` },
  { target: "#forecast-card", alt: "#month-card", title: "Prognose",
    text: `Sobald du Missionen hast, rechne ich aus deinem Verlauf aus, welchen Rang du am
           Monatsende <b>wahrscheinlich</b> erreichst – und was drin ist, wenn du keinen Tag verpasst.` },
  { target: "#orders-card", title: "Orden",
    text: `Am Monatsende verleihe ich dir deinen Rang als <b>Orden</b>. So siehst du Monat für Monat,
           wie weit du gekommen bist.` },
  { target: "#demo-toggle", title: "Demo-Modus",
    text: `Neugierig, wie ein General aussieht? Im <b>Demo-Modus</b> kannst du Tage vorspulen,
           Ränge testen und alles ausprobieren – deine echten Daten bleiben dabei unberührt.` },
  { target: "#command-card", title: "Kommando",
    text: `Hier kannst du dieses Tutorial jederzeit wieder ansehen oder deinen
           <b>Fortschritt zurücksetzen</b> und neu anfangen. Vorher lege ich eine Sicherungskopie an.` },
  { target: null, mood: "salute", title: "Dein Einsatzplan",
    text: `<ol class="tour-plan">
             <li><b>Klein starten:</b> 2–3 Missionen, die du wirklich jeden Tag schaffst.</li>
             <li><b>Erinnerung setzen</b>, am besten abends – dann rettet sie deinen Streak.</li>
             <li><b>30 Tage durchhalten</b> – ab dann gibt es ×3 auf jede Mission.</li>
             <li><b>Langsam aufstocken:</b> Für den General brauchst du 5 Missionen mit ×3.</li>
             <li><b>Prognose im Blick</b> behalten und nach einem Fehltag sofort neu starten.</li>
           </ol>
           Weggetreten – und viel Erfolg, Rekrut!` },
];

let tourIndex = -1;          // -1 = Tutorial läuft gerade nicht

// Startet das Tutorial automatisch beim ersten Öffnen (nicht im Demo-Modus)
function maybeStartTour() {
  if (state && !state.tutorial_done && !state.demo && tourIndex < 0) startTour();
}

function startTour() {
  tourIndex = 0;
  $("tour").hidden = false;
  showTourStep();
}

// Ziel-Element suchen; nur nehmen, wenn es sichtbar ist
function tourTarget(step) {
  for (const sel of [step.target, step.alt]) {
    if (!sel) continue;
    const el = document.querySelector(sel);
    if (el && el.offsetParent !== null && el.getBoundingClientRect().height > 0) return el;
  }
  return null;
}

function showTourStep() {
  const step = TOUR[tourIndex];
  const rank = state ? state.rank.index : 0;
  $("tour-kuno").innerHTML = mascotSVG(rank, step.mood || "");
  $("tour-step").textContent = `Schritt ${tourIndex + 1} von ${TOUR.length}`;
  $("tour-title").textContent = step.title;
  $("tour-text").innerHTML = step.text;
  $("tour-dots").innerHTML = TOUR.map((_, i) => `<i class="${i === tourIndex ? "on" : ""}"></i>`).join("");
  $("tour-back").disabled = tourIndex === 0;
  $("tour-next").textContent = tourIndex === TOUR.length - 1 ? "Los geht's!" : "Weiter";

  const el = tourTarget(step);
  if (el) {
    el.scrollIntoView({ block: "center" });            // sofort hinscrollen ...
    requestAnimationFrame(() => placeTour(el));        // ... dann Position messen
  } else {
    placeTour(null);
  }
}

// Spotlight über das Ziel legen und die Sprechblase daneben platzieren
function placeTour(el) {
  const spot = $("tour-spot"), card = $("tour-card");
  const vw = window.innerWidth, vh = window.innerHeight, pad = 8;
  if (!el) {
    spot.className = "tour-spot center";
    card.style.left = Math.max(12, (vw - card.offsetWidth) / 2) + "px";
    card.style.top = Math.max(12, (vh - card.offsetHeight) / 2) + "px";
    return;
  }
  const r = el.getBoundingClientRect();
  spot.className = "tour-spot";
  Object.assign(spot.style, {
    left: r.left - pad + "px", top: r.top - pad + "px",
    width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px",
  });
  const cw = card.offsetWidth, ch = card.offsetHeight;
  let top = r.bottom + pad + 14;                       // bevorzugt unterhalb
  if (top + ch > vh - 12) top = r.top - pad - 14 - ch; // sonst oberhalb
  if (top < 12) top = Math.min(vh - ch - 12, Math.max(12, r.top));   // sonst daneben
  let left = r.left + r.width / 2 - cw / 2;
  if (top === Math.min(vh - ch - 12, Math.max(12, r.top))) {
    left = r.right + 20 + cw < vw ? r.right + 20 : r.left - 20 - cw;
  }
  card.style.left = Math.min(vw - cw - 12, Math.max(12, left)) + "px";
  card.style.top = top + "px";
}

async function endTour() {
  tourIndex = -1;
  $("tour").hidden = true;
  try {
    const res = await api("/api/tutorial/done", {});    // merken: Tutorial gesehen
    state = res.state;
    render();
  } catch (e) { toast(e.message); }
}

/* ---------- Fortschritt zurücksetzen (FR-34) ---------- */
function openReset() {
  const demo = !!(state && state.demo);
  $("reset-kuno").innerHTML = mascotSVG(state ? state.rank.index : 0, "sad");
  $("reset-text").innerHTML = demo
    ? "Die <b>Demo</b> wird neu aufgesetzt (Szenario „Frischer Start“). Eure echten Daten bleiben unberührt."
    : `Gelöscht werden <b>alle Missionen, Streaks, XP und Orden</b>. Danach startest du als Private
       und ich zeige dir das Tutorial noch einmal.<br><br>
       🛟 Vorher lege ich eine <b>Sicherungskopie</b> im Ordner <code>backups</code> an.`;
  $("reset-modal").hidden = false;
}

async function confirmReset() {
  $("reset-modal").hidden = true;
  try {
    const res = await api("/api/reset", {});
    state = res.state;
    mascotKey = "";
    render();
    const backup = res.result && res.result.backup;
    toast(backup ? `↺ Neustart! Sicherung: ${backup}` : "↺ Demo neu aufgesetzt.", 6000);
  } catch (e) { toast(e.message); }
}

/* ---------- Demo-Modus ---------- */
function renderDemo() {
  const on = !!(state && state.demo);
  document.body.classList.toggle("demo", on);
  $("demo-banner").hidden = !on;
  $("demo-panel").hidden = !on;
  $("demo-toggle-text").textContent = on ? "Demo beenden" : "Demo";
  if (!on) return;
  const d = new Date(state.demo.today + "T12:00:00");
  $("demo-date").textContent = d.toLocaleDateString("de-AT", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
  $("demo-scenario").textContent = "Szenario: " + state.demo.label;
}

async function setDemo(on) {
  demoMode = on;
  mascotKey = "";
  try {
    await refresh();
    toast(on ? "🧪 Demo-Modus aktiv – eure echten Daten bleiben unberührt." : "Zurück zu euren echten Daten.");
  } catch (e) { demoMode = !on; toast(e.message); }
}

async function demoAction(kind) {
  const calls = {
    "scenario": ["/api/demo/scenario", () => ({ name: $("demo-scenario-select").value })],
    "day-all": ["/api/demo/next-day", () => ({ mode: "all" })],
    "day-miss": ["/api/demo/next-day", () => ({ mode: "miss" })],
    "day-none": ["/api/demo/next-day", () => ({ mode: "none" })],
    "month": ["/api/demo/end-month", () => ({})],
    "rank": ["/api/demo/rank", () => ({ rank: Number($("demo-rank-select").value) })],
  };
  if (kind === "exit") return setDemo(false);
  if (kind === "gallery") return openGallery();
  if (kind === "reminder") {
    const h = state.habits.find((x) => !x.done_today) || state.habits[0];
    if (!h) return toast("Keine Mission vorhanden.");
    askNotificationPermission();
    return fireReminder(h);
  }
  const [path, body] = calls[kind];
  try {
    const res = await api(path, body());
    state = res.state;
    mascotKey = "";
    render();
    const r = res.result || {};
    if (kind.startsWith("day-")) {
      toast(`📅 ${r.completed} erledigt, ${r.missed} verpasst${r.reset ? " – alle Streaks auf 0!" : ""}`);
      if (r.reset) mascotReact("sad", "Eine Mission verpasst … alle Streaks sind weg. Neuer Anlauf!", 3000);
    }
    if (kind === "month") toast(`⏩ ${r.days} Tage vorgespult.`);
    if (kind === "rank") toast(`Knapp vor ${r.name}. Hake eine Mission ab!`);
    if (kind === "scenario") toast(`Szenario „${r.label}“ geladen.`);
    const order = r.new_orders && r.new_orders[r.new_orders.length - 1];
    if (order) {
      setTimeout(() => showPromotion({ index: order.rank, name: order.rank_name, grade: order.grade, anecdote: order.anecdote },
        "MONATSORDEN VERLIEHEN", `${order.label} · ${fmt(order.xp)} XP (${fmt(order.percent)} %)`), 400);
    } else if (r.promoted) {
      setTimeout(() => showPromotion(state.rank), 400);
    }
  } catch (e) { toast(e.message); }
}

function openGallery(mood = "") {
  $("gallery-grid").innerHTML = RANK_NAMES.map((n, i) =>
    `<div class="card gallery-item">${mascotSVG(i, mood)}<b>${n}</b></div>`).join("");
  document.querySelectorAll("#gallery-moods button").forEach((b) => b.classList.toggle("btn-primary", b.dataset.mood === mood));
  $("gallery").hidden = false;
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
  $("open-form").addEventListener("click", openForm);
  $("cancel-form").addEventListener("click", closeForm);
  $("habit-form").addEventListener("submit", addHabit);
  $("f-name").addEventListener("input", (e) => ($("c-name").textContent = e.target.value.length));
  $("f-goal").addEventListener("input", (e) => ($("c-goal").textContent = e.target.value.length));
  $("promo-close").addEventListener("click", () => ($("promo").hidden = true));

  // Tutorial
  $("tour-next").addEventListener("click", () => {
    if (tourIndex >= TOUR.length - 1) return endTour();
    tourIndex++; showTourStep();
  });
  $("tour-back").addEventListener("click", () => { if (tourIndex > 0) { tourIndex--; showTourStep(); } });
  $("tour-skip").addEventListener("click", endTour);
  $("help-toggle").addEventListener("click", startTour);
  $("tour-again").addEventListener("click", startTour);
  window.addEventListener("resize", () => { if (tourIndex >= 0) placeTour(tourTarget(TOUR[tourIndex])); });

  // Zurücksetzen
  $("reset-open").addEventListener("click", openReset);
  $("reset-cancel").addEventListener("click", () => ($("reset-modal").hidden = true));
  $("reset-confirm").addEventListener("click", confirmReset);

  // Demo-Modus
  $("demo-rank-select").innerHTML = RANK_NAMES.slice(1, 14)
    .map((n, i) => `<option value="${i + 1}">${n}</option>`).join("");
  $("demo-toggle").addEventListener("click", () => setDemo(!demoMode));
  $("demo-panel").addEventListener("click", (e) => {
    const b = e.target.closest("[data-demo]");
    if (b) demoAction(b.dataset.demo);
  });
  $("gallery-close").addEventListener("click", () => ($("gallery").hidden = true));
  $("gallery-moods").addEventListener("click", (e) => {
    const b = e.target.closest("[data-mood]");
    if (b) openGallery(b.dataset.mood);
  });

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
