/* Grafiken: Rangabzeichen der US Army (vereinfacht) und Maskottchen "Sgt. Biscuit". */

const GOLD = { fill: "#F5B700", edge: "#9A6F00" };
const SILVER = { fill: "#D3D9E0", edge: "#7D8794" };

function chevron(y) {
  const d = `M8 ${y + 10} L30 ${y} L52 ${y + 10}`;
  return `<path d="${d}" stroke="${GOLD.edge}" stroke-width="7.5" fill="none" stroke-linejoin="miter"/>` +
         `<path d="${d}" stroke="${GOLD.fill}" stroke-width="5" fill="none" stroke-linejoin="miter"/>`;
}

function rocker(y) {
  const d = `M8 ${y} Q30 ${y + 11} 52 ${y}`;
  return `<path d="${d}" stroke="${GOLD.edge}" stroke-width="7.5" fill="none"/>` +
         `<path d="${d}" stroke="${GOLD.fill}" stroke-width="5" fill="none"/>`;
}

function star(cx, cy, r, c = SILVER) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 0 ? r : r * 0.42;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    pts.push(`${(cx + rad * Math.cos(a)).toFixed(1)},${(cy + rad * Math.sin(a)).toFixed(1)}`);
  }
  return `<polygon points="${pts.join(" ")}" fill="${c.fill}" stroke="${c.edge}" stroke-width="1.5" stroke-linejoin="round"/>`;
}

function bar(y, c) {
  return `<rect x="13" y="${y}" width="34" height="11" rx="2.5" fill="${c.fill}" stroke="${c.edge}" stroke-width="2"/>`;
}

const INSIGNIA = [
  // 0 Private – kein Abzeichen ("slick sleeve")
  () => `<circle cx="30" cy="30" r="20" fill="none" stroke="#B9B39C" stroke-width="3" stroke-dasharray="5 5"/>`,
  // 1 Private First Class
  () => chevron(14) + rocker(31),
  // 2 Specialist
  () => `<path d="M17 12 H43 V30 Q43 45 30 51 Q17 45 17 30 Z" fill="${GOLD.fill}" stroke="${GOLD.edge}" stroke-width="2.5"/>` +
        `<path d="M21 25 Q30 31 39 25 Q34 36 30 37 Q26 36 21 25 Z" fill="${GOLD.edge}"/>`,
  // 3 Sergeant
  () => chevron(6) + chevron(14) + chevron(22),
  // 4 Staff Sergeant
  () => chevron(4) + chevron(12) + chevron(20) + rocker(37),
  // 5 Sergeant First Class
  () => chevron(2) + chevron(10) + chevron(18) + rocker(33) + rocker(41),
  // 6 Master Sergeant
  () => chevron(1) + chevron(8) + chevron(15) + rocker(31) + rocker(38) + rocker(45),
  // 7 Sergeant Major
  () => chevron(1) + chevron(8) + chevron(15) + rocker(33) + rocker(40) + rocker(47) + star(30, 26, 6, GOLD),
  // 8 Second Lieutenant
  () => bar(24, GOLD),
  // 9 Captain
  () => bar(15, SILVER) + bar(34, SILVER),
  // 10 Major – goldenes Eichenblatt
  () => `<path d="M30 6 C39 11 44 19 39 27 C47 31 44 41 37 41 C40 48 35 53 30 54 C25 53 20 48 23 41 C16 41 13 31 21 27 C16 19 21 11 30 6 Z" fill="${GOLD.fill}" stroke="${GOLD.edge}" stroke-width="2.5"/>` +
        `<path d="M30 14 V54" stroke="${GOLD.edge}" stroke-width="2"/>`,
  // 11 Colonel – Adler
  () => `<path d="M30 20 L35 26 L54 15 L48 28 L56 31 L43 36 L35 34 L37 49 L30 45 L23 49 L25 34 L17 36 L4 31 L12 28 L6 15 L25 26 Z" fill="${SILVER.fill}" stroke="${SILVER.edge}" stroke-width="2" stroke-linejoin="round"/>` +
        `<circle cx="30" cy="16" r="5" fill="${SILVER.fill}" stroke="${SILVER.edge}" stroke-width="2"/>`,
  // 12 Brigadier General
  () => star(30, 31, 19),
  // 13 General
  () => star(8, 30, 7.5) + star(22.5, 30, 7.5) + star(37.5, 30, 7.5) + star(52, 30, 7.5),
];

