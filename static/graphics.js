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

function mascotSVG() {
  return `
<svg viewBox="0 0 200 210" role="img" aria-label="Sgt. Biscuit, die Drill-Sergeant-Bulldogge">
  <path d="M42 210 Q44 160 100 157 Q156 160 158 210 Z" fill="#5E7B2B"/>
  <path d="M84 159 L100 181 L116 159 Z" fill="#45601E"/>
  <circle cx="72" cy="190" r="4" fill="#F5B700"/><circle cx="128" cy="190" r="4" fill="#F5B700"/>

  <path d="M50 80 Q28 70 33 100 Q44 93 57 93 Z" fill="#B9814A"/>
  <path d="M150 80 Q172 70 167 100 Q156 93 143 93 Z" fill="#B9814A"/>
  <ellipse cx="100" cy="108" rx="60" ry="54" fill="#E9B87C" stroke="#B9814A" stroke-width="3"/>
  <path d="M84 84 Q100 78 116 84" stroke="#C9935A" stroke-width="3" fill="none" stroke-linecap="round"/>

  <ellipse cx="77" cy="135" rx="30" ry="22" fill="#F6DDB4"/>
  <ellipse cx="123" cy="135" rx="30" ry="22" fill="#F6DDB4"/>
  <ellipse cx="100" cy="127" rx="20" ry="16" fill="#F6DDB4"/>
  <ellipse cx="100" cy="116" rx="14" ry="9" fill="#3A2A20"/>
  <ellipse cx="95" cy="113" rx="4" ry="2" fill="#fff" opacity=".55"/>

  <g class="face-normal">
    <path d="M80 146 Q100 157 120 146" stroke="#3A2A20" stroke-width="4" fill="none" stroke-linecap="round"/>
    <polygon points="86,147 90,136 94,149" fill="#fff" stroke="#3A2A20" stroke-width="1.5" stroke-linejoin="round"/>
    <polygon points="106,149 110,136 114,147" fill="#fff" stroke="#3A2A20" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="80" cy="102" r="10" fill="#fff"/><circle cx="120" cy="102" r="10" fill="#fff"/>
    <circle cx="82" cy="104" r="5.5" fill="#2A1F18"/><circle cx="118" cy="104" r="5.5" fill="#2A1F18"/>
    <path d="M65 88 L92 95" stroke="#7A4E25" stroke-width="6" stroke-linecap="round"/>
    <path d="M135 88 L108 95" stroke="#7A4E25" stroke-width="6" stroke-linecap="round"/>
  </g>
  <g class="face-sad">
    <path d="M84 153 Q100 143 116 153" stroke="#3A2A20" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="80" cy="103" r="10" fill="#fff"/><circle cx="120" cy="103" r="10" fill="#fff"/>
    <circle cx="80" cy="107" r="5.5" fill="#2A1F18"/><circle cx="120" cy="107" r="5.5" fill="#2A1F18"/>
    <path d="M67 95 L92 87" stroke="#7A4E25" stroke-width="6" stroke-linecap="round"/>
    <path d="M133 95 L108 87" stroke="#7A4E25" stroke-width="6" stroke-linecap="round"/>
    <path d="M152 96 Q159 107 152 112 Q145 107 152 96 Z" fill="#7EC8F0"/>
  </g>

  <ellipse cx="100" cy="62" rx="80" ry="13" fill="#8C6B36" stroke="#6B5128" stroke-width="2"/>
  <path d="M62 61 Q63 35 78 22 Q100 11 122 22 Q137 35 138 61 Z" fill="#A27D40" stroke="#6B5128" stroke-width="2"/>
  <path d="M100 13 V30 M84 21 L90 34 M116 21 L110 34" stroke="#6B5128" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M63 53 Q100 60 137 53 L138 61 Q100 67 62 61 Z" fill="#3B2F1C"/>

  <g class="salute">
    <path d="M152 200 Q182 140 156 84" stroke="#5E7B2B" stroke-width="22" fill="none" stroke-linecap="round"/>
    <ellipse cx="150" cy="76" rx="15" ry="10" fill="#E9B87C" stroke="#B9814A" stroke-width="2.5" transform="rotate(-35 150 76)"/>
  </g>
</svg>`;
}
