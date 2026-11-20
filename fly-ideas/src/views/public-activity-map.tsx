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

function signalColor(value: number) {
  return `rgb(${Math.round(47 + value * 120)},${Math.round(48 + value * 91)},${Math.round(43 + value * 48)})`;
}
function differenceColor(value: number) {
  const amount = Math.min(1, Math.abs(value) * 4), base = [46, 44, 40], target = value < 0 ? [55, 85, 111] : [145, 71, 50];
  return `rgb(${base.map((channel, index) => Math.round(channel + (target[index] - channel) * amount)).join(",")})`;
}
function Cells({ values, label, difference = false }: { values: number[]; label: string; difference?: boolean }) {
  return <div><div className="mb-1 flex justify-between text-[10px]"><span>{label}</span><span className="font-mono text-muted-foreground">12×8 = 96 каналов</span></div><div className="grid grid-cols-12 gap-0.5 border bg-border p-0.5">{values.map((value, index) => <span key={index} title={`канал ${index + 1}: ${value >= 0 ? "+" : ""}${value.toFixed(3)}`} className="aspect-square min-h-2 border border-black/15" style={{ backgroundColor: difference ? differenceColor(value) : signalColor(value) }} />)}</div></div>;
}

export function PublicActivityMap({ action, amplitude, phase }: { action: ActivityKind; amplitude: number; phase: number }) {
  const observation = activity(action, amplitude, phase, false); const execution = activity(action, amplitude, phase, true); const difference = execution.map((value, index) => value - observation[index]);
  const threshold = .32; const activeObservation = observation.filter(value => value >= threshold).length; const activeExecution = execution.filter(value => value >= threshold).length;
  const shared = observation.filter((value, index) => value >= threshold && execution[index] >= threshold).length;
  const meanDifference = difference.reduce((sum, value) => sum + Math.abs(value), 0) / 96;
  return <section className="min-w-0 border p-3">
    <div className="border-b pb-2"><h3 className="text-[13px] font-semibold">96 искусственных каналов модели</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">Одна клетка на всех трёх картах — один и тот же программный канал. Так видно текущий сигнал при наблюдении, при повторе и разницу между ними.</p></div>
    <div className="mt-3 space-y-3"><Cells values={observation} label="Во время наблюдения"/><Cells values={execution} label="Во время собственного повтора"/><Cells values={difference} label="Разница: повтор минус наблюдение" difference/></div>
    <div className="mt-3 border p-2 text-[10px]" aria-label="Легенда карт сигналов и разницы"><strong>Легенда</strong><div className="mt-2 grid gap-2 sm:grid-cols-2"><div><div className="mb-1 text-muted-foreground">Сигнал канала</div><div className="grid grid-cols-[18px_1fr_18px] items-center gap-2"><span>0</span><div className="flex h-3 overflow-hidden border">{[0,.2,.4,.6,.8,1].map(value => <span key={value} className="flex-1" style={{ backgroundColor: signalColor(value) }}/>)}</div><span>1</span></div><div className="mt-1 text-muted-foreground">темнее: слабее, светлее: сильнее</div></div><div><div className="mb-1 text-muted-foreground">Разница «повтор минус наблюдение»</div><div className="grid grid-cols-[70px_1fr_70px] items-center gap-2"><span className="text-[#6384a1]">повтор слабее</span><div className="flex h-3 overflow-hidden border">{[-.25,-.12,0,.12,.25].map(value => <span key={value} className="flex-1" style={{ backgroundColor: differenceColor(value) }}/>)}</div><span className="text-right text-[#a66552]">повтор сильнее</span></div><div className="mt-1 text-muted-foreground">синий: меньше, серый: одинаково, красный: больше. Это прямое вычитание, не корреляция.</div></div></div></div>
    <div className="mt-3 grid grid-cols-2 gap-px border bg-border text-[10px] sm:grid-cols-4"><div className="bg-background p-2"><span className="text-muted-foreground">активны при наблюдении</span><strong className="mt-1 block font-mono">{activeObservation}</strong></div><div className="bg-background p-2"><span className="text-muted-foreground">активны при повторе</span><strong className="mt-1 block font-mono">{activeExecution}</strong></div><div className="bg-background p-2"><span className="text-muted-foreground">активны в обоих</span><strong className="mt-1 block font-mono">{shared}</strong></div><div className="bg-background p-2"><span className="text-muted-foreground">средняя |разница|</span><strong className="mt-1 block font-mono">{meanDifference.toFixed(3)}</strong></div></div>
    <div className="mt-3 border-t pt-3 text-[10px] leading-5 text-muted-foreground"><p><strong className="text-foreground">Это не96 нейронов.</strong> Число96 было инженерным размером rich-представления изображения в раннем прототипе: каждый канал хранит вычисленный признак, а не анатомическую клетку.</p><p className="mt-2"><strong className="text-foreground">Это не память96×96.</strong> В локальном демонстраторе серии69 сохранённое внутреннее состояние имело72 числовых коэффициента. На публичной странице реальные72 коэффициента не загружаются; показана только объясняющая схема сигналов.</p><p className="mt-2">Значения здесь генерирует browser surrogate. Это не экспорт89E, не FlyWire map и не запись активности живой мухи.</p></div>
  </section>;
}