function insigniaSVG(index, cls = "") {
  return `<svg class="${cls}" viewBox="0 0 60 60" aria-hidden="true">${INSIGNIA[index]()}</svg>`;
}

/* ---------- Maskottchen "Kuno" – jeder Rang ein eigener Charakter ----------
   Je höher der Rang, desto extremer: Körperbau, Haltung, Requisiten, Effekte. */

let mascotUid = 0;

const FUR = "#8C6A4B", FUR_D = "#6B4E37", FACE = "#EAD7B7", PATCH = "#4B3626",
      CLAW = "#EFE2CA", INK = "#24170F", NOSE = "#2A1C14";

const OUTFITS = {
  tshirt:  { fill: "#76844D", edge: "#5A6638" },
  ocp:     { fill: "#8E8F64", edge: "#686A45" },
  service: { fill: "#4A5535", edge: "#343D24" },
};

const RANK_NAMES = ["Private", "Private First Class", "Specialist", "Sergeant", "Staff Sergeant",
  "Sergeant First Class", "Master Sergeant", "Sergeant Major", "Second Lieutenant", "Captain",
  "Major", "Colonel", "Brigadier General", "General"];

function outfitFor(rank) {
  if (rank <= 1) return "tshirt";
  if (rank <= 7) return "ocp";
  return "service";
}

function claws(x, y, dir = 1) {
  let out = "";
  for (let i = -1; i <= 1; i++) {
    out += `<path d="M${x + i * 4.5} ${y} q${dir * 1.5} 7 ${-dir * 2.5} 10" stroke="${CLAW}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`;
  }
  return out;
}

function arm(path, w, sleeveColor, sleeveLen) {
  let out = `<path d="${path}" stroke="${FUR}" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
  if (sleeveLen > 0) {
    out += `<path d="${path}" pathLength="1" stroke-dasharray="${sleeveLen} 2" stroke="${sleeveColor}" stroke-width="${w + 5}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
  }
  return out;
}

function sparkle(x, y, r, c = GOLD.fill) {
  return `<path d="M${x} ${y - r} Q${x} ${y} ${x + r} ${y} Q${x} ${y} ${x} ${y + r} Q${x} ${y} ${x - r} ${y} Q${x} ${y} ${x} ${y - r} Z" fill="${c}"/>`;
}

