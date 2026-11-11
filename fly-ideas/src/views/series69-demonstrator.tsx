import { useEffect, useMemo, useState } from "react";
import { fly } from "@/lib/bridge";
import { parseSeries69Demo, type Series69Demo } from "@/lib/series69-demo";
import { ZERO, type Angles } from "@/lib/wing-trajectory";
import { WingScene } from "@/views/wing-scene";

const button = "cursor-pointer border bg-background px-2.5 py-1.5 text-[12px] disabled:cursor-not-allowed disabled:opacity-40";
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));
function Cells({ values, title }: { values: number[]; title: string }) {
  const max = Math.max(.001, ...values.map(Math.abs));
  return <div className="min-w-0"><div className="mb-1 flex justify-between text-[10px]"><span>{title}</span><span className="font-mono text-muted-foreground">max |a| {max.toFixed(3)}</span></div><div className="grid grid-cols-12 gap-px border bg-border p-px" aria-label={title}>{values.map((v, i) => { const q = clamp(Math.abs(v) / max, 0, 1); const warm = v >= 0; return <span key={i} title={`${i}: ${v.toFixed(5)}`} className="aspect-square" style={{ backgroundColor: warm ? `rgb(${Math.round(225-65*q)},${Math.round(218-120*q)},${Math.round(190-125*q)})` : `rgb(${Math.round(190-105*q)},${Math.round(210-80*q)},${Math.round(220-45*q)})` }} />; })}</div></div>;
}
function StateStrip({ values, title }: { values: number[]; title: string }) {
  const max = Math.max(.001, ...values.map(Math.abs));
  return <div><div className="mb-1 text-[10px]">{title}</div><div className="flex h-12 items-end gap-px border px-1 pt-1">{values.map((v, i) => <span key={i} title={`${i}: ${v.toFixed(5)}`} className="min-w-0 flex-1 bg-foreground/70" style={{ height: `${8 + 88 * Math.abs(v) / max}%` }} />)}</div></div>;
}

