import { parseTrajectory, type Angles, type Trajectory } from "@/lib/wing-trajectory";

export type AblationSample = { t: number; teacher: Angles; prediction: Angles };
export type AblationPlayback = { trajectory: Trajectory; samples: AblationSample[]; method: string };
export type AblationActivity = { times: number[]; compact: number[][]; richLevel: number[][]; richDelta: number[][] };
export type AblationMetrics = {
  holdout_index: number;
  delay_s: number;
  state_unchanged_during_delay: boolean;
  zero: { rmse_rad: number };
  conditions: Record<string, { compact: { rmse_rad: number }; rich: { rmse_rad: number } }>;
};
export type Series69Demo = {
  folder: string;
  compact: AblationPlayback;
  rich: AblationPlayback;
  activity: AblationActivity;
  metrics: AblationMetrics;
  states: { compact: number[]; rich: number[]; updates_during_delay: number };
};

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const angles = (v: unknown): v is Angles => Array.isArray(v) && v.length === 6 && v.every(x => finite(x) && Math.abs(x) <= 360);

export function parseAblationPlayback(value: unknown): AblationPlayback {
  if (!value || typeof value !== "object") throw new Error("Playback серии 69 повреждён.");
  const o = value as Record<string, unknown>;
  if (o.schema !== "fly-wings-result-v1" || o.fps !== 25 || !Array.isArray(o.samples)) throw new Error("Нужен playback серии 69, 25 FPS.");
  const trajectory = parseTrajectory(o.trajectory);
  if (o.samples.length !== Math.round(trajectory.duration_s * 25) + 1) throw new Error("Число кадров playback не совпадает с траекторией.");
  const samples = o.samples.map((raw, i) => {
    if (!raw || typeof raw !== "object") throw new Error("Кадр playback повреждён.");
    const s = raw as Record<string, unknown>;
    if (!finite(s.t) || Math.abs(s.t - i / 25) > 1e-6 || !angles(s.teacher_deg) || !angles(s.prediction_deg)) throw new Error("Некорректные время или углы playback.");
    return { t: s.t, teacher: [...s.teacher_deg] as Angles, prediction: [...s.prediction_deg] as Angles };
  });
  return { trajectory, samples, method: typeof o.method === "string" ? o.method : "series 69 autonomous replay" };
}

function csvRows(text: string): string[][] {
  return text.replace(/^\uFEFF/, "").trim().split(/\r?\n/).map(line => line.split(","));
}
export function parseAblationActivity(text: string): AblationActivity {
  const rows = csvRows(text);
  const header = rows.shift();
  if (!header || header.length !== 217 || header[0] !== "time_s") throw new Error("observer_activity.csv серии 69 имеет неизвестный формат.");
  if (!header.slice(1, 25).every((v, i) => v === `compact_${String(i).padStart(2, "0")}`)) throw new Error("Нет 24 compact units.");
  if (!header.slice(25, 121).every((v, i) => v === `rich_level_${String(i).padStart(3, "0")}`)) throw new Error("Нет 96 rich level units.");
  if (!header.slice(121).every((v, i) => v === `rich_delta_${String(i).padStart(3, "0")}`)) throw new Error("Нет 96 rich delta units.");
  const times: number[] = [], compact: number[][] = [], richLevel: number[][] = [], richDelta: number[][] = [];
  rows.forEach((row, ri) => {
    if (row.length !== 217) throw new Error(`Некорректная строка activity ${ri + 2}.`);
    const v = row.map(Number);
    if (!v.every(Number.isFinite) || Math.abs(v[0] - ri / 25) > 1e-6) throw new Error(`Некорректные числа activity ${ri + 2}.`);
    times.push(v[0]); compact.push(v.slice(1, 25)); richLevel.push(v.slice(25, 121)); richDelta.push(v.slice(121));
  });
  if (rows.length < 2 || rows.length > 251) throw new Error("Некорректное число кадров activity.");
  return { times, compact, richLevel, richDelta };
}

export function parseSeries69Demo(raw: { folder: string; compact: string; rich: string; activity: string; metrics: string; states: string }): Series69Demo {
  const compact = parseAblationPlayback(JSON.parse(raw.compact.replace(/^\uFEFF/, "")));
  const rich = parseAblationPlayback(JSON.parse(raw.rich.replace(/^\uFEFF/, "")));
  const metrics = JSON.parse(raw.metrics.replace(/^\uFEFF/, "")) as AblationMetrics;
  const states = JSON.parse(raw.states.replace(/^\uFEFF/, "")) as Series69Demo["states"];
  const activity = parseAblationActivity(raw.activity);
  if (JSON.stringify(compact.trajectory) !== JSON.stringify(rich.trajectory)) throw new Error("Compact и rich playback относятся к разным движениям.");
  if (compact.samples.length !== rich.samples.length || activity.times.length !== rich.samples.length) throw new Error("Длины playback и activity не совпадают.");
  if (!metrics || !finite(metrics.delay_s) || !metrics.conditions?.normal || !finite(metrics.conditions.normal.compact?.rmse_rad) || !finite(metrics.conditions.normal.rich?.rmse_rad)) throw new Error("metrics.json серии 69 повреждён.");
  if (!states || !Array.isArray(states.compact) || states.compact.length !== 72 || !Array.isArray(states.rich) || states.rich.length !== 72 || !states.compact.every(finite) || !states.rich.every(finite) || states.updates_during_delay !== 0) throw new Error("internal_states.json серии 69 повреждён.");
  return { folder: raw.folder, compact, rich, activity, metrics, states };
}
