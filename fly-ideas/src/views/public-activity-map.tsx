import { useEffect, useMemo, useRef, useState } from "react";
import matrixCsv from "../../experiments/reports/biological-digital-pipeline-116a-61x61.csv?raw";
import prototypeJson from "../../experiments/reports/adaptive-three-direction-118-action-prototypes.json?raw";

type ActivityKind = "rest" | "wing_display" | "foreleg_rubbing" | "head_directed_grooming" | "reach_withdraw";
type PrototypeFile = { actions: string[]; types: string[]; prototypes: number[][]; interpretation: string };
const rows = matrixCsv.trim().split(/\r?\n/).map(line => line.split(","));
const types = rows[0].slice(1);
const matrix = rows.slice(1).map(row => row.slice(1).map(Number));
const prototypeFile = JSON.parse(prototypeJson) as PrototypeFile;
const SIZE = 61, CELL = 5, CANVAS = SIZE * CELL;
const flat = matrix.flat(), edgeCount = flat.filter(value => value > 0).length, synapseCount = flat.reduce((sum, value) => sum + value, 0), maximum = Math.max(...flat);
const strongest = flat.map((value, index) => ({ value, source: Math.floor(index / SIZE), target: index % SIZE })).sort((a, b) => b.value - a.value).slice(0, 3);
if (prototypeFile.types.join("|") !== types.join("|")) throw new Error("Series118 action prototypes do not match the frozen61-type map.");

function weightColor(value: number, activation: number): string {
  if (value <= 0) return "rgb(35,34,31)";
  const weight = Math.log1p(value) / Math.log1p(maximum);
  const dark = [53,48,42], structural = [224,91,43], active = [49,174,201];
  const base = dark.map((channel, index) => channel + (structural[index] - channel) * weight);
  const mix = Math.min(.9, Math.max(0, activation));
  return `rgb(${base.map((channel, index) => Math.round(channel + (active[index] - channel) * mix)).join(",")})`;
}

export function PublicActivityMap({ action, amplitude, phase }: { action: ActivityKind; amplitude: number; phase: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<{ source: number; target: number; value: number } | null>(null);
  const actionIndex = prototypeFile.actions.indexOf(action);
  const pulseStep = Math.floor(phase * 6);
  const activation = useMemo(() => {
    if (actionIndex < 0 || amplitude <= 0) return Array(SIZE).fill(0) as number[];
    const values = prototypeFile.prototypes[actionIndex], max = Math.max(...values), pulse = .6 + .4 * Math.abs(Math.sin(pulseStep / 6 * Math.PI * 2));
    return values.map(value => value / Math.max(max, 1e-15) * Math.min(1.25, amplitude) * pulse);
  }, [actionIndex, amplitude, pulseStep]);
  useEffect(() => {
    const context = canvas.current?.getContext("2d"); if (!context) return;
    context.fillStyle = "rgb(24,23,21)"; context.fillRect(0, 0, CANVAS, CANVAS);
    for (let source = 0; source < SIZE; source += 1) for (let target = 0; target < SIZE; target += 1) {
      const value = matrix[source][target]; if (value <= 0) continue;
      const edgeActivation = Math.sqrt(activation[source] * activation[target]);
      context.fillStyle = weightColor(value, edgeActivation);
      context.fillRect(target * CELL, source * CELL, CELL - 1, CELL - 1);
    }
    if (hover) { context.strokeStyle = "rgb(235,225,201)"; context.lineWidth = 1; context.strokeRect(hover.target * CELL + .5, hover.source * CELL + .5, CELL - 1, CELL - 1); }
  }, [hover, activation]);
  const overlayName = actionIndex >= 0 ? `Series118: ${action}` : action === "rest" ? "пауза: подсветка выключена" : "для взмахов нет frozen Series118-прототипа";
  return <section className="min-w-0 border p-3">
    <div className="border-b pb-2"><h3 className="text-[13px] font-semibold">Карта61×61 + цифровая action-подсветка</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">Оранжевая основа — постоянное число синапсов между реальными индексированными типами. Голубая подсветка меняется вместе с выбранным действием и показывает frozen цифровой прототип.</p></div>
    <div className="mt-2 border px-2 py-1 font-mono text-[9px] text-muted-foreground">{overlayName}</div>
    <div className="mt-3 flex justify-center"><canvas ref={canvas} width={CANVAS} height={CANVAS} className="aspect-square w-full max-w-[305px] border [image-rendering:pixelated]" aria-label="Карта61 на61 реальных типов с цифровой action-подсветкой" onMouseLeave={() => setHover(null)} onMouseMove={event => { const box = event.currentTarget.getBoundingClientRect(); const target = Math.max(0, Math.min(SIZE - 1, Math.floor((event.clientX - box.left) / box.width * SIZE))); const source = Math.max(0, Math.min(SIZE - 1, Math.floor((event.clientY - box.top) / box.height * SIZE))); setHover({ source, target, value: matrix[source][target] }); }}/></div>
    <div className="mt-2 grid grid-cols-3 gap-1 text-center font-mono text-[9px] text-muted-foreground"><span className="border-t-4 border-[#23221f] pt-1">нет связи</span><span className="border-t-4 border-[#e05b2b] pt-1">структура</span><span className="border-t-4 border-[#31aec9] pt-1">action overlay</span></div>
    <div className="mt-2 min-h-10 border p-2 font-mono text-[10px] leading-5">{hover ? `${types[hover.source]} → ${types[hover.target]}: ${hover.value.toLocaleString("ru-RU")} синапсов · overlay ${Math.round(Math.sqrt(activation[hover.source] * activation[hover.target]) * 100)}%` : "Наведите на клетку: source → target, точный вес и текущая подсветка"}</div>
    <dl className="mt-3 grid grid-cols-3 border text-center text-[10px]"><div className="border-r p-2"><dt className="text-muted-foreground">Типы</dt><dd className="mt-1 font-mono">61</dd></div><div className="border-r p-2"><dt className="text-muted-foreground">Связи</dt><dd className="mt-1 font-mono">{edgeCount.toLocaleString("ru-RU")}</dd></div><div className="p-2"><dt className="text-muted-foreground">Синапсы</dt><dd className="mt-1 font-mono">{synapseCount.toLocaleString("ru-RU")}</dd></div></dl>
    <div className="mt-3 border-t pt-3 text-[10px] leading-5 text-muted-foreground"><p><strong className="text-foreground">Структура реальна и неизменна; подсветка расчётная.</strong> Основа exact-loads frozen61×61 CSV SHA `03157b50…`. Overlay exact-loads Series118 prototypes SHA `28edd80b…`; это не измеренная активность живых нейронов.</p><p className="mt-2">Сильнейшие связи: {strongest.map(edge => `${types[edge.source]}→${types[edge.target]} (${edge.value.toLocaleString("ru-RU")})`).join("; ")}.</p></div>
  </section>;
}