/* ---- Requisiten in der linken Pfote (px/py = Pfotenposition) ---- */
const PROPS = {
  0: (px, py) =>   // Kaffeetasse
    `<g transform="translate(${px - 10} ${py - 16})"><rect width="20" height="22" rx="4" fill="#F4F1EA" stroke="#9A9486" stroke-width="2"/>` +
    `<path d="M20 6 q9 0 9 6 q0 6 -9 6" stroke="#9A9486" stroke-width="3" fill="none"/>` +
    `<rect x="3" y="3" width="14" height="4" rx="2" fill="#6B4527"/>` +
    `<path class="steam" d="M6 -3 q-4 -5 0 -10 M13 -3 q-4 -5 0 -10" stroke="#B8B2A4" stroke-width="2" fill="none" stroke-linecap="round"/></g>`,
  1: (px, py) =>   // Snack-Blatt
    `<g transform="translate(${px} ${py}) rotate(-35)"><path d="M0 0 Q14 -16 0 -34 Q-14 -16 0 0 Z" fill="#5DAA3A" stroke="#3E7A22" stroke-width="2"/>` +
    `<path d="M0 -2 V-30" stroke="#3E7A22" stroke-width="1.5"/></g>`,
  2: (px, py) =>   // Schraubenschlüssel
    `<g transform="translate(${px} ${py}) rotate(20)"><rect x="-3.5" y="-36" width="7" height="34" rx="3" fill="#A7B0BA" stroke="#5F6872" stroke-width="1.5"/>` +
    `<path d="M-9 -46 a10 10 0 1 0 18 0 l-4 6 h-10 z" fill="#A7B0BA" stroke="#5F6872" stroke-width="1.5"/></g>`,
  4: (px, py) =>   // Klemmbrett
    `<g transform="translate(${px - 14} ${py - 30}) rotate(-8)"><rect width="28" height="36" rx="3" fill="#9C6B3A" stroke="#6B4524" stroke-width="2"/>` +
    `<rect x="4" y="6" width="20" height="26" fill="#FFFDF5"/><rect x="9" y="-3" width="10" height="7" rx="2" fill="#A7B0BA"/>` +
    `<path d="M7 13 h14 M7 19 h14 M7 25 h9" stroke="#8C8F7A" stroke-width="1.5"/><path d="M8 13 l2 2 l3 -4" stroke="#3C8D2F" stroke-width="2" fill="none"/></g>`,
  5: (px, py) =>   // Funkgerät
    `<g transform="translate(${px - 7} ${py - 26})"><rect width="14" height="28" rx="3" fill="#2B2F2A" stroke="#111" stroke-width="1.5"/>` +
    `<path d="M10 0 V-16" stroke="#111" stroke-width="3" stroke-linecap="round"/><circle cx="10" cy="-17" r="2.5" fill="#E5483A"/>` +
    `<rect x="3" y="5" width="8" height="6" rx="1" fill="#7CC36B"/><path d="M3 15 h8 M3 19 h8 M3 23 h8" stroke="#555" stroke-width="1.5"/></g>`,
  6: (px, py) =>   // Megafon
    `<g transform="translate(${px} ${py - 6}) rotate(-25)"><path d="M0 -6 L-30 -18 L-30 18 L0 6 Z" fill="#E5483A" stroke="#9E2418" stroke-width="2"/>` +
    `<rect x="-34" y="-19" width="6" height="38" rx="3" fill="#F4F1EA" stroke="#9E2418" stroke-width="1.5"/><rect x="0" y="-5" width="9" height="10" rx="2" fill="#333"/>` +
    `<path d="M-42 -14 l-8 -6 M-44 0 h-10 M-42 14 l-8 6" stroke="#E5483A" stroke-width="3" stroke-linecap="round"/></g>`,
  7: (px, py) =>   // Swagger Stick
    `<g transform="translate(${px} ${py}) rotate(-40)"><rect x="-2.5" y="-62" width="5" height="76" rx="2.5" fill="#6B3E1E"/>` +
    `<rect x="-3.5" y="-66" width="7" height="8" rx="2" fill="${GOLD.fill}"/><rect x="-3.5" y="12" width="7" height="6" rx="2" fill="${GOLD.fill}"/></g>`,
  9: (px, py) =>   // Landkarte
    `<g transform="translate(${px} ${py - 4}) rotate(-60)"><rect x="-6" y="-34" width="12" height="44" rx="6" fill="#E8D9A8" stroke="#A88D4E" stroke-width="2"/>` +
    `<path d="M-6 -24 h12 M-6 0 h12" stroke="#B22234" stroke-width="2"/></g>`,
  10: (px, py) =>  // Zeigestock
    `<g transform="translate(${px} ${py}) rotate(-28)"><rect x="-2" y="-80" width="4" height="86" rx="2" fill="#3B2F1C"/><circle cx="0" cy="-81" r="3.5" fill="${GOLD.fill}"/></g>`,
};

