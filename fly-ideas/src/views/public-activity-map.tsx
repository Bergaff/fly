import { useEffect, useMemo, useRef, useState } from "react";

type ActivityKind = "rest" | "wing_display" | "foreleg_rubbing" | "head_directed_grooming" | "reach_withdraw";

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const centers: Record<ActivityKind, number[]> = {
  rest: [],
  wing_display: [8, 9, 20, 21, 32, 33],
  foreleg_rubbing: [38, 39, 50, 51, 62, 63],
  head_directed_grooming: [55, 56, 67, 68, 79],
  reach_withdraw: [72, 73, 84, 85, 94],
};

function activity(action: ActivityKind, amplitude: number, phase: number, execution: boolean) {
  const wave = .52 + .48 * Math.abs(Math.sin(phase * Math.PI * 2));
  return Array.from({ length: 96 }, (_, index) => {
    const shifted = execution ? index - 1 : index;
    const peak = centers[action].reduce((best, center) => Math.max(best, Math.exp(-Math.pow(shifted - center, 2) / 18)), 0);
    const secondary = centers[action].reduce((best, center) => Math.max(best, Math.exp(-Math.pow(shifted - (95 - center), 2) / 36)), 0) * (.14 + .1 * Math.cos(phase * Math.PI * 2 + index * .13));
    const routeBias = execution ? ((index % 12) / 12) * .035 : ((7 - Math.floor(index / 12)) / 8) * .025;
    return clamp((peak * wave + secondary + routeBias) * amplitude * (execution ? .94 : 1));
  });
}

function pearson(a: number[], b: number[]) {
  const am = a.reduce((sum, value) => sum + value, 0) / a.length, bm = b.reduce((sum, value) => sum + value, 0) / b.length;
  let numerator = 0, av = 0, bv = 0;
  for (let i = 0; i < a.length; i += 1) { const x = a[i] - am, y = b[i] - bm; numerator += x * y; av += x * x; bv += y * y; }
  return av > 1e-12 && bv > 1e-12 ? Math.max(-1, Math.min(1, numerator / Math.sqrt(av * bv))) : 0;
}
function correlationColor(value: number): string {
  const base = [46, 44, 40], target = value < 0 ? [48, 82, 111] : [151, 67, 48], amount = Math.abs(value);
  return `rgb(${base.map((channel, index) => Math.round(channel + (target[index] - channel) * amount)).join(",")})`;
}

export function PublicActivityMap({ action, amplitude }: { action: ActivityKind; amplitude: number; phase: number }) {
  const canvas = useRef<HTMLCanvasElement>(null); const [hover, setHover] = useState<{ observation: number; replay: number; value: number } | null>(null);
  const matrix = useMemo(() => {
    const phases = Array.from({ length: 32 }, (_, index) => index / 32);
    const observation = phases.map(phase => activity(action, amplitude, phase, false)); const replay = phases.map(phase => activity(action, amplitude, phase, true));
    const result = new Float32Array(96 * 96);
    for (let row = 0; row < 96; row += 1) for (let column = 0; column < 96; column += 1) result[row * 96 + column] = pearson(observation.map(values => values[row]), replay.map(values => values[column]));
    return result;
  }, [action, amplitude]);
  useEffect(() => {
    const context = canvas.current?.getContext("2d"); if (!context) return;
    context.fillStyle = "rgb(24,23,21)"; context.fillRect(0, 0, 288, 288);
    for (let row = 0; row < 96; row += 1) for (let column = 0; column < 96; column += 1) { context.fillStyle = correlationColor(matrix[row * 96 + column]); context.fillRect(column * 3, row * 3, 2, 2); }
  }, [matrix]);
  const diagonalMean = Array.from({ length: 96 }, (_, index) => matrix[index * 96 + index]).reduce((sum, value) => sum + value, 0) / 96;
  return <section className="min-w-0 border p-3">
    <div className="border-b pb-2"><h3 className="text-[13px] font-semibold">Корреляция искусственных каналов 96×96</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">96 строк для каналов наблюдения ×96 столбцов для каналов повтора. Каждый маленький отделённый квадрат показывает одну пару.</p></div>
    <div className="mt-3 flex justify-center"><canvas ref={canvas} width="288" height="288" className="aspect-square w-full max-w-[288px] border [image-rendering:pixelated]" aria-label="Матрица корреляции 96 на 96 искусственных каналов" onMouseLeave={() => setHover(null)} onMouseMove={event => { const box = event.currentTarget.getBoundingClientRect(); const column = Math.max(0, Math.min(95, Math.floor((event.clientX - box.left) / box.width * 96))); const row = Math.max(0, Math.min(95, Math.floor((event.clientY - box.top) / box.height * 96))); setHover({ observation: row + 1, replay: column + 1, value: matrix[row * 96 + column] }); }}/></div>
    <div className="mt-2 grid grid-cols-5 gap-1 text-center font-mono text-[9px] text-muted-foreground" aria-label="Легенда корреляции"><span className="border-t-4 border-[#30526f] pt-1">−1</span><span className="border-t-4 border-[#2f3c49] pt-1">−0,5</span><span className="border-t-4 border-[#2e2c28] pt-1">0</span><span className="border-t-4 border-[#634036] pt-1">+0,5</span><span className="border-t-4 border-[#974330] pt-1">+1</span></div>
    <p className="mt-2 text-[10px] leading-5 text-muted-foreground">Синий: противоположное изменение. Тёмный: связи почти нет. Красный: совместное изменение.</p>
    <div className="mt-2 min-h-5 border p-2 font-mono text-[10px]">{hover ? `наблюдение ${hover.observation} × повтор ${hover.replay}: r=${hover.value.toFixed(3)}` : `Наведите на квадрат · средняя диагональ r=${diagonalMean.toFixed(2)}`}</div>
    <div className="mt-3 border-t pt-3 text-[10px] leading-5 text-muted-foreground"><p><strong className="text-foreground">Это не96 нейронов и не память96×96.</strong> Это9216 попарных сравнений96 программных каналов наблюдения с96 программными каналами повтора по32 сгенерированным моментам.</p><p className="mt-2">Матрицу создаёт browser surrogate. Это не экспорт89E, не FlyWire map, не запись живой мухи и не биологическое доказательство.</p></div>
  </section>;
}
