import { useEffect, useRef, useState } from "react";
import matrixCsv from "../../experiments/reports/biological-digital-pipeline-116a-61x61.csv?raw";

const rows = matrixCsv.trim().split(/\r?\n/).map(line => line.split(","));
const types = rows[0].slice(1);
const matrix = rows.slice(1).map(row => row.slice(1).map(Number));
const SIZE = 61, CELL = 5, CANVAS = SIZE * CELL;
const flat = matrix.flat();
const edgeCount = flat.filter(value => value > 0).length;
const synapseCount = flat.reduce((sum, value) => sum + value, 0);
const maximum = Math.max(...flat);
const strongest = flat.map((value, index) => ({ value, source: Math.floor(index / SIZE), target: index % SIZE })).sort((a, b) => b.value - a.value).slice(0, 3);

function weightColor(value: number): string {
  if (value <= 0) return "rgb(35,34,31)";
  const amount = Math.log1p(value) / Math.log1p(maximum);
  const base = [53, 48, 42], target = [224, 91, 43];
  return `rgb(${base.map((channel, index) => Math.round(channel + (target[index] - channel) * amount)).join(",")})`;
}

export function PublicActivityMap() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<{ source: number; target: number; value: number } | null>(null);
  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (!context) return;
    context.fillStyle = "rgb(24,23,21)"; context.fillRect(0, 0, CANVAS, CANVAS);
    for (let source = 0; source < SIZE; source += 1) for (let target = 0; target < SIZE; target += 1) {
      context.fillStyle = weightColor(matrix[source][target]);
      context.fillRect(target * CELL, source * CELL, CELL - 1, CELL - 1);
    }
    if (hover) {
      context.strokeStyle = "rgb(235,225,201)"; context.lineWidth = 1;
      context.strokeRect(hover.target * CELL + .5, hover.source * CELL + .5, CELL - 1, CELL - 1);
    }
  }, [hover]);
  return <section className="min-w-0 border p-3">
    <div className="border-b pb-2"><h3 className="text-[13px] font-semibold">Реальная карта связей типов61×61</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">Строка — исходный FlyVis/FlyWire-indexed тип, столбец — целевой тип. Цвет показывает число синапсов в frozen Series116 map.</p></div>
    <div className="mt-3 flex justify-center"><canvas ref={canvas} width={CANVAS} height={CANVAS} className="aspect-square w-full max-w-[305px] border [image-rendering:pixelated]" aria-label="Карта синаптических связей 61 на 61 реальных индексированных типов" onMouseLeave={() => setHover(null)} onMouseMove={event => { const box = event.currentTarget.getBoundingClientRect(); const target = Math.max(0, Math.min(SIZE - 1, Math.floor((event.clientX - box.left) / box.width * SIZE))); const source = Math.max(0, Math.min(SIZE - 1, Math.floor((event.clientY - box.top) / box.height * SIZE))); setHover({ source, target, value: matrix[source][target] }); }}/></div>
    <div className="mt-2 grid grid-cols-5 gap-1 text-center font-mono text-[9px] text-muted-foreground" aria-label="Легенда числа синапсов"><span className="border-t-4 border-[#23221f] pt-1">0</span><span className="border-t-4 border-[#59483d] pt-1">мало</span><span className="border-t-4 border-[#87533e] pt-1">средне</span><span className="border-t-4 border-[#b45b39] pt-1">много</span><span className="border-t-4 border-[#e05b2b] pt-1">max</span></div>
    <div className="mt-2 min-h-10 border p-2 font-mono text-[10px] leading-5">{hover ? `${types[hover.source]} → ${types[hover.target]}: ${hover.value.toLocaleString("ru-RU")} синапсов` : "Наведите на клетку, чтобы увидеть source → target и точный вес"}</div>
    <dl className="mt-3 grid grid-cols-3 border text-center text-[10px]"><div className="border-r p-2"><dt className="text-muted-foreground">Типы</dt><dd className="mt-1 font-mono">61</dd></div><div className="border-r p-2"><dt className="text-muted-foreground">Связи</dt><dd className="mt-1 font-mono">{edgeCount.toLocaleString("ru-RU")}</dd></div><div className="p-2"><dt className="text-muted-foreground">Синапсы</dt><dd className="mt-1 font-mono">{synapseCount.toLocaleString("ru-RU")}</dd></div></dl>
    <div className="mt-3 border-t pt-3 text-[10px] leading-5 text-muted-foreground"><p><strong className="text-foreground">Это новая biological-indexed карта, а не старые96 программных каналов.</strong> Она exact-loads frozen CSV SHA `03157b50…` и содержит реальные названия типов, но остаётся агрегированной type-to-type картой, а не записью активности отдельных клеток.</p><p className="mt-2">Самые сильные связи: {strongest.map(edge => `${types[edge.source]}→${types[edge.target]} (${edge.value.toLocaleString("ru-RU")})`).join("; ")}.</p></div>
  </section>;
}
