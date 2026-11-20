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

function Cells({ values, label }: { values: number[]; label: string }) {
  return <div><div className="mb-1 flex justify-between text-[10px]"><span>{label}</span><span className="font-mono text-muted-foreground">96 units</span></div><div className="grid grid-cols-12 gap-px border bg-border p-px">{values.map((value, index) => <span key={index} title={`unit ${index + 1}: ${value.toFixed(3)}`} className="aspect-square" style={{ backgroundColor: `rgb(${Math.round(47 + value * 120)},${Math.round(48 + value * 91)},${Math.round(43 + value * 48)})` }} />)}</div></div>;
}

function pearson(a: number[], b: number[]) {
  const am = a.reduce((sum, value) => sum + value, 0) / a.length, bm = b.reduce((sum, value) => sum + value, 0) / b.length;
  let numerator = 0, av = 0, bv = 0;
  for (let i = 0; i < a.length; i++) { const x = a[i] - am, y = b[i] - bm; numerator += x * y; av += x * x; bv += y * y; }
  return av > 1e-12 && bv > 1e-12 ? Math.max(-1, Math.min(1, numerator / Math.sqrt(av * bv))) : 0;
}
function correlationColor(value: number): [number, number, number, number] {
  const base: [number, number, number] = [46, 44, 40], blue: [number, number, number] = [48, 82, 111], red: [number, number, number] = [151, 67, 48];
  const amount = Math.abs(value), target = value < 0 ? blue : red;
  return [Math.round(base[0] + (target[0] - base[0]) * amount), Math.round(base[1] + (target[1] - base[1]) * amount), Math.round(base[2] + (target[2] - base[2]) * amount), 255];
}

function CorrelationMatrix({ action, amplitude }: { action: ActivityKind; amplitude: number }) {
  const canvas = useRef<HTMLCanvasElement>(null); const [hover, setHover] = useState<{ observation: number; replay: number; value: number } | null>(null);
  const matrix = useMemo(() => {
    const phases = Array.from({ length: 32 }, (_, index) => index / 32);
    const observation = phases.map(phase => activity(action, amplitude, phase, false)); const replay = phases.map(phase => activity(action, amplitude, phase, true));
    const result = new Float32Array(96 * 96);
    for (let row = 0; row < 96; row++) for (let column = 0; column < 96; column++) result[row * 96 + column] = pearson(observation.map(values => values[row]), replay.map(values => values[column]));
    return result;
  }, [action, amplitude]);
  useEffect(() => {
    const context = canvas.current?.getContext("2d"); if (!context) return; const image = context.createImageData(96, 96);
    for (let index = 0; index < matrix.length; index++) image.data.set(correlationColor(matrix[index]), index * 4);
    context.putImageData(image, 0, 0);
  }, [matrix]);
  const sameUnit = Array.from({ length: 96 }, (_, index) => matrix[index * 96 + index]); const diagonalMean = sameUnit.reduce((sum, value) => sum + value, 0) / 96;
  return <div className="mt-3 border-t pt-3"><div className="mb-2 flex flex-wrap items-end justify-between gap-2"><div><div className="text-[11px] font-semibold">Матрица корреляции 96×96</div><p className="mt-1 text-[10px] leading-5 text-muted-foreground">Строки: units при наблюдении. Столбцы: units при повторе. Корреляция рассчитана по32 моментам одного цикла.</p></div><span className="font-mono text-[10px]">средняя диагональ {diagonalMean.toFixed(2)}</span></div>
    <canvas ref={canvas} width="96" height="96" className="aspect-square w-full border [image-rendering:pixelated]" aria-label="Матрица корреляции активности наблюдения и повтора" onMouseLeave={() => setHover(null)} onMouseMove={event => { const box = event.currentTarget.getBoundingClientRect(); const column = Math.max(0, Math.min(95, Math.floor((event.clientX - box.left) / box.width * 96))); const row = Math.max(0, Math.min(95, Math.floor((event.clientY - box.top) / box.height * 96))); setHover({ observation: row + 1, replay: column + 1, value: matrix[row * 96 + column] }); }}/>
    <div className="mt-2 grid grid-cols-5 gap-1 text-center font-mono text-[9px] text-muted-foreground"><span className="border-t-4 border-[#30526f] pt-1">−1</span><span className="border-t-4 border-[#2f3c49] pt-1">−0,5</span><span className="border-t-4 border-[#2e2c28] pt-1">0</span><span className="border-t-4 border-[#634036] pt-1">+0,5</span><span className="border-t-4 border-[#974330] pt-1">+1</span></div>
    <div className="mt-2 min-h-5 font-mono text-[10px]">{hover ? `наблюдение ${hover.observation} × повтор ${hover.replay}: r=${hover.value.toFixed(3)}` : "Наведите на клетку, чтобы увидеть пару units и коэффициент r."}</div>
  </div>;
}

export function PublicActivityMap({ action, amplitude, phase }: { action: ActivityKind; amplitude: number; phase: number }) {
  const observation = activity(action, amplitude, phase, false); const execution = activity(action, amplitude, phase, true);
  return <section className="min-w-0 border p-3">
    <div className="border-b pb-2"><h3 className="text-[13px] font-semibold">Карта активности: наблюдение и повтор</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">Две карты показывают текущий сигнал96 искусственных units. Матрица ниже сравнивает полные временные профили.</p></div>
    <div className="mt-3 grid gap-3 sm:grid-cols-2"><Cells values={observation} label="Во время наблюдения"/><Cells values={execution} label="Во время собственного повтора"/></div>
    <CorrelationMatrix action={action} amplitude={amplitude}/>
    <p className="mt-3 border-t pt-2 text-[10px] leading-5 text-muted-foreground">Это динамическая схема browser surrogate, похожая на96-unit карту в локальном приложении. Корреляция относится только к сгенерированным здесь искусственным сигналам. Это не экспорт нейронной записи, FlyWire map или новый результат89E.</p>
  </section>;
}