function hat(rank) {
  if (rank === 0) {   // zerzauste Haare
    return `<path d="M80 46 q4 -13 9 -1 q4 -15 9 -1 q5 -14 10 0 q5 -11 9 2" stroke="${FUR_D}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  }
  if (rank <= 2) {    // Feldmütze – beim PFC schief
    const tilt = rank === 1 ? 'transform="rotate(-14 100 50)"' : "";
    return `<g ${tilt}><path d="M64 54 L69 30 Q100 24 131 30 L136 54 Z" fill="#87895E" stroke="#5F6141" stroke-width="2"/>` +
           `<ellipse cx="86" cy="40" rx="7" ry="4" fill="#A9A67C"/><ellipse cx="112" cy="35" rx="6" ry="3" fill="#6F6B4A"/>` +
           `<path d="M60 54 Q100 62 140 54 L148 61 Q100 70 52 61 Z" fill="#6F7150" stroke="#5F6141" stroke-width="2"/></g>`;
  }
  if (rank === 6) {   // Drill-Sergeant-Hut
    return `<ellipse cx="100" cy="54" rx="74" ry="12" fill="#8C6B36" stroke="#6B5128" stroke-width="2"/>` +
           `<path d="M64 54 Q66 30 80 20 Q100 10 120 20 Q134 30 136 54 Z" fill="#A27D40" stroke="#6B5128" stroke-width="2"/>` +
           `<path d="M100 12 V28 M84 19 L90 32 M116 19 L110 32" stroke="#6B5128" stroke-width="2.5" stroke-linecap="round"/>` +
           `<path d="M65 47 Q100 53 135 47 L136 54 Q100 60 64 54 Z" fill="#3B2F1C"/>` +
           `<circle cx="100" cy="38" r="6" fill="${GOLD.fill}" stroke="${GOLD.edge}" stroke-width="1.5"/>`;
  }
  if (rank <= 7) {    // Barett
    return `<path d="M54 56 Q50 30 92 26 Q138 24 146 44 Q148 54 132 56 Q96 50 54 56 Z" fill="#1F2126" stroke="#0E0F12" stroke-width="2"/>` +
           `<path d="M56 56 Q100 50 140 56" stroke="#0E0F12" stroke-width="5" fill="none" stroke-linecap="round"/>` +
           `<path d="M72 34 h14 v10 q-7 6 -14 0 z" fill="#6B8E23" stroke="${GOLD.fill}" stroke-width="1.5"/>`;
  }
  // Dienstmütze, wird mit dem Rang immer prunkvoller
  const big = rank >= 13 ? 1.12 : 1;
  const braid = (y) => `<path d="M${66} ${y} q5 -3 10 0 t10 0 t10 0 t10 0 t10 0 t10 0 t10 0" stroke="${GOLD.fill}" stroke-width="2.4" fill="none"/>`;
  let deco = "";
  if (rank >= 10) deco += braid(58);
  if (rank >= 12) deco += braid(63);
  let stars = "";
  if (rank >= 12) {
    const n = rank === 12 ? 1 : 4;
    for (let k = 0; k < n; k++) stars += star(100 + (k - (n - 1) / 2) * 13, 26, 5.5);
  }
  const aviators = rank === 9
    ? `<g transform="translate(0 -4)"><ellipse cx="88" cy="46" rx="9" ry="6" fill="#2F3B45" stroke="${GOLD.fill}" stroke-width="1.5"/>` +
      `<ellipse cx="112" cy="46" rx="9" ry="6" fill="#2F3B45" stroke="${GOLD.fill}" stroke-width="1.5"/><path d="M97 46 h6" stroke="${GOLD.fill}" stroke-width="1.5"/></g>`
    : "";
  return `<g transform="translate(100 50) scale(${big}) translate(-100 -50)">` +
         `<ellipse cx="100" cy="34" rx="56" ry="15" fill="#3F4A2D" stroke="#2A321D" stroke-width="2"/>` +
         `<path d="M60 36 L62 52 Q100 58 138 52 L140 36 Z" fill="#33402A"/>` +
         `<path d="M61 50 Q100 57 139 50 L140 54 Q100 61 60 54 Z" fill="#B48A2C"/>` +
         `<path d="M58 54 Q100 60 142 54 Q136 70 100 70 Q64 70 58 54 Z" fill="#121212"/>` + deco + stars + aviators +
         `<circle cx="100" cy="42" r="6" fill="${GOLD.fill}" stroke="${GOLD.edge}" stroke-width="1.5"/></g>`;
}

function eagle(x, y) {   // Weißkopfseeadler auf der Schulter (Colonel+)
  return `<g transform="translate(${x} ${y})">` +
    `<path d="M-4 0 Q-18 -8 -24 4 Q-14 2 -8 8 Z" fill="#4A3020"/>` +
    `<ellipse cx="0" cy="-2" rx="10" ry="13" fill="#5A3A24"/>` +
    `<circle cx="2" cy="-18" r="8" fill="#FFFDF8" stroke="#D8D2C4"/>` +
    `<path d="M8 -19 L16 -16 L9 -13 Z" fill="${GOLD.fill}" stroke="${GOLD.edge}" stroke-width="1"/>` +
    `<circle cx="4" cy="-20" r="1.8" fill="${INK}"/>` +
    `<path d="M-4 10 l-2 5 M2 10 l0 5 M6 9 l3 5" stroke="${GOLD.fill}" stroke-width="2" stroke-linecap="round"/></g>`;
}

function mustache(rank) {
  if (rank < 10) return "";
  if (rank === 10) return `<path d="M88 113 Q94 108 100 112 Q106 108 112 113 Q106 116 100 114 Q94 116 88 113 Z" fill="${FUR_D}"/>`;
  const s = rank === 13 ? 1.35 : rank === 12 ? 1.18 : 1;
  return `<g transform="translate(100 113) scale(${s}) translate(-100 -113)">` +
    `<path d="M100 111 Q90 104 80 110 Q72 116 66 108 Q68 120 80 119 Q92 118 100 114 Q108 118 120 119 Q132 120 134 108 Q128 116 120 110 Q110 104 100 111 Z" fill="#5A3E2B"/></g>`;
}

function mascotSVG(rank = 0, mood = "") {
  const u = ++mascotUid;
  const f = rank / 13;
  const slouch = 1 - f;
  const outfit = outfitFor(rank);
  const cloth = OUTFITS[outfit];

  // ---- Körperbau: vom Pudding zum Panzer
  const sh = 32 + 50 * Math.pow(f, 1.25), belly = 62 - 26 * f, bottom = 44 + 4 * f;
  const torso = `M${100 - sh} 140 Q100 ${124 - 6 * f} ${100 + sh} 140 C${100 + belly + 8} 166 ${100 + belly} 200 ${100 + bottom} 222 ` +
                `L${100 - bottom} 222 C${100 - belly} 200 ${100 - belly - 8} 166 ${100 - sh} 140 Z`;
  const armW = 11 + 22 * Math.pow(f, 1.2);
  const headY = 12 * slouch, tilt = -10 * slouch;
  const handsOnHips = rank >= 11;

  // ---- Hintergrund-Effekte
  let bg = "";
  if (rank >= 12) {
    bg += `<circle cx="100" cy="110" r="${rank === 13 ? 118 : 96}" fill="url(#glow${u})"/>`;
  }
  if (rank === 13) {
    let rays = "";
    for (let k = 0; k < 16; k++) {
      const a1 = (k / 16) * Math.PI * 2, a2 = a1 + Math.PI / 22;
      rays += `<path d="M100 110 L${100 + 140 * Math.cos(a1)} ${110 + 140 * Math.sin(a1)} L${100 + 140 * Math.cos(a2)} ${110 + 140 * Math.sin(a2)} Z"/>`;
    }
    bg += `<g class="rays" fill="${GOLD.fill}" opacity=".28">${rays}</g>`;
    // Umhang
    bg += `<path d="M${100 - sh + 4} 142 Q${100 - sh - 34} 190 ${100 - sh - 30} 234 L${100 + sh + 30} 234 Q${100 + sh + 34} 190 ${100 + sh - 4} 142 Z" fill="#B22234" stroke="#7A1420" stroke-width="2"/>`;
  }
  if (rank === 8) {
    bg += sparkle(36, 70, 9) + sparkle(168, 52, 7) + sparkle(160, 120, 6) + sparkle(42, 130, 5);
  }

  // ---- Uniform-Details
  let details = "";
  if (outfit === "tshirt") {
    details += `<path d="M86 138 Q100 152 114 138" stroke="${cloth.edge}" stroke-width="3" fill="none"/>`;
    details += `<path d="M${100 - belly + 10} 196 Q100 ${210 + 4 * slouch} ${100 + belly - 10} 196" stroke="${cloth.edge}" stroke-width="2.5" fill="none" opacity=".8"/>`;
    if (rank === 0) details += `<ellipse cx="112" cy="172" rx="7" ry="5" fill="#5E4A2E" opacity=".55"/><circle cx="104" cy="182" r="2.5" fill="#5E4A2E" opacity=".5"/>`;
    if (rank === 1) {
      details += `<path d="M90 140 Q100 170 110 140" stroke="#C7CED6" stroke-width="1.6" fill="none"/>` +
                 `<rect x="96" y="162" width="8" height="11" rx="2" fill="#D3D9E0" stroke="#7D8794"/>`;
    }
  } else if (outfit === "ocp") {
    details += `<g clip-path="url(#torso${u})">` +
      `<ellipse cx="72" cy="160" rx="11" ry="6" fill="#ADA97E"/><ellipse cx="128" cy="188" rx="13" ry="6" fill="#ADA97E"/>` +
      `<ellipse cx="122" cy="152" rx="9" ry="5" fill="#6C6A48"/><ellipse cx="78" cy="200" rx="10" ry="5" fill="#6C6A48"/>` +
      `<ellipse cx="100" cy="214" rx="13" ry="5" fill="#ADA97E"/><ellipse cx="60" cy="182" rx="8" ry="4" fill="#ADA97E"/></g>`;
    details += `<path d="M86 138 L100 150 L114 138" stroke="${cloth.edge}" stroke-width="3" fill="none"/>`;
    details += `<path d="M100 150 V222" stroke="${cloth.edge}" stroke-width="2"/>`;
    details += `<rect x="89" y="157" width="22" height="26" rx="3" fill="#B6B289" stroke="${cloth.edge}" stroke-width="1.5"/>` +
               `<g transform="translate(90 160) scale(.3333)">${INSIGNIA[rank]()}</g>`;
    details += `<rect x="${100 - sh + 12}" y="152" width="22" height="6" rx="1" fill="#B6B289"/>` +
               `<rect x="${100 + sh - 34}" y="152" width="22" height="6" rx="1" fill="#B6B289"/>`;
    if (rank === 3) {  // Trillerpfeife
      details += `<path d="M88 140 Q92 168 112 176" stroke="#E5483A" stroke-width="2" fill="none"/>` +
                 `<rect x="110" y="172" width="14" height="8" rx="4" fill="#D3D9E0" stroke="#7D8794" stroke-width="1.5"/>`;
    }
    if (rank === 5) {  // Rucksackgurte
      details += `<path d="M${100 - sh + 16} 142 V222 M${100 + sh - 16} 142 V222" stroke="#4E4B33" stroke-width="7"/>`;
    }
    if (rank === 7) {  // Ordensspange schon als Unteroffizier
      details += `<rect x="114" y="164" width="7" height="4.5" fill="#B22234"/><rect x="121.5" y="164" width="7" height="4.5" fill="#2E5AAC"/><rect x="129" y="164" width="7" height="4.5" fill="#E8C547"/>`;
    }
  } else {
    details += `<path d="M84 138 L100 172 L116 138 Z" fill="#CDB88E"/>`;
    details += `<path d="M97 142 L103 142 L104.5 166 L100 173 L95.5 166 Z" fill="#2F2A1E"/>`;
    details += `<path d="M84 138 L100 176 L116 138" stroke="${cloth.edge}" stroke-width="3" fill="none"/>`;
    details += `<circle cx="100" cy="186" r="3" fill="${GOLD.fill}"/><circle cx="100" cy="203" r="3" fill="${GOLD.fill}"/>`;
    const ribbons = (rank - 7) * 2, cols = ["#B22234", "#2E5AAC", "#E8C547", "#3C8D2F", "#7B2D8E", "#F2F2F2", "#E5732A"];
    for (let i = 0; i < ribbons; i++) {
      const x = 108 + (i % 4) * 7.5, y = 150 + Math.floor(i / 4) * 5;
      details += `<rect x="${x}" y="${y}" width="7" height="4.5" fill="${cols[i % cols.length]}" stroke="#222" stroke-width=".4"/>`;
    }
    if (rank >= 12) {   // hängende Orden
      const n = rank === 12 ? 2 : 4;
      for (let k = 0; k < n; k++) {
        const x = 112 + k * 9, y = 150 + Math.ceil(ribbons / 4) * 5 + 2;
        details += `<path d="M${x} ${y} v8" stroke="${cols[k]}" stroke-width="5"/><circle cx="${x}" cy="${y + 12}" r="4.5" fill="${GOLD.fill}" stroke="${GOLD.edge}"/>`;
      }
      // goldene Fransen-Epauletten
      for (const x of [100 - sh + 2, 100 + sh - 30]) {
        details += `<rect x="${x}" y="132" width="28" height="9" rx="4" fill="${GOLD.fill}" stroke="${GOLD.edge}"/>`;
        for (let k = 0; k < 7; k++) details += `<path d="M${x + 3 + k * 3.7} 141 v9" stroke="${GOLD.fill}" stroke-width="2"/>`;
      }
    }
    if (rank === 8) {   // Fernglas
      details += `<path d="M84 140 Q100 162 116 140" stroke="#222" stroke-width="1.5" fill="none"/>` +
                 `<rect x="88" y="156" width="10" height="16" rx="3" fill="#2B2F2A"/><rect x="102" y="156" width="10" height="16" rx="3" fill="#2B2F2A"/>` +
                 `<rect x="97" y="160" width="6" height="6" fill="#444"/>`;
    }
    for (const x of [100 - sh + 6, 100 + sh - 26]) {
      if (rank < 12) details += `<g transform="translate(${x} 130) scale(.3)">${INSIGNIA[rank]()}</g>`;
    }
  }

  // ---- Arme
  const sleeve = outfit === "tshirt" ? 0.45 : 1;
  const lx = 100 - sh + 8, rx = 100 + sh - 8;
  let left, right;
  if (handsOnHips) {
    left = arm(`M${lx} 148 L${lx - 22} 178 L${100 - belly + 2} 198`, armW, cloth.fill, sleeve) +
           `<ellipse cx="${100 - belly + 2}" cy="198" rx="${armW / 2.2}" ry="${armW / 2.8}" fill="${FUR}"/>`;
  } else {
    const px = lx - 10, py = 203;
    left = arm(`M${lx} 148 Q${lx - 16} 172 ${px} 200`, armW, cloth.fill, sleeve) +
           (PROPS[rank] ? PROPS[rank](px, py) : "") + claws(px, py, 1);
  }
  if (mood === "salute") {
    const hy = 60 + headY;
    right = arm(`M${rx} 148 Q${rx + 30} 112 132 ${hy + 4}`, armW, cloth.fill, sleeve) +
            `<ellipse cx="127" cy="${hy}" rx="11" ry="7" fill="${FUR}" transform="rotate(-20 127 ${hy})"/>` + claws(120, hy - 4, -1);
  } else if (handsOnHips) {
    right = arm(`M${rx} 148 L${rx + 22} 178 L${100 + belly - 2} 198`, armW, cloth.fill, sleeve) +
            `<ellipse cx="${100 + belly - 2}" cy="198" rx="${armW / 2.2}" ry="${armW / 2.8}" fill="${FUR}"/>`;
  } else {
    right = arm(`M${rx} 148 Q${rx + 16} 172 ${rx + 10} 200`, armW, cloth.fill, sleeve) + claws(rx + 10, 203, -1);
  }
  const eagleSvg = rank === 11 || rank === 12 ? eagle(100 + sh - 12, 128) : "";

  // ---- Gesicht
  let lid = 0.05 + 0.4 * slouch;
  if (mood === "sad") lid += 0.15;
  if (mood === "salute") lid -= 0.12;
  lid = Math.max(0, Math.min(0.6, lid));

  const starEyes = rank === 13;
  const eye = (cx, side) => `
    <clipPath id="eye${side}${u}"><circle cx="${cx}" cy="90" r="12.5"/></clipPath>
    <circle cx="${cx}" cy="90" r="12.5" fill="#FFFDF8"/>
    <circle cx="${cx}" cy="91.5" r="10" fill="${starEyes ? "#2E5AAC" : "#6B4527"}"/>
    <circle cx="${cx}" cy="92" r="6.8" fill="${INK}"/>
    ${starEyes ? star(cx + 3, 87.5, 5, { fill: "#fff", edge: "#fff" }) : `<circle cx="${cx + 3.6}" cy="87" r="3.8" fill="#fff"/>`}
    <circle cx="${cx - 3.8}" cy="95.5" r="1.8" fill="#fff" opacity=".9"/>
    <rect x="${cx - 14}" y="76" width="28" height="${(27 * lid).toFixed(1)}" fill="${PATCH}" clip-path="url(#eye${side}${u})"/>
    <circle cx="${cx}" cy="90" r="12.5" fill="none" stroke="${PATCH}" stroke-width="1.5"/>`;

  const bags = slouch > 0.3
    ? `<path d="M70 106 q10 5 20 0 M110 106 q10 5 20 0" stroke="#7E6249" stroke-width="2" fill="none" opacity="${(slouch * 0.8).toFixed(2)}" stroke-linecap="round"/>`
    : "";
  const scar = rank === 7 || rank >= 12
    ? `<path d="M66 74 L84 106 M70 84 l6 -3 M74 92 l6 -3 M78 100 l6 -3" stroke="#D98C8C" stroke-width="2.4" stroke-linecap="round"/>`
    : "";

  let mouth;
  if (mood === "sad") mouth = `<path d="M88 124 Q100 116 112 124" stroke="${NOSE}" stroke-width="3.5" fill="none" stroke-linecap="round"/>`;
  else if (mood === "salute") mouth = `<path d="M86 116 Q100 129 114 116" stroke="${NOSE}" stroke-width="3.5" fill="none" stroke-linecap="round"/>`;
  else if (rank === 0) mouth = `<ellipse cx="100" cy="119" rx="6" ry="4.5" fill="${NOSE}"/><path d="M104 122 q2 8 0 12 q-3 -3 0 -12" fill="#BFE3F5"/>`;
  else if (rank === 6) mouth = `<ellipse cx="100" cy="121" rx="10" ry="8" fill="${NOSE}"/><ellipse cx="100" cy="125" rx="6" ry="3" fill="#D9636B"/>`;
  else if (rank === 8) mouth = `<path d="M84 115 Q100 132 116 115 Z" fill="${NOSE}"/><path d="M88 117 Q100 121 112 117 L111 120 Q100 124 89 120 Z" fill="#fff"/>`;
  else if (f > 0.55) mouth = `<path d="M88 119 Q103 124 115 113" stroke="${NOSE}" stroke-width="3.5" fill="none" stroke-linecap="round"/>`;
  else mouth = `<path d="M89 118 Q100 124 111 118" stroke="${NOSE}" stroke-width="3.5" fill="none" stroke-linecap="round"/>`;

  const tear = mood === "sad" ? `<path d="M131 100 Q136 109 131 113 Q126 109 131 100 Z" fill="#7EC8F0"/>` : "";
  const zz = rank <= 1 && mood === ""
    ? `<g class="zz" font-family="Nunito, sans-serif" font-weight="900" fill="#8C8F7A">` +
      `<text x="146" y="44" font-size="13">z</text><text x="157" y="31" font-size="17">z</text><text x="170" y="16" font-size="21">Z</text></g>`
    : "";
  const shout = rank === 6 && mood === ""
    ? `<g font-family="Nunito, sans-serif" font-weight="900" fill="#E5483A" font-size="13"><text x="-14" y="150" transform="rotate(-20 -14 150)">LOS!</text></g>`
    : "";

  return `
<svg viewBox="0 0 240 244" role="img" aria-label="Kuno, das Faultier, Rang ${RANK_NAMES[rank]}">
  <defs>
    <clipPath id="torso${u}"><path d="${torso}"/></clipPath>
    <radialGradient id="glow${u}"><stop offset="0" stop-color="#FFE58A" stop-opacity=".9"/><stop offset="1" stop-color="#FFE58A" stop-opacity="0"/></radialGradient>
  </defs>
  <g transform="translate(20 16)">
    ${bg}
    <path d="${torso}" fill="${cloth.fill}" stroke="${cloth.edge}" stroke-width="2"/>
    ${details}
    ${left}
    <g transform="translate(0 ${headY.toFixed(1)}) rotate(${tilt.toFixed(1)} 100 125)">
      <ellipse cx="100" cy="88" rx="52" ry="47" fill="${FUR}"/>
      <path d="M52 92 q-6 -6 -2 -14 M148 92 q6 -6 2 -14" stroke="${FUR_D}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <ellipse cx="100" cy="97" rx="42" ry="34" fill="${FACE}"/>
      <ellipse cx="79" cy="91" rx="21" ry="15" fill="${PATCH}" transform="rotate(-16 79 91)"/>
      <ellipse cx="121" cy="91" rx="21" ry="15" fill="${PATCH}" transform="rotate(16 121 91)"/>
      ${eye(81, "L")}${eye(119, "R")}
      ${bags}${scar}
      <ellipse cx="100" cy="107" rx="8" ry="5.5" fill="${NOSE}"/>
      <ellipse cx="97.5" cy="105" rx="2.6" ry="1.4" fill="#fff" opacity=".5"/>
      ${mustache(rank)}
      ${mouth}
      ${tear}
      ${hat(rank)}
    </g>
    ${eagleSvg}
    ${right}
    ${zz}${shout}
  </g>
</svg>`;
}
