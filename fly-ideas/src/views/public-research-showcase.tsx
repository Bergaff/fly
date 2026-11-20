import { useEffect, useMemo, useState } from "react";
import { PublicMirrorScene, type MirrorPose } from "@/views/public-mirror-scene";
import { LegalDialog, type LegalKind } from "@/components/legal-dialog";
import { PublicActivityMap } from "@/views/public-activity-map";

const actions = {
  rest: { label: "Пауза", short: "пауза" },
  wing_display: { label: "Взмахи крыльями", short: "крылья" },
  foreleg_rubbing: { label: "Потирание передних лап", short: "лапы" },
  head_directed_grooming: { label: "Движение лап к голове", short: "голова" },
  reach_withdraw: { label: "Вытянуть и убрать лапы", short: "reach" },
} as const;
type Action = keyof typeof actions;
const activeActions: Action[] = ["wing_display", "foreleg_rubbing", "head_directed_grooming", "reach_withdraw"];
type Slot = { action: Action; amplitude: number };
const initialSlots: Slot[] = [
  { action: "wing_display", amplitude: .86 }, { action: "foreleg_rubbing", amplitude: 1 },
  { action: "head_directed_grooming", amplitude: .78 }, { action: "rest", amplitude: 0 },
  { action: "reach_withdraw", amplitude: .88 }, { action: "wing_display", amplitude: .68 },
];
const ZERO: MirrorPose = { forelegLeft: 0, forelegRight: 0, headYaw: 0, headPitch: 0, reach: 0, bodyShift: 0, wingLeft: 0, wingRight: 0 };
const button = "border bg-background px-3 py-2 text-[12px] hover:bg-secondary disabled:opacity-40";
const field = "min-w-0 border bg-background px-2 py-2 text-[12px]";
const randomUnit = () => { const value = new Uint32Array(1); crypto.getRandomValues(value); return value[0] / 4294967296; };

function actionPose(action: Action, amplitude: number, phase: number): MirrorPose {
  const wave = Math.sin(phase * Math.PI * 2), pulse = Math.sin(Math.min(1, phase) * Math.PI);
  if (action === "wing_display") return { ...ZERO, wingLeft: wave * amplitude, wingRight: -wave * amplitude, bodyShift: .035 * Math.sin(phase * Math.PI * 4) * amplitude };
  if (action === "foreleg_rubbing") return { ...ZERO, forelegLeft: wave * amplitude, forelegRight: -wave * amplitude, headPitch: .08 * amplitude };
  if (action === "head_directed_grooming") return { ...ZERO, forelegLeft: (.55 + .3 * wave) * amplitude, forelegRight: (.55 - .3 * wave) * amplitude, headPitch: (.32 + .12 * wave) * amplitude, headYaw: .08 * wave };
  if (action === "reach_withdraw") return { ...ZERO, forelegLeft: .35 * pulse * amplitude, forelegRight: .35 * pulse * amplitude, reach: pulse * amplitude, bodyShift: .12 * pulse * amplitude };
  return ZERO;
}
function predictedPose(pose: MirrorPose, action: Action, amplitude: number): MirrorPose {
  const gain = action === "foreleg_rubbing" ? .94 : action === "head_directed_grooming" ? .965 : .955;
  const nonlinear = amplitude > 1 ? Math.max(.78, 1 - (amplitude - 1) * .28) : 1;
  return { forelegLeft: pose.forelegLeft * gain * nonlinear, forelegRight: pose.forelegRight * gain * nonlinear, headYaw: pose.headYaw * .96, headPitch: pose.headPitch * .95, reach: pose.reach * .94 * nonlinear, bodyShift: pose.bodyShift * .93, wingLeft: pose.wingLeft * .95 * nonlinear, wingRight: pose.wingRight * .95 * nonlinear };
}
function demoSimilarity(slots: Slot[]) {
  const axes = Object.keys(ZERO) as (keyof MirrorPose)[]; let signal = 0, error = 0;
  slots.forEach(slot => { for (let sample = 1; sample <= 12; sample += 1) { const target = actionPose(slot.action, slot.amplitude, sample / 13); const attempt = predictedPose(target, slot.action, slot.amplitude); axes.forEach(axis => { signal += Math.abs(target[axis]); error += Math.abs(attempt[axis] - target[axis]); }); } });
  return signal ? Math.max(0, 1 - error / signal) : 1;
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
  ["82–84", "Увидеть движение", "Модель восстанавливала шесть углов движения по изображению и проверялась на новых ракурсах."],
  ["85–86", "Связать показ и повтор", "Проверялось, возникает ли похожая внутренняя активность при наблюдении и при собственном выполнении трёх действий."],
  ["87", "Отключить части модели", "Группы искусственных units выключались по заранее записанному плану; после этого отдельно измерялось ухудшение распознавания и движения."],
  ["88–89E", "Управлять телом", "Предсказанные углы передавались упрощённому телу. Финальная неизменяемая модель повторила результат на новой проверочной выборке."],
  ["90", "Проверить связь с биологией", "Готовой проверенной цепи от зрительных типов FlyVis через FlyWire к моторным нейронам не найдено. Поэтому биологический вывод не сделан."],
];

