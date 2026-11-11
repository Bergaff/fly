import { useEffect, useRef, useState } from "react";
import { fly } from "@/lib/bridge";
import { initialTrajectory, interpolate, parseResult, parseTrajectory, randomAngles, ZERO, type Angles, type Trajectory, type WingResult } from "@/lib/wing-trajectory";
import { WingScene } from "@/views/wing-scene";

const labels = ["X подъём", "Y наклон", "Z поворот", "X подъём", "Y наклон", "Z поворот"];
const button = "cursor-pointer border bg-background px-2.5 py-1.5 text-[12px] disabled:cursor-not-allowed disabled:opacity-40";
const field = "border bg-background px-1.5 py-1 font-mono text-[12px]";
const storeKey = "fly-wing-studio-v1";
function stored(): Trajectory { try { const s = localStorage.getItem(storeKey); return s ? parseTrajectory(JSON.parse(s)) : initialTrajectory; } catch { return initialTrajectory; } }

export function WingStudioView() {
  const [trajectory, setTrajectory] = useState<Trajectory>(stored);
  const [frame, setFrame] = useState(0); const [time, setTime] = useState(0); const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(.5); const [result, setResult] = useState<WingResult | null>(null); const [phase, setPhase] = useState<"observation" | "replay">("observation");
  const [message, setMessage] = useState(""); const [durationInput, setDurationInput] = useState(String(trajectory.duration_s));
  const browserFile = useRef<HTMLInputElement>(null); const fileKind = useRef<"trajectory" | "result">("trajectory");
  useEffect(() => { try { localStorage.setItem(storeKey, JSON.stringify(trajectory)); } catch { setMessage("Автосохранение недоступно. Сохраните JSON в файл."); } }, [trajectory]);
  useEffect(() => {
    if (!playing) return;
    let id = 0, last: number | null = null;
    const step = (now: number) => { if (last !== null) setTime(t => (t + (now - last!) / 1000 * speed) % trajectory.duration_s); last = now; id = requestAnimationFrame(step); };
    id = requestAnimationFrame(step); return () => cancelAnimationFrame(id);
  }, [playing, speed, trajectory.duration_s]);
  const change = (t: Trajectory) => { setTrajectory(t); setResult(null); setPhase("observation"); setPlaying(false); };
  const selected = trajectory.keyframes[frame] || trajectory.keyframes[0];
  const liveTeacher = interpolate(time, trajectory);
  const sampleIndex = result ? Math.min(result.samples.length - 1, Math.floor(time * 25 + 1e-7)) : 0;
  const sample = result?.samples[sampleIndex];
  const teacher = result && sample ? sample.teacher_deg : liveTeacher;
  const observer = sample?.prediction_deg || ZERO;
  const teacherVisible = !result || phase === "observation";
  const setAngle = (i: number, value: number) => {
    if (!Number.isFinite(value)) return;
    const frames = trajectory.keyframes.map((k, n) => n === frame ? { ...k, angles_deg: k.angles_deg.map((v, a) => a === i ? Math.max(-60, Math.min(60, value)) : v) as Angles } : k);
    change({ ...trajectory, keyframes: frames }); setTime(selected.t);
  };
  const updateDuration = () => {
    const n = Number(durationInput.replace(",", "."));
    if (!Number.isFinite(n) || n < .52 || n > 10 || Math.abs(n * 25 - Math.round(n * 25)) > 1e-7) { setMessage("Длительность от 0,52 до 10 с, с шагом 0,04 с."); setDurationInput(String(trajectory.duration_s)); return; }
    const frames = trajectory.keyframes.map((k, i) => ({ ...k, t: i === trajectory.keyframes.length - 1 ? n : k.t * n / trajectory.duration_s }));
    change({ ...trajectory, duration_s: n, keyframes: frames }); setTime(0); setMessage("Времена ключевых кадров пропорционально изменены.");
  };
  const insert = () => {
    const t = Math.round(time * 25) / 25;
    if (trajectory.keyframes.length >= 200 || trajectory.keyframes.some(k => Math.abs(k.t - t) < 1e-6)) { setMessage("В этой точке уже есть кадр или достигнут предел 200 кадров."); return; }
    const frames = [...trajectory.keyframes, { t, angles_deg: interpolate(t, trajectory) }].sort((a,b) => a.t - b.t);
    change({ ...trajectory, keyframes: frames }); setFrame(frames.findIndex(k => k.t === t)); setTime(t); setMessage("Кадр добавлен. Задайте углы ниже.");
  };
  const remove = () => { if (frame === 0 || frame === trajectory.keyframes.length - 1) return; change({ ...trajectory, keyframes: trajectory.keyframes.filter((_, i) => i !== frame) }); setFrame(0); setTime(0); };
  const advanceRandom = () => {
    if (time >= trajectory.duration_s - 1e-9) { setMessage("Достигнут конец траектории. Нажмите «В начало», чтобы начать новый проход."); return; }
    const nextTime = Math.min(trajectory.duration_s, (Math.floor((time + 1e-9) / .5) + 1) * .5);
    const keepOnGrid = (t: number) => Math.abs(t / .5 - Math.round(t / .5)) < 1e-7 || Math.abs(t - trajectory.duration_s) < 1e-7;
    const kept = trajectory.keyframes.filter(k => keepOnGrid(k.t) && Math.abs(k.t - nextTime) > 1e-7);
    const frames = [...kept, { t: nextTime, angles_deg: randomAngles() }].sort((a,b) => a.t - b.t);
    change({ ...trajectory, keyframes: frames }); setFrame(frames.findIndex(k => Math.abs(k.t - nextTime) < 1e-7)); setTime(nextTime);
    setMessage(`Случайные углы заданы в ${nextTime.toFixed(2)} с. Следующее нажатие сдвинет точку ещё на 0,5 с.`);
  };
  const save = async () => {
    try {
      const text = JSON.stringify(trajectory, null, 2) + "\n";
      if (fly) { const p = await fly.saveFile({ defaultName: "wing-trajectory.json", content: text, filters: [{ name: "JSON", extensions: ["json"] }], kind: "exports" }); if (p) setMessage(`Траектория сохранена: ${p}`); }
      else { const url = URL.createObjectURL(new Blob([text], { type: "application/json" })); const a = document.createElement("a"); a.href = url; a.download = "wing-trajectory.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage("Траектория сохранена через браузер."); }
    } catch (e) { setMessage(`Не удалось сохранить: ${String(e)}`); }
  };
  const applyFile = (content: string, kind: "trajectory" | "result") => {
    try {
      const value: unknown = JSON.parse(content.replace(/^\uFEFF/, ""));
      if (kind === "trajectory") { const t = parseTrajectory(value); setTrajectory(t); setDurationInput(String(t.duration_s)); setResult(null); setMessage("Траектория загружена."); }
      else { const r = parseResult(value); setTrajectory(r.trajectory); setDurationInput(String(r.duration_s)); setResult(r); setMessage("Загружен рассчитанный результат. При изменении траектории он будет закрыт."); }
      setTime(0); setFrame(0); setPhase("observation"); setPlaying(false);
    } catch (e) { setMessage(`Не удалось открыть: ${String((e as Error).message || e)}`); }
  };
  const open = async (kind: "trajectory" | "result") => {
    if (!confirm("Загрузка заменит текущую траекторию в редакторе. Сохраните её в JSON заранее. Продолжить?")) return;
    try {
      if (fly) { const f = await fly.openFile({ filters: [{ name: "JSON", extensions: ["json"] }], kind: "exports" }); if (f) applyFile(f.content, kind); }
      else { fileKind.current = kind; browserFile.current?.click(); }
    } catch (e) { setMessage(`Не удалось открыть: ${String(e)}`); }
  };
  return <div className="h-full overflow-y-auto"><div className="mx-auto max-w-[1600px] px-4 py-4 md:px-6">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3">
      <div><div className="font-mono text-[10px] uppercase tracking-[.14em] text-muted-foreground">кинематика / 6 осей / редактор 01</div><h1 className="mt-1 text-xl font-semibold">Движение крыльев</h1><p className="mt-1 max-w-3xl text-[12px] text-muted-foreground">Создайте показ для первой мухи. Трёхмерная муха здесь схематичная, не биомеханическая реконструкция; в расчёте используются упрощённые эллипсоиды.</p></div>
      <div className="flex flex-wrap gap-2"><button className={button} onClick={() => void open("trajectory")}>Открыть траекторию</button><button className={button} onClick={() => void save()}>Сохранить JSON</button><button className={button} onClick={() => void open("result")}>Открыть playback.json</button></div>
      <input ref={browserFile} type="file" accept=".json,application/json" className="hidden" onChange={e => { const file=e.target.files?.[0]; if (file) void file.text().then(s => applyFile(s,fileKind.current)).catch(err => setMessage(String(err))); e.currentTarget.value=""; }} />
    </div>
    {message && <div role="status" className="border-b py-2 text-[12px]">{message}</div>}
    <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
      <section className="min-w-0">
        <div className="flex items-baseline justify-between border-b pb-2"><h2 className="text-[13px] font-semibold">Ключевые кадры</h2><span className="font-mono text-[10px] text-muted-foreground">{trajectory.keyframes.length} / 200</span></div>
        <p className="py-2 text-[11px] text-muted-foreground">Выберите кадр, задайте углы двух крыльев. Между кадрами движение линейное. Время точки добавляется ползунком справа.</p>
        <div className="border-b pb-2"><button className={button} onClick={advanceRandom}>Случайное движение, шаг 0,5 с</button><p className="mt-1 text-[10px] text-muted-foreground">Каждое нажатие сдвигает шкалу вправо к следующей точке 0,5 с и случайно меняет все шесть ползунков от −45° до +45°. В конце нажмите «В начало» для нового прохода.</p></div>
        <div className="flex max-h-36 flex-wrap content-start gap-1 overflow-auto border-b py-2">{trajectory.keyframes.map((k,i) => <button key={i} type="button" className={`${button} font-mono ${i === frame ? "bg-secondary" : ""}`} aria-pressed={i === frame} onClick={() => { setFrame(i); setTime(k.t); setPlaying(false); }}>{k.t.toFixed(2)} с</button>)}</div>
        <div className="flex flex-wrap items-center gap-2 border-b py-2"><button className={button} onClick={insert}>Добавить на шкале</button><button className={button} disabled={frame===0 || frame===trajectory.keyframes.length-1} onClick={remove}>Удалить кадр</button></div>
        <div className="flex items-center gap-2 border-b py-2 text-[12px]"><label htmlFor="wing-duration">Длительность, с</label><input id="wing-duration" className={`${field} w-20`} inputMode="decimal" value={durationInput} onChange={e => setDurationInput(e.target.value)} /><button className={button} onClick={updateDuration}>Применить</button></div>
        <div className="pt-3 text-[11px] text-muted-foreground">Кадр <span className="font-mono text-foreground">{selected.t.toFixed(2)} с</span> · оси локальные X / Y / Z, градусы; правая и левая стороны задаются независимо.</div>
        {[0,1].map(side => <div key={side} className="mt-3"><div className="border-b pb-1 text-[12px] font-semibold">{side === 0 ? "Левое крыло" : "Правое крыло"}</div>{[0,1,2].map(j => { const i=side*3+j; return <div key={i} className="grid grid-cols-[90px_minmax(50px,1fr)_58px] items-center gap-2 border-b py-2"><label htmlFor={`angle-${i}`} className="text-[11px]">{labels[i]}</label><input id={`angle-${i}`} type="range" min="-60" max="60" step="1" value={selected.angles_deg[i]} onChange={e => setAngle(i,Number(e.target.value))} className="w-full accent-foreground"/><input aria-label={`${side === 0 ? "Левое" : "Правое"} ${labels[i]}, градусы`} type="number" min="-60" max="60" step="1" className={`${field} w-full`} value={Number(selected.angles_deg[i].toFixed(2))} onChange={e => { if (e.target.value !== "") setAngle(i,Number(e.target.value)); }} /></div>; })}</div>)}
      </section>
      <section className="min-w-0">
        <div className="flex flex-wrap justify-between gap-2 border-b pb-2 text-[11px]"><span><strong>01</strong> демонстратор справа · <strong>02</strong> наблюдатель слева</span><span className="text-muted-foreground">Мышь: поворот и масштаб сцены</span></div>
        <div className="mt-2"><WingScene teacher={teacher} observer={observer} teacherVisible={teacherVisible} /></div>
        <div className="flex flex-wrap items-center gap-2 border-b py-3"><button className={button} onClick={() => setPlaying(v => !v)}>{playing ? "Пауза" : "Воспроизвести"}</button><button className={button} onClick={() => { setPlaying(false); setTime(0); }}>В начало</button><label htmlFor="wing-speed" className="text-[11px]">Скорость</label><select id="wing-speed" value={speed} onChange={e => setSpeed(Number(e.target.value))} className={field}><option value="0.25">0,25×</option><option value="0.5">0,5×</option><option value="1">1×</option></select><span className="ml-auto font-mono text-[12px]">{time.toFixed(2)} / {trajectory.duration_s.toFixed(2)} с</span></div>
        <label htmlFor="wing-time" className="sr-only">Время просмотра</label><input id="wing-time" type="range" min="0" max={trajectory.duration_s} step="0.04" value={time} onChange={e => { setPlaying(false); setTime(Number(e.target.value)); }} className="mt-3 w-full accent-foreground" />
        <div className="flex justify-between font-mono text-[10px] text-muted-foreground"><span>0.00</span><span>{trajectory.duration_s.toFixed(2)} с</span></div>
        <div className="mt-4 border-t pt-3"><div className="flex flex-wrap items-center gap-2"><strong className="text-[13px]">Вторая муха</strong>{result ? <><button className={button} aria-pressed={phase === "observation"} onClick={() => { setPhase("observation"); setTime(0); setPlaying(false); }}>Во время показа</button><button className={button} aria-pressed={phase === "replay"} onClick={() => { setPhase("replay"); setTime(0); setPlaying(false); }}>Повтор после показа</button></> : <span className="font-mono text-[11px] text-muted-foreground">ожидает результат</span>}</div>
          {result ? <><p className="mt-2 text-[12px]">{phase === "observation" ? "Первая показывает, вторая воспроизводит рассчитанные для каждого кадра углы. Первые 2 кадра ещё нет прогноза." : "Первая скрыта. Вторая проигрывает сохранённые прогнозы после показа. Это память записи, а не автономная генерация."}</p><p className="mt-2 font-mono text-[11px]">Ваша траектория: RMSE модель {result.user_metrics.new.rmse_rad.toFixed(4)} рад / неподвижная {result.user_metrics.zero.rmse_rad.toFixed(4)} рад.<br/>{result.holdout_label || "Другие синтетические движения"}: {result.holdout_metrics.new.rmse_rad.toFixed(4)} / {result.holdout_metrics.zero.rmse_rad.toFixed(4)} рад.</p></> : <p className="mt-2 text-[12px] text-muted-foreground">Пока движения второй мухи не рассчитаны: она неподвижна. Сохраните JSON, запустите <span className="font-mono">experiments\RUN-WING-STUDIO-PILOT.bat</span>, выберите траекторию и затем откройте созданный <span className="font-mono">playback.json</span>.</p>}
          <p className="mt-3 border-t pt-2 text-[11px] text-muted-foreground">Чтобы обучить модель на своих движениях, сохраните не менее трёх разных JSON. Двойным щелчком запустите <span className="font-mono">experiments\RUN-USER-WING-LEARNING.bat</span>: сначала выберите минимум два файла для обучения, затем другие для проверки. Откройте <span className="font-mono">playback.json</span> из папки проверочной траектории. Это короткая проба, не серия на 4–8 часов.</p>
          <p className="mt-2 text-[11px] text-muted-foreground">Глаза модели: в папке результата <span className="font-mono">observer_vision.gif</span> показывает увеличенную картинку двух искусственных камер, а в новой пробе файл <span className="font-mono">observer_model_input.gif</span> показывает блоки яркости до нормировки. Точные кадры, а в новой пробе и вход модели, сохранены в NPZ. Это не зрение живой мухи.</p>
          <p className="mt-2 text-[11px] text-muted-foreground">Проба обучает линейную модель по изображениям и известным углам. Проверочная траектория не участвует в обучении. Вращения могут быть зрительно неоднозначны; это не исследование реального мозга и не доказательство зеркальных нейронов.</p>
        </div>
      </section>
    </div>
  </div></div>;
}