export function Series69Demonstrator() {
  const [demo, setDemo] = useState<Series69Demo | null>(null);
  const [model, setModel] = useState<"rich" | "compact">("rich");
  const [clock, setClock] = useState(0); const [playing, setPlaying] = useState(false); const [message, setMessage] = useState("");
  const observation = demo?.rich.trajectory.duration_s || 2; const delay = demo?.metrics.delay_s || .5; const total = observation * 2 + delay;
  useEffect(() => { if (!playing) return; let id=0,last:number|null=null; const tick=(now:number)=>{ if(last!==null)setClock(v=>Math.min(total,v+(now-last!)/1000));last=now;id=requestAnimationFrame(tick);};id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id); }, [playing,total]);
  useEffect(() => { if (clock >= total && playing) setPlaying(false); }, [clock,playing,total]);
  const phase = clock < observation ? "observation" : clock < observation + delay ? "delay" : "replay";
  const local = phase === "replay" ? clock - observation - delay : Math.min(clock, observation);
  const index = demo ? clamp(Math.floor(local * 25 + 1e-7), 0, demo.rich.samples.length - 1) : 0;
  const selected = demo?.[model]; const teacher = demo?.rich.samples[clamp(Math.floor(Math.min(clock,observation)*25),0,(demo?.rich.samples.length||1)-1)]?.teacher || ZERO;
  const observer: Angles = phase === "replay" && selected ? selected.samples[index].prediction : ZERO;
  const activityIndex = demo ? clamp(Math.floor(Math.min(clock,observation)*25),0,demo.activity.times.length-1) : 0;
  const values = demo?.activity; const metrics = demo?.metrics.conditions.normal;
  const load = async (choose = false) => { try { if(!fly){setMessage("Открытие папки доступно в Windows-приложении Fly Ideas.");return;} const raw=choose ? await fly.chooseSeries69Demo() : await fly.loadSeries69Demo(); if(!raw)return; const parsed=parseSeries69Demo(raw);setDemo(parsed);setClock(0);setPlaying(false);setMessage(`Загружен holdout 1 серии 69: ${parsed.folder}. Путь запомнен; исходные файлы не изменены.`); } catch(e){setMessage(`Не удалось открыть демонстрацию: ${String((e as Error).message||e)}`);} };
  const openResultFolder = () => { if (fly && demo) void fly.openPath(demo.folder); };
  const phaseLabel = phase === "observation" ? "Наблюдение: первая муха движется, состояние формируется" : phase === "delay" ? "Задержка: первая муха скрыта, новых кадров нет" : `Автономный replay: ${model}`;
  const errorDeg = useMemo(() => { if(!demo || phase!=="replay")return 0; const s=selected!.samples[index]; return Math.sqrt(s.teacher.reduce((q,v,i)=>q+(s.prediction[i]-v)**2,0)/6); },[demo,index,phase,selected]);
  return <section className="border-b pb-5">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3"><div><div className="font-mono text-[10px] uppercase tracking-[.14em] text-muted-foreground">серия 69 / наблюдение → состояние → задержка → replay</div><h2 className="mt-1 text-lg font-semibold">Видимый демонстратор результата</h2><p className="mt-1 max-w-4xl text-[12px] text-muted-foreground">Открывает только готовые playback, activity, state и metrics. Ничего не переобучает и не выдаёт 96 искусственных units за нейроны настоящей мухи.</p></div><div className="flex flex-wrap gap-2"><button className={button} onClick={() => void load()}>Открыть result серии 69</button><button className={button} onClick={() => void load(true)}>Выбрать другую папку</button>{demo && fly && <button className={button} onClick={openResultFolder}>Открыть папку результата</button>}</div></div>
    {message && <p role="status" className="border-b py-2 text-[12px]">{message}</p>}
    {!demo ? <div className="py-4 text-[12px] text-muted-foreground">Кнопка сначала использует запомненный путь, затем ищет последний полный запуск в <span className="font-mono">workspace\runs\ideas\i-observational\matched-encoder-ablation</span>. Диалог появится только если результат не найден. После загрузки будут показаны обе модели, активность encoder и неизменное состояние во время задержки.</div> : <>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-b pb-3"><button className={button} onClick={()=>{if(clock>=total)setClock(0);setPlaying(v=>!v);}}>{playing?"Пауза":"Воспроизвести"}</button><button className={button} onClick={()=>{setPlaying(false);setClock(0);}}>В начало</button><button className={button} aria-pressed={model==="rich"} onClick={()=>setModel("rich")}>Rich, 96 units</button><button className={button} aria-pressed={model==="compact"} onClick={()=>setModel("compact")}>Compact, 24 units</button><span className="ml-auto font-mono text-[11px]">{clock.toFixed(2)} / {total.toFixed(2)} с</span></div>
      <div className="grid gap-4 pt-3 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,.7fr)]"><div><div className="mb-2 flex justify-between text-[11px]"><strong>{phaseLabel}</strong><span className="font-mono text-muted-foreground">кадр {index}</span></div><WingScene teacher={teacher} observer={observer} teacherVisible={phase==="observation"} /><input aria-label="Время демонстрации" type="range" min="0" max={total} step="0.04" value={clock} onChange={e=>{setPlaying(false);setClock(Number(e.target.value));}} className="mt-2 w-full accent-foreground" /><div className="grid grid-cols-3 text-center font-mono text-[10px] text-muted-foreground"><span>показ 0–{observation.toFixed(1)} с</span><span>без кадров {delay.toFixed(1)} с</span><span>replay {observation.toFixed(1)} с</span></div></div>
        <div className="space-y-3"><div className="border-b pb-2 text-[11px]"><div className="flex justify-between"><span>Normal RMSE rich</span><strong className="font-mono">{metrics?.rich.rmse_rad.toFixed(6)} рад</strong></div><div className="flex justify-between"><span>Normal RMSE compact</span><strong className="font-mono">{metrics?.compact.rmse_rad.toFixed(6)} рад</strong></div><div className="mt-1 flex justify-between"><span>Текущая ошибка replay</span><strong className="font-mono">{errorDeg.toFixed(2)}°</strong></div></div>
          {phase==="observation" && values ? <><Cells title="Rich level: 96 искусственных units" values={values.richLevel[activityIndex]} /><Cells title="Rich delta: изменение между кадрами" values={values.richDelta[activityIndex]} /><Cells title="Compact: 24 искусственных units" values={values.compact[activityIndex]} /></> : <StateStrip title={`${model}: 72 коэффициента состояния; updates during delay = 0`} values={demo.states[model]} />}
          <p className="border-t pt-2 text-[10px] text-muted-foreground">Во время replay входом служат только сохранённое 72-компонентное состояние и фаза. Teacher показан лишь как численная проверка ошибки; первая муха в сцене скрыта.</p></div></div>
    </>}
  </section>;
}
