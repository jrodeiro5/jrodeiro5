// Bakes morphicons' spring morphs into SMIL keyframes (GitHub strips JS, so the
// morph is sampled here and replayed by <animate>). Writes design/morphs.json.
// Run: cd design && pnpm install && node morph.mjs
import { writeFileSync } from "node:fs";
import { ChartColumn, Check, Box, Send } from "lucide";
import { resampleIcon, buildPlan, allocOutputs, interpPolar, Spring, SPRING_PRESETS } from "morphicons";

const LOOPS = { hero: [ChartColumn, Check, Box, Send] };
const N = 40;          // samples per subpath: enough at 108px, keeps each frame ~1 KB
const FRAMES = 12;     // keyframes per morph; SMIL interpolates linearly between them
const DT = 1 / 240;

// Spring progress over time, from rest (x=0) to settle, including its overshoot.
const { k, c } = SPRING_PRESETS.snappy;
const s = new Spring();
s.config(k, c);
s.start();
const curve = [0];
while (!s.step(DT)) curve.push(s.x);
curve.push(1);
const T = (curve.length - 1) * DT;

const num = (v) => String(Math.round(v * 100) / 100);
const path = (out, closed) => out.map((a, i) => {
  const p = [];
  for (let j = 0; j < a.length; j += 2) p.push(num(a[j]) + " " + num(a[j + 1]));
  return "M" + p.join(" ") + (closed[i] ? "Z" : "");
}).join("");

const result = {};
for (const [name, icons] of Object.entries(LOOPS)) {
  result[name] = icons.map((from, i) => {
    const plan = buildPlan(resampleIcon(from, N), resampleIcon(icons[(i + 1) % icons.length], N));
    const out = allocOutputs(plan);
    const closed = plan.items.map((it) => it.closed);
    const frames = [];
    for (let f = 0; f <= FRAMES; f++) {
      const idx = Math.round((f / FRAMES) * (curve.length - 1));
      interpPolar(plan, curve[idx], out);
      frames.push(path(out, closed));
    }
    return { dur: +T.toFixed(3), frames };
  });
}
writeFileSync(new URL("morphs.json", import.meta.url), JSON.stringify(result));
console.log(Object.entries(result).map(([n, m]) => `${n}: ${m.length} morphs, ${T.toFixed(2)}s`).join("\n"));
