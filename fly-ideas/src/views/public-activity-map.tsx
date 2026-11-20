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
    const sharedBackground = ((index * 17 + 11) % 29 === 0 ? .18 : 0) * amplitude;
    const routeBias = execution ? ((index % 12) / 12) * .035 : ((7 - Math.floor(index / 12)) / 8) * .025;
    return clamp((peak * wave + sharedBackground + routeBias) * amplitude * (execution ? .94 : 1));
  });
}

function Cells({ values, label }: { values: number[]; label: string }) {
  return <div><div className="mb-1 flex justify-between text-[10px]"><span>{label}</span><span className="font-mono text-muted-foreground">96 units</span></div><div className="grid grid-cols-12 gap-px border bg-border p-px">{values.map((value, index) => <span key={index} title={`unit ${index + 1}: ${value.toFixed(3)}`} className="aspect-square" style={{ backgroundColor: `rgb(${Math.round(47 + value * 120)},${Math.round(48 + value * 91)},${Math.round(43 + value * 48)})` }} />)}</div></div>;
}

export function PublicActivityMap({ action, amplitude, phase }: { action: ActivityKind; amplitude: number; phase: number }) {
  const observation = activity(action, amplitude, phase, false); const execution = activity(action, amplitude, phase, true);
  const threshold = .32; const both = observation.filter((value, index) => value >= threshold && execution[index] >= threshold).length;
  const observationOnly = observation.filter((value, index) => value >= threshold && execution[index] < threshold).length;
  const executionOnly = execution.filter((value, index) => value >= threshold && observation[index] < threshold).length;
  return <section className="border p-3">
    <div className="flex flex-wrap items-start justify-between gap-2 border-b pb-2"><div><h3 className="text-[13px] font-semibold">Карта активности: наблюдение и повтор</h3><p className="mt-1 text-[10px] leading-5 text-muted-foreground">96 искусственных units. Верхние карты показывают величину сигнала, нижняя — где активность общая и где различается.</p></div><div className="font-mono text-[10px] text-muted-foreground">порог {threshold.toFixed(2)}</div></div>
    <div className="mt-3 grid gap-3 sm:grid-cols-2"><Cells values={observation} label="Во время наблюдения"/><Cells values={execution} label="Во время собственного повтора"/></div>
    <div className="mt-3"><div className="mb-1 text-[10px]">Совмещение</div><div className="grid grid-cols-12 gap-px border bg-border p-px">{observation.map((value, index) => { const o = value >= threshold, e = execution[index] >= threshold; const color = o && e ? "#77764e" : o ? "#8a633f" : e ? "#526a70" : "#302f2b"; return <span key={index} title={`unit ${index + 1}: observation ${value.toFixed(3)}, replay ${execution[index].toFixed(3)}, delta ${(execution[index] - value).toFixed(3)}`} className="aspect-square" style={{ backgroundColor: color }} />; })}</div></div>
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px]"><span><i className="mr-1 inline-block size-2 bg-[#77764e]"/>оба режима: <b>{both}</b></span><span><i className="mr-1 inline-block size-2 bg-[#8a633f]"/>только наблюдение: <b>{observationOnly}</b></span><span><i className="mr-1 inline-block size-2 bg-[#526a70]"/>только повтор: <b>{executionOnly}</b></span></div>
    <p className="mt-2 border-t pt-2 text-[10px] leading-5 text-muted-foreground">Это динамическая схема browser surrogate, похожая на 96-unit карту в локальном приложении. Она объясняет идею shared activity, но не является экспортом нейронной записи, FlyWire map или новым результатом89E.</p>
  </section>;
}
