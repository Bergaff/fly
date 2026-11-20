import { useEffect, useMemo, useState } from "react";
import { PublicMirrorScene, type MirrorPose } from "@/views/public-mirror-scene";
import { LegalDialog, type LegalKind } from "@/components/legal-dialog";

const actions = {
  rest: { label: "Пауза", short: "пауза" },
  foreleg_rubbing: { label: "Потирание передних лап", short: "лапы" },
  head_directed_grooming: { label: "Движение лап к голове", short: "голова" },
  reach_withdraw: { label: "Вытянуть и убрать лапы", short: "reach" },
} as const;
type Action = keyof typeof actions;
type Slot = { action: Action; amplitude: number };
const initialSlots: Slot[] = [
  { action: "foreleg_rubbing", amplitude: .82 }, { action: "foreleg_rubbing", amplitude: 1 },
  { action: "head_directed_grooming", amplitude: .78 }, { action: "rest", amplitude: 0 },
  { action: "reach_withdraw", amplitude: .88 }, { action: "reach_withdraw", amplitude: .68 },
];
const ZERO: MirrorPose = { forelegLeft: 0, forelegRight: 0, headYaw: 0, headPitch: 0, reach: 0, bodyShift: 0 };
const button = "border bg-background px-3 py-2 text-[12px] hover:bg-secondary disabled:opacity-40";
const field = "border bg-background px-2 py-2 text-[12px]";

function actionPose(action: Action, amplitude: number, phase: number): MirrorPose {
  const wave = Math.sin(phase * Math.PI * 2), pulse = Math.sin(Math.min(1, phase) * Math.PI);
  if (action === "foreleg_rubbing") return { ...ZERO, forelegLeft: wave * amplitude, forelegRight: -wave * amplitude, headPitch: .08 * amplitude };
  if (action === "head_directed_grooming") return { ...ZERO, forelegLeft: (.55 + .3 * wave) * amplitude, forelegRight: (.55 - .3 * wave) * amplitude, headPitch: (.32 + .12 * wave) * amplitude, headYaw: .08 * wave };
  if (action === "reach_withdraw") return { ...ZERO, forelegLeft: .35 * pulse * amplitude, forelegRight: .35 * pulse * amplitude, reach: pulse * amplitude, bodyShift: .12 * pulse * amplitude };
  return ZERO;
}
function predictedPose(pose: MirrorPose, action: Action, amplitude: number): MirrorPose {
  const gain = action === "foreleg_rubbing" ? .94 : action === "head_directed_grooming" ? .965 : .955;
  const nonlinear = amplitude > 1 ? Math.max(.78, 1 - (amplitude - 1) * .28) : 1;
  return { forelegLeft: pose.forelegLeft * gain * nonlinear, forelegRight: pose.forelegRight * gain * nonlinear, headYaw: pose.headYaw * .96, headPitch: pose.headPitch * .95, reach: pose.reach * .94 * nonlinear, bodyShift: pose.bodyShift * .93 };
}

function Trace({ slots }: { slots: Slot[] }) {
  const points = slots.flatMap((slot, index) => Array.from({ length: 10 }, (_, i) => {
    const phase = i / 9, pose = actionPose(slot.action, slot.amplitude, phase); return { x: (index * 10 + i) / 59 * 100, y: 23 - (pose.forelegLeft - pose.forelegRight + pose.reach) * 8 };
  }));
  const path = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
  return <svg viewBox="0 0 100 46" className="h-20 w-full border" role="img" aria-label="Схематическая временная кривая выбранного движения">
    {[10,23,36].map(y => <line key={y} x1="0" x2="100" y1={y} y2={y} stroke="currentColor" opacity=".12" strokeWidth=".35" />)}
    <path d={path} fill="none" stroke="currentColor" strokeWidth="1.1" />
  </svg>;
}

const stages = [
  ["82–84", "Зрение", "Six-axis reconstruction и frozen view replication"],
  ["85–86", "Общее состояние", "Shared observation/execution population и три action identities"],
  ["87", "Причинный тест", "Preregistered digital lesions с operational effects"],
  ["88–89E", "Тело", "Actuator surrogate, closed loop и frozen policy replication"],
  ["90", "Биологическая привязка", "Mapping gate closed:5/9"],
];

