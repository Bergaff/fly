export type Angles = [number, number, number, number, number, number];
export type Keyframe = { t: number; angles_deg: Angles };
export type Trajectory = { schema: "fly-wings-trajectory-v1"; fps: 25; duration_s: number; keyframes: Keyframe[] };
export type WingSample = { t: number; teacher_deg: Angles; prediction_deg: Angles | null };
export type WingResult = { schema: "fly-wings-result-v1"; fps: 25; duration_s: number; trajectory: Trajectory; samples: WingSample[]; holdout_label?: string; user_metrics: { new: { rmse_rad: number }; zero: { rmse_rad: number }; axis_new: Record<string, { rmse_rad: number }> }; holdout_metrics: { new: { rmse_rad: number }; zero: { rmse_rad: number } } };
export const ZERO: Angles = [0, 0, 0, 0, 0, 0];
export const initialTrajectory: Trajectory = { schema: "fly-wings-trajectory-v1", fps: 25, duration_s: 2, keyframes: [
  { t: 0, angles_deg: [0, 0, 0, 0, 0, 0] },
  { t: .25, angles_deg: [35, 12, 10, -25, -8, 5] },
  { t: .5, angles_deg: [-25, -8, -10, 30, 12, -10] },
  { t: .75, angles_deg: [35, 12, 10, -25, -8, 5] },
  { t: 1, angles_deg: [-25, -8, -10, 30, 12, -10] },
  { t: 1.25, angles_deg: [35, 12, 10, -25, -8, 5] },
  { t: 1.5, angles_deg: [-25, -8, -10, 30, 12, -10] },
  { t: 1.75, angles_deg: [35, 12, 10, -25, -8, 5] },
  { t: 2, angles_deg: [0, 0, 0, 0, 0, 0] },
] };
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
function angles(a: unknown): a is Angles { return Array.isArray(a) && a.length === 6 && a.every(v => finite(v) && Math.abs(v) <= 60.00000001); }
export function parseTrajectory(value: unknown): Trajectory {
  if (!value || typeof value !== "object") throw new Error("Файл не содержит объект траектории.");
  const o = value as Record<string, unknown>;
  if (o.schema !== "fly-wings-trajectory-v1" || o.fps !== 25 || !finite(o.duration_s) || o.duration_s < .5 || o.duration_s > 10 || Math.abs(Math.round(o.duration_s * 25) - o.duration_s * 25) > 1e-7 || !Array.isArray(o.keyframes) || o.keyframes.length < 2 || o.keyframes.length > 200) throw new Error("Нужна траектория версии 1: 25 кадров/с, длительность от 0,52 до 10 секунд, кратная 0,04 с, 2–200 кадров.");
  const frames: Keyframe[] = o.keyframes.map((f: unknown) => {
    if (!f || typeof f !== "object") throw new Error("Некорректный кадр.");
    const k = f as Record<string, unknown>;
    if (!finite(k.t) || !angles(k.angles_deg)) throw new Error("Кадр должен содержать время и шесть углов в диапазоне ±60°.");
    return { t: k.t, angles_deg: [...k.angles_deg] as Angles };
  });
  if (Math.abs(frames[0].t) > 1e-9 || Math.abs(frames[frames.length - 1].t - o.duration_s) > 1e-9 || frames.some((f, i) => i > 0 && f.t - frames[i - 1].t < 1e-6)) throw new Error("Время кадров должно строго возрастать от 0 до конца траектории.");
  return { schema: "fly-wings-trajectory-v1", fps: 25, duration_s: o.duration_s, keyframes: frames };
}
export function interpolate(t: number, trajectory: Trajectory): Angles {
  const fs = trajectory.keyframes;
  if (t <= fs[0].t) return [...fs[0].angles_deg];
  if (t >= fs[fs.length - 1].t) return [...fs[fs.length - 1].angles_deg];
  const index = fs.findIndex(f => f.t >= t), a = fs[index - 1], b = fs[index];
  const p = (t - a.t) / (b.t - a.t);
  return a.angles_deg.map((v, i) => v + (b.angles_deg[i] - v) * p) as Angles;
}
export function parseResult(value: unknown): WingResult {
  if (!value || typeof value !== "object") throw new Error("Файл результата повреждён.");
  const o = value as Record<string, unknown>;
  if (o.schema !== "fly-wings-result-v1" || o.fps !== 25 || !finite(o.duration_s) || !Array.isArray(o.samples)) throw new Error("Нужен файл playback.json из пробы 6 осей.");
  const trajectory = parseTrajectory(o.trajectory);
  if (o.duration_s !== trajectory.duration_s || o.samples.length !== Math.round(trajectory.duration_s * 25) + 1) throw new Error("Число кадров результата не совпадает с траекторией.");
  const samples: WingSample[] = o.samples.map((v: unknown, i: number) => {
    if (!v || typeof v !== "object") throw new Error("Некорректный кадр результата.");
    const s = v as Record<string, unknown>;
    if (!finite(s.t) || Math.abs(s.t - i / 25) > 1e-6 || !angles(s.teacher_deg) || (i < 2 ? s.prediction_deg !== null : !angles(s.prediction_deg))) throw new Error("Некорректное время или углы в результате.");
    const expected = interpolate(s.t, trajectory);
    if (s.teacher_deg.some((v, j) => Math.abs(v - expected[j]) > 1e-6)) throw new Error("Углы показа не совпадают с траекторией результата.");
    return { t: s.t, teacher_deg: s.teacher_deg, prediction_deg: s.prediction_deg as Angles | null };
  });
  function validMetrics(v: unknown): boolean {
    if (!v || typeof v !== "object") return false;
    const a = v as Record<string, unknown>;
    return [a.new, a.zero].every(x => !!x && typeof x === "object" && finite((x as Record<string, unknown>).rmse_rad));
  }
  if (!validMetrics(o.user_metrics) || !validMetrics(o.holdout_metrics)) throw new Error("Нет показателей ошибки в результате.");
  if (o.holdout_label !== undefined && (typeof o.holdout_label !== "string" || o.holdout_label.length > 100)) throw new Error("Некорректная подпись проверочного набора.");
  return { ...o, trajectory, samples } as WingResult;
}