export function PublicResearchShowcase() {
  useEffect(() => { document.title = "Fly: результаты серий82–90 и интерактивный повтор"; const meta = document.querySelector('meta[name="description"]') || document.head.appendChild(document.createElement("meta")); meta.setAttribute("name", "description"); meta.setAttribute("content", "Визуальный отчёт о функциональном synthetic mirror-like surrogate, frozen replication89E и biological mapping gate90."); }, []);
  const [slots, setSlots] = useState<Slot[]>(initialSlots); const [playing, setPlaying] = useState(false); const [elapsed, setElapsed] = useState(0); const [speed, setSpeed] = useState(1); const [legal, setLegal] = useState<LegalKind | null>(null);
  const slotDuration = .6, observationDuration = slots.length * slotDuration, delay = .5, total = observationDuration * 2 + delay;
  useEffect(() => { if (!playing) return; let frame = 0, previous: number | null = null; const step = (now: number) => { if (previous !== null) setElapsed(value => (value + (now - previous!) / 1000 * speed) % total); previous = now; frame = requestAnimationFrame(step); }; frame = requestAnimationFrame(step); return () => cancelAnimationFrame(frame); }, [playing, speed, total]);
  const phase = elapsed < observationDuration ? "наблюдение" : elapsed < observationDuration + delay ? "задержка 0,5 с" : "автономная попытка повтора";
  const replayTime = elapsed - observationDuration - delay;
  const sequenceTime = elapsed < observationDuration ? elapsed : Math.max(0, replayTime);
  const slotIndex = Math.min(slots.length - 1, Math.floor(sequenceTime / slotDuration)); const localPhase = (sequenceTime / slotDuration) % 1; const slot = slots[slotIndex];
  const target = actionPose(slot.action, slot.amplitude, localPhase); const attempt = predictedPose(target, slot.action, slot.amplitude);
  const teacher = elapsed < observationDuration ? target : ZERO; const observer = elapsed >= observationDuration + delay ? attempt : ZERO;
  const inDomain = slots.filter(s => s.action !== "rest" && s.amplitude <= 1).length; const active = slots.filter(s => s.action !== "rest").length;
  const estimated = useMemo(() => demoSimilarity(slots), [slots]);
  const setSlot = (index: number, patch: Partial<Slot>) => { setSlots(current => current.map((value, i) => i === index ? { ...value, ...patch } : value)); if (!playing) setElapsed(index * slotDuration + slotDuration * .25); };
  const randomize = () => { setSlots(current => { const next = current.map(() => ({ action: activeActions[Math.floor(randomUnit() * activeActions.length)], amplitude: Math.round((.5 + randomUnit() * .5) * 20) / 20 })); if (next.every((value, index) => value.action === current[index].action && value.amplitude === current[index].amplitude)) next[0] = { action: activeActions[(activeActions.indexOf(next[0].action) + 1) % activeActions.length], amplitude: next[0].amplitude }; return next; }); setElapsed(0); setPlaying(false); };
  const togglePlayback = () => { if (playing) { setPlaying(false); setElapsed(0); return; } setElapsed(0); setPlaying(true); };
  const playbackLabel = playing ? "Стоп" : "Старт";
  return <div className="h-full overflow-y-auto bg-background text-foreground">
    <header className="sticky top-0 z-20 border-b bg-background">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-8">
        <div><div className="font-mono text-[10px] uppercase tracking-[.16em] text-muted-foreground">Fly / research record / series82–90</div><div className="mt-1 text-[15px] font-semibold">Функциональный цифровой аналог наблюдения и повтора</div></div>
        <nav className="flex flex-wrap gap-1 text-[11px]" aria-label="Разделы страницы"><a className={button} href="#demo">Демонстратор</a><a className={button} href="#results">Результаты</a><a className={button} href="#limits">Ограничения</a><a className={button} href="#next">Следующие шаги</a><a className={button} href="#files">Данные</a></nav>
      </div>
    </header>
    <main className="mx-auto max-w-[1500px] px-4 pb-16 md:px-8">
      <section className="border-b py-7"><div className="font-mono text-[11px] uppercase tracking-[.14em] text-muted-foreground">Две виртуальные мухи · наблюдение · задержка · повтор</div><h1 className="mt-3 max-w-5xl text-3xl font-semibold leading-tight md:text-5xl">Составьте движение и посмотрите, как вторая муха пытается его повторить</h1><p className="mt-4 max-w-3xl text-[13px] leading-6 text-muted-foreground">Интерактивная часть объясняет логику эксперимента. Ниже отдельно и простыми словами описано, что действительно проверено, а что остаётся демонстрацией.</p></section>

      <section id="demo" className="scroll-mt-20 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-3"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Интерактивный браузерный surrogate</div><h2 className="mt-1 text-2xl font-semibold">Задайте последовательность первой мухе</h2></div><p className="max-w-xl text-[11px] leading-5 text-muted-foreground">Работает полностью в браузере. Это наглядная deterministic реконструкция крыльев из ранних серий и трёх action families86–89E, не запуск Python-модели89E и не новый научный результат.</p></div>
        <div className="relative z-10 mt-5 bg-background">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2"><strong className="text-[13px]">Таймлайн показа</strong><button className={button} onClick={randomize}>Другой пример</button></div>
          <p className="py-2 text-[11px] leading-5 text-muted-foreground">Каждый блок длится0,6 с. Выберите взмахи крыльями либо одно из трёх действий frozen policy89E и задайте амплитуду. Значения выше100% помечаются как выход за проверенную область.</p>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{slots.map((item, index) => <div key={index} className={`min-w-0 border p-3 ${index === slotIndex && playing ? "bg-secondary" : "bg-background"}`}><div className="flex items-center gap-2"><span className="font-mono text-[10px]">{index + 1}</span><select aria-label={`Действие ${index + 1}`} className={`${field} w-full`} value={item.action} onChange={e => setSlot(index, { action: e.target.value as Action, amplitude: e.target.value === "rest" ? 0 : Math.max(.4, item.amplitude) })}>{Object.entries(actions).map(([id, value]) => <option key={id} value={id}>{value.label}</option>)}</select></div><label className="mt-3 grid grid-cols-[minmax(0,1fr)_42px] items-center gap-2 text-[10px]"><input aria-label={`Амплитуда ${index + 1}`} type="range" min="0" max="1.25" step=".05" disabled={item.action === "rest"} value={item.amplitude} onChange={e => setSlot(index, { amplitude: Number(e.target.value) })} className="min-w-0 w-full accent-foreground"/><span className="font-mono text-right">{Math.round(item.amplitude * 100)}%</span></label></div>)}</div>
          <div className="mt-3"><Trace slots={slots} /></div>
          <div className="mt-3 flex flex-wrap items-center gap-2"><button className={button} onClick={togglePlayback}>{playbackLabel}</button><span className="text-[10px] text-muted-foreground">После старта показ повторяется по кругу до нажатия «Стоп».</span><label className="ml-auto text-[11px]">скорость <select className={field} value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value=".5">0,5×</option><option value="1">1×</option><option value="1.5">1,5×</option></select></label></div>
          <input aria-label="Время демонстрации" type="range" min="0" max={total} step=".01" value={elapsed} onChange={e => { setPlaying(false); setElapsed(Number(e.target.value)); }} className="mt-3 w-full accent-foreground"/>
          <div className="flex justify-between font-mono text-[10px] text-muted-foreground"><span>0,00</span><span>{elapsed.toFixed(2)} / {total.toFixed(2)} с</span></div>
        </div>
        <div className="mt-6 grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="min-w-0"><PublicMirrorScene teacher={teacher} observer={observer} teacherVisible={elapsed < observationDuration} phase={phase}/><div className="grid grid-cols-2 border-x border-b text-[11px] md:grid-cols-4"><div className="border-r p-3"><span className="text-muted-foreground">Сейчас</span><strong className="mt-1 block">{phase}</strong></div><div className="border-r p-3"><span className="text-muted-foreground">Движение</span><strong className="mt-1 block">{actions[slot.action].short}</strong></div><div className="border-r p-3"><span className="text-muted-foreground">В проверенном диапазоне</span><strong className="mt-1 block font-mono">{inDomain}/{active || 0}</strong></div><div className="p-3"><span className="text-muted-foreground">Сходство траекторий в demo</span><strong className="mt-1 block font-mono">{(estimated * 100).toFixed(1)}%</strong></div></div><p className="mt-2 text-[10px] leading-5 text-muted-foreground">Сначала двигается муха01. После задержки муха02 повторяет последовательность. Процент пересчитывается при изменении действий и амплитуды: это единица минус суммарная абсолютная ошибка позы, делённая на суммарное движение первой мухи. Он описывает только эту браузерную анимацию и не является корреляцией, результатом89E или биологической метрикой.</p></div>
          <PublicActivityMap action={slot.action} amplitude={slot.amplitude} phase={localPhase}/>
        </div>
      </section>

      <section id="results" className="scroll-mt-20 border-t py-8"><div className="grid gap-7 lg:grid-cols-[.72fr_1.28fr]"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Ход исследования</div><h2 className="mt-2 text-2xl font-semibold">От изображения к попытке собственного движения</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Этапы шли по порядку. Неудачные проверки тоже сохранены: модель менялась только в новой серии, а финальный вариант отдельно проверялся без дообучения.</p></div><ol className="border-t">{stages.map(([id,title,text]) => <li key={id} className="grid gap-1 border-b py-4 text-[12px] sm:grid-cols-[72px_170px_minmax(0,1fr)] sm:gap-3"><span className="font-mono text-muted-foreground">{id}</span><strong>{title}</strong><span className="leading-5 text-muted-foreground">{text}</span></li>)}</ol></div>
        <div className="mt-8 grid gap-px border bg-border md:grid-cols-2"><div className="bg-background p-5"><h3 className="text-[14px] font-semibold">Что подтвердила финальная проверка</h3><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Неизменяемая модель получила216 новых сочетаний движения и ракурса. Во всех216 она правильно определила одно из трёх действий. Для каждого сочетания тело запускалось из трёх начальных состояний: всего648 попыток. Все648 завершились без зарегистрированных нарушений безопасности и с восстановлением движения.</p><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Модель также сравнивали с восемью упрощёнными вариантами управления. Она прошла заранее заданные требования в семи сравнениях из восьми. Это подтверждает устойчивость внутри синтетического теста, но не измеряет поведение живой мухи.</p></div><div className="bg-background p-5"><h3 className="text-[14px] font-semibold">Почему нельзя назвать units зеркальными нейронами</h3><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Для такого вывода нужно знать, какие реальные клетки получают зрительный сигнал и какие моторные клетки управляют соответствующим движением. FlyVis, FlyWire/Shiu и FlyGym существуют отдельно, но проверенного соответствия между их клетками для этих действий пока нет.</p><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Поэтому результат формулируется осторожно: искусственная система связывает наблюдение с последующим повтором. Она пока не устанавливает, какие нейроны делают это у настоящей дрозофилы.</p></div></div>
        <div className="mt-6 border-y py-5"><h3 className="text-[14px] font-semibold">Как коротко объяснить эту работу</h3><p className="mt-3 max-w-5xl text-[13px] leading-7">«Я построил вычислительный прототип с двумя виртуальными мухами. Первая показывает движение, программа преобразует изображения в искусственные числовые признаки и внутреннее состояние, а затем управляет второй мухой без новых кадров. Я проверил работу на новых движениях, ракурсах, начальных состояниях и цифровых отключениях частей модели. Это функциональный аналог наблюдения и повтора, но96 каналов модели не являются96 реальными нейронами, и биологические зеркальные нейроны этим опытом не обнаружены».</p></div>
      </section>

      <section id="limits" className="scroll-mt-20 border-t py-8"><div className="grid gap-6 md:grid-cols-2"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Допустимый вывод</div><h2 className="mt-2 text-xl font-semibold">Функциональный synthetic mirror-like механизм</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Наблюдение связано с внутренним состоянием, задержкой, автономным воспроизведением, causal digital lesions и actuator surrogate. Итоговая policy прошла frozen replication.</p></div><div className="border-l pl-6"><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Недопустимый вывод</div><h2 className="mt-2 text-xl font-semibold">Не доказательство биологических зеркальных нейронов</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Нет reviewed end-to-end neural mapping, natural vision, muscle dynamics, collision forces и interventions у живых мух. Browser demo также не изменяет этот статус.</p></div></div></section>

      <section id="next" className="scroll-mt-20 border-t py-8"><div className="grid gap-7 lg:grid-cols-[.72fr_1.28fr]"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Следующий roadmap</div><h2 className="mt-2 text-2xl font-semibold">Какие утверждения ещё предстоит проверить</h2><p className="mt-3 text-[12px] leading-6 text-muted-foreground">Это цели будущих исследований, а не выводы текущих серий. Для них нужны reviewed mappings, новый preregistration и biological recordings/interventions.</p></div><ul className="border-t text-[12px] text-muted-foreground"><li className="border-b py-3">Обнаружены ли у дрозофилы биологические зеркальные нейроны.</li><li className="border-b py-3">Можно ли после независимой проверки считать конкретные FlyWire IDs зеркальными нейронами.</li><li className="border-b py-3">Воспроизводят ли interventions у живого животного причинные эффекты, найденные synthetic lesions.</li><li className="border-b py-3">Существует ли проверенная естественная цепь FlyVis-like vision → FlyWire/Shiu pathway → моторные нейроны → мышцы.</li><li className="border-b py-3">Переносятся ли результаты six-joint surrogate на реальное тело, мышцы и контактные силы.</li></ul></div></section>

      <section id="files" className="scroll-mt-20 border-t py-8"><div className="flex flex-wrap justify-between gap-5"><div><div className="font-mono text-[10px] uppercase tracking-[.15em] text-muted-foreground">Воспроизводимость</div><h2 className="mt-2 text-xl font-semibold">Отчёты и проверяемые артефакты находятся в репозитории</h2><p className="mt-3 max-w-3xl text-[12px] leading-6 text-muted-foreground">Для89E сохранены trial-level extract, independent verifier и report. Для90 сохранены source audit, machine-readable decision и gate runner. На этой странице нет сервера: заданные движения остаются в браузере и никуда не отправляются.</p></div><a className={button} href="https://github.com/Bergaff/fly" target="_blank" rel="noreferrer">Открыть репозиторий</a></div></section>
    </main>
    <footer className="border-t px-4 py-5 text-center text-[10px] text-muted-foreground"><div>Synthetic research demonstrator · no biological diagnosis or animal claim · данные ввода не передаются</div><div className="mt-2 flex justify-center gap-3"><button className="underline" onClick={() => setLegal("terms")}>Условия использования</button><button className="underline" onClick={() => setLegal("privacy")}>Политика конфиденциальности</button></div></footer>
    <LegalDialog kind={legal} onClose={() => setLegal(null)} />
  </div>;
}