export function PublicResearchShowcase() {
  useEffect(() => { document.title = "Fly: результаты серий82–90 и интерактивный повтор"; const meta = document.querySelector('meta[name="description"]') || document.head.appendChild(document.createElement("meta")); meta.setAttribute("name", "description"); meta.setAttribute("content", "Визуальный отчёт о функциональном synthetic mirror-like surrogate, frozen replication89E и biological mapping gate90."); }, []);
  const [slots, setSlots] = useState<Slot[]>(initialSlots); const [playing, setPlaying] = useState(false); const [elapsed, setElapsed] = useState(0); const [speed, setSpeed] = useState(1); const [legal, setLegal] = useState<LegalKind | null>(null);
  const slotDuration = .6, observationDuration = slots.length * slotDuration, delay = .5, total = observationDuration * 2 + delay;
  useEffect(() => { if (!playing) return; let frame = 0, previous: number | null = null; const step = (now: number) => { if (previous !== null) setElapsed(value => { const next = value + (now - previous!) / 1000 * speed; if (next >= total) { setPlaying(false); return total; } return next; }); previous = now; frame = requestAnimationFrame(step); }; frame = requestAnimationFrame(step); return () => cancelAnimationFrame(frame); }, [playing, speed, total]);
  const phase = elapsed < observationDuration ? "наблюдение" : elapsed < observationDuration + delay ? "задержка 0,5 с" : "автономная попытка повтора";
  const replayTime = elapsed - observationDuration - delay;
  const sequenceTime = elapsed < observationDuration ? elapsed : Math.max(0, replayTime);
  const slotIndex = Math.min(slots.length - 1, Math.floor(sequenceTime / slotDuration)); const localPhase = (sequenceTime / slotDuration) % 1; const slot = slots[slotIndex];
  const target = actionPose(slot.action, slot.amplitude, localPhase); const attempt = predictedPose(target, slot.action, slot.amplitude);
  const teacher = elapsed < observationDuration ? target : ZERO; const observer = elapsed >= observationDuration + delay ? attempt : ZERO;
  const inDomain = slots.filter(s => s.action !== "rest" && s.amplitude <= 1).length; const active = slots.filter(s => s.action !== "rest").length;
  const estimated = useMemo(() => active ? Math.max(.78, Math.min(.98, .965 - slots.reduce((sum, s) => sum + Math.max(0, s.amplitude - 1) * .08, 0) / active)) : 1, [slots, active]);
  const setSlot = (index: number, patch: Partial<Slot>) => setSlots(current => current.map((value, i) => i === index ? { ...value, ...patch } : value));
  const randomize = () => { const keys = Object.keys(actions) as Action[]; setSlots(slots.map((_, i) => ({ action: keys[1 + ((i * 7 + 2) % 3)], amplitude: .55 + ((i * 19 + 11) % 45) / 100 }))); setElapsed(0); setPlaying(false); };
  const restart = () => { setElapsed(0); setPlaying(true); };
  return <div className="h-full overflow-y-auto bg-background text-foreground">
    <header className="sticky top-0 z-20 border-b bg-background">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-8">
        <div><div className="font-mono text-[10px] uppercase tracking-[.16em] text-muted-foreground">Fly / research record / series82–90</div><div className="mt-1 text-[15px] font-semibold">Функциональный цифровой аналог наблюдения и повтора</div></div>
        <nav className="flex flex-wrap gap-1 text-[11px]" aria-label="Разделы страницы"><a className={button} href="#demo">Демонстратор</a><a className={button} href="#results">Результаты</a><a className={button} href="#limits">Ограничения</a><a className={button} href="#files">Данные</a></nav>
      </div>
    </header>
    <main className="mx-auto max-w-[1500px] px-4 pb-16 md:px-8">
      <section className="grid gap-7 border-b py-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(300px,.7fr)]">
        <div><div className="font-mono text-[11px] uppercase tracking-[.14em] text-muted-foreground">Заключение текущего roadmap</div><h1 className="mt-3 max-w-4xl text-3xl font-semibold leading-tight md:text-5xl">Муха-наблюдатель сохраняет состояние и воспроизводит действие в синтетической модели</h1><p className="mt-5 max-w-3xl text-[14px] leading-7 text-muted-foreground">Серии82–89E прошли путь от зрительного восстановления до closed-loop surrogate и frozen replication. Серия90 остановила биологическую интерпретацию: reviewed neural mapping отсутствует.</p></div>
        <dl className="grid grid-cols-2 border-l text-[12px]"><div className="border-b border-r p-4"><dt className="text-muted-foreground">Frozen89E</dt><dd className="mt-2 font-mono text-xl">216 /216</dd><dd>identity</dd></div><div className="border-b p-4"><dt className="text-muted-foreground">Trials</dt><dd className="mt-2 font-mono text-xl">648</dd><dd>safety pass</dd></div><div className="border-r p-4"><dt className="text-muted-foreground">Broad controls</dt><dd className="mt-2 font-mono text-xl">7 /8</dd><dd>passed</dd></div><div className="p-4"><dt className="text-muted-foreground">Series90</dt><dd className="mt-2 font-mono text-xl">5 /9</dd><dd>mapping closed</dd></div></dl>
      </section>

      <section id="demo" className="scroll-mt-20 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-3"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Интерактивный браузерный surrogate</div><h2 className="mt-1 text-2xl font-semibold">Задайте последовательность первой мухе</h2></div><p className="max-w-xl text-[11px] leading-5 text-muted-foreground">Работает полностью в браузере. Это наглядная deterministic реконструкция трёх исследованных action families, не запуск Python-модели89E и не новый научный результат.</p></div>
        <div className="mt-5 grid gap-6 xl:grid-cols-[390px_minmax(0,1fr)]">
          <div>
            <div className="flex items-center justify-between border-b pb-2"><strong className="text-[13px]">Таймлайн показа</strong><button className={button} onClick={randomize}>Другой пример</button></div>
            <p className="py-2 text-[11px] leading-5 text-muted-foreground">Каждый блок длится0,6 с. Выберите одно из трёх действий, знакомых frozen policy, и амплитуду. Значения выше100% помечаются как выход за проверенную область.</p>
            <div className="space-y-1">{slots.map((item, index) => <div key={index} className={`grid grid-cols-[28px_minmax(0,1fr)_90px] items-center gap-2 border-b py-2 ${index === slotIndex && playing ? "bg-secondary" : ""}`}><span className="font-mono text-[10px]">{index + 1}</span><select aria-label={`Действие ${index + 1}`} className={field} value={item.action} onChange={e => setSlot(index, { action: e.target.value as Action, amplitude: e.target.value === "rest" ? 0 : Math.max(.4, item.amplitude) })}>{Object.entries(actions).map(([id, value]) => <option key={id} value={id}>{value.label}</option>)}</select><label className="grid grid-cols-[1fr_34px] items-center gap-1 text-[10px]"><input aria-label={`Амплитуда ${index + 1}`} type="range" min="0" max="1.25" step=".05" disabled={item.action === "rest"} value={item.amplitude} onChange={e => setSlot(index, { amplitude: Number(e.target.value) })} className="accent-foreground"/><span className="font-mono">{Math.round(item.amplitude * 100)}%</span></label></div>)}</div>
            <Trace slots={slots} />
            <div className="mt-3 flex flex-wrap items-center gap-2"><button className={button} onClick={() => setPlaying(value => !value)}>{playing ? "Пауза" : elapsed >= total ? "Сначала" : "Продолжить"}</button><button className={button} onClick={restart}>Запустить показ и повтор</button><label className="ml-auto text-[11px]">скорость <select className={field} value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value=".5">0,5×</option><option value="1">1×</option><option value="1.5">1,5×</option></select></label></div>
            <input aria-label="Время демонстрации" type="range" min="0" max={total} step=".01" value={elapsed} onChange={e => { setPlaying(false); setElapsed(Number(e.target.value)); }} className="mt-3 w-full accent-foreground"/>
            <div className="flex justify-between font-mono text-[10px] text-muted-foreground"><span>0,00</span><span>{elapsed.toFixed(2)} / {total.toFixed(2)} с</span></div>
          </div>
          <div><PublicMirrorScene teacher={teacher} observer={observer} teacherVisible={elapsed < observationDuration} phase={phase}/><div className="grid grid-cols-2 border-x border-b text-[11px] md:grid-cols-4"><div className="border-r p-3"><span className="text-muted-foreground">Фаза</span><strong className="mt-1 block">{phase}</strong></div><div className="border-r p-3"><span className="text-muted-foreground">Текущий блок</span><strong className="mt-1 block">{actions[slot.action].short}</strong></div><div className="border-r p-3"><span className="text-muted-foreground">В tested range</span><strong className="mt-1 block font-mono">{inDomain}/{active || 0}</strong></div><div className="p-3"><span className="text-muted-foreground">Demo fidelity</span><strong className="mt-1 block font-mono">{(estimated * 100).toFixed(1)}%</strong></div></div><p className="mt-2 text-[10px] leading-5 text-muted-foreground">Во время наблюдения двигается муха01. После фиксированной задержки муха02 повторяет выбранную последовательность. Fidelity является параметром визуального surrogate, а не опубликованной биологической метрикой.</p></div>
        </div>
      </section>

      <section id="results" className="scroll-mt-20 border-t py-8"><div className="grid gap-7 lg:grid-cols-[.72fr_1.28fr]"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Проверенный путь</div><h2 className="mt-2 text-2xl font-semibold">Что именно было сделано</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Каждый следующий этап открывался только после заранее заданных gates. Failed и near-miss серии сохранены в истории, а не исключены из вывода.</p></div><ol className="border-t">{stages.map(([id,title,text]) => <li key={id} className="grid grid-cols-[72px_150px_minmax(0,1fr)] gap-3 border-b py-3 text-[12px]"><span className="font-mono text-muted-foreground">{id}</span><strong>{title}</strong><span className="text-muted-foreground">{text}</span></li>)}</ol></div>
        <div className="mt-8 grid gap-px border bg-border md:grid-cols-2"><div className="bg-background p-5"><h3 className="text-[14px] font-semibold">Frozen89E, replicated go</h3><dl className="mt-4 grid grid-cols-2 gap-y-3 text-[11px]"><div><dt className="text-muted-foreground">Identity</dt><dd className="font-mono">216/216</dd></div><div><dt className="text-muted-foreground">Safety/recovery/completion</dt><dd className="font-mono">648/648</dd></div><div><dt className="text-muted-foreground">Contact soft/angle/common</dt><dd className="font-mono">598/636/633</dd></div><div><dt className="text-muted-foreground">Candidate contact mean</dt><dd className="font-mono">0.124517</dd></div></dl></div><div className="bg-background p-5"><h3 className="text-[14px] font-semibold">Series90, mapping closed</h3><p className="mt-4 text-[12px] leading-6 text-muted-foreground">Official components существуют, но reviewed FlyVis→FlyWire mapping, fixed transduction и validated DN/VNC/motor readout отсутствуют. Поэтому конкретные neurons не называются зеркальными.</p></div></div>
      </section>

      <section id="limits" className="scroll-mt-20 border-t py-8"><div className="grid gap-6 md:grid-cols-2"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Допустимый вывод</div><h2 className="mt-2 text-xl font-semibold">Функциональный synthetic mirror-like механизм</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Наблюдение связано с внутренним состоянием, задержкой, автономным воспроизведением, causal digital lesions и actuator surrogate. Итоговая policy прошла frozen replication.</p></div><div className="border-l pl-6"><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Недопустимый вывод</div><h2 className="mt-2 text-xl font-semibold">Не доказательство биологических зеркальных нейронов</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Нет reviewed end-to-end neural mapping, natural vision, muscle dynamics, collision forces и interventions у живых мух. Browser demo также не изменяет этот статус.</p></div></div></section>

      <section id="files" className="scroll-mt-20 border-t py-8"><div className="flex flex-wrap justify-between gap-5"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Воспроизводимость</div><h2 className="mt-2 text-xl font-semibold">Отчёты и проверяемые артефакты находятся в репозитории</h2><p className="mt-3 max-w-3xl text-[12px] leading-6 text-muted-foreground">Для89E сохранены trial-level extract, independent verifier и report. Для90 сохранены source audit, machine-readable decision и gate runner. На этой странице нет сервера: заданные движения остаются в браузере и никуда не отправляются.</p></div><a className={button} href="https://github.com/Bergaff/fly" target="_blank" rel="noreferrer">Открыть репозиторий</a></div></section>
    </main>
    <footer className="border-t px-4 py-5 text-center text-[10px] text-muted-foreground"><div>Synthetic research demonstrator · no biological diagnosis or animal claim · данные ввода не передаются</div><div className="mt-2 flex justify-center gap-3"><button className="underline" onClick={() => setLegal("terms")}>Условия использования</button><button className="underline" onClick={() => setLegal("privacy")}>Политика конфиденциальности</button></div></footer>
    <LegalDialog kind={legal} onClose={() => setLegal(null)} />
  </div>;
}
