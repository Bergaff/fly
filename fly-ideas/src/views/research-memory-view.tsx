import { useEffect, useState } from "react";
import type { ResearchMemoryState } from "@/data/research-memory";
import { fly, type DataFileLinks, type Paths } from "@/lib/bridge";

const historical = [
  { label: "Папка программы, сообщена пользователем", path: String.raw`E:\ass\fly\fly-ideas`, note: "Исторический путь, текущее наличие не проверено." },
  { label: "Запуск программы", path: String.raw`E:\ass\fly\fly-ideas\START.bat`, note: "Путь на компьютере пользователя из переписки; наличие не проверено." },
  { label: "Проверенная копия кода частотного расчёта", path: String.raw`E:\ass\fly\fly-ideas\workspace\scripts\ideas\i-lesions\.shiu-frequency-check-v630\37_shiu_frequency_check.py`, note: "Путь из сообщения об остановке; файл не заменяет результаты." },
  { label: "Общий набор, сообщённый путь", path: String.raw`E:\ass\fly\fly-ideas\workspace\data\shiu-v630-shared\Study_20261102_135659_26e34eaf`, note: "Папка набора на компьютере пользователя; наличие здесь не проверено." },
  { label: "Полный отчёт лезий 510/510, сообщённый путь", path: String.raw`E:\ass\fly\fly-ideas\workspace\data\shiu-v630-shared\Study_20261102_135659_26e34eaf\05_reports\all_20261103_105142_9c5315e1`, note: "Исторический путь к отчёту; наличие здесь не проверено." },
];
const derived = [
  { label: "Частотная база", relative: "shiu-v630-frequency-check/<Study_ID>/frequencies.sqlite3" },
  { label: "Индивидуальность, пилот", relative: "shiu-v630-individuality/<Study_ID>/pilot.sqlite3" },
  { label: "Индивидуальность, продолжение", relative: "shiu-v630-individuality/<Study_ID>/extension_10seeds_v1/extension.sqlite3" },
  { label: "Индивидуальность, проверка", relative: "shiu-v630-individuality/<Study_ID>/holdout_10seeds_v1/holdout.sqlite3" },
];

export function ResearchMemoryView({ memory }: { memory?: ResearchMemoryState }) {
  const [paths, setPaths] = useState<Paths | null>(null);
  const [links, setLinks] = useState<DataFileLinks | null>(null);
  const [shared, setShared] = useState<{ id: string; label: string; path: string }[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!fly) return;
    let alive = true;
    Promise.allSettled([fly.getPaths(), fly.getDataFileLinks(), fly.listSharedStudies()]).then(([p, l, s]) => {
      if (!alive) return;
      if (p.status === "fulfilled") setPaths(p.value);
      if (l.status === "fulfilled") setLinks(l.value);
      if (s.status === "fulfilled") setShared(s.value.studies);
      if ([p, l, s].some((result) => result.status === "rejected")) setError("часть источников путей недоступна");
    });
    return () => { alive = false; };
  }, []);
  const records = (memory?.entries ?? []).filter((entry) => entry && typeof entry.title === "string" && Array.isArray(entry.files));
  const matchingStudy = shared.find((item) => item.id === "Study_20261102_135659_26e34eaf");
  const derivedPath = (relative: string) => {
    if (!paths) return relative;
    const sep = paths.data.includes("\\") ? "\\" : "/";
    const prefix = paths.data.replace(/[\\/]+$/, "");
    const actual = relative.replace("<Study_ID>", matchingStudy?.id ?? "<Study_ID>");
    return prefix + sep + actual.replace(/\//g, sep);
  };
  return <div className="h-full min-h-0 overflow-y-auto p-3 text-[12px]">
    <div className="mx-auto max-w-5xl">
      <h1 className="text-[15px] font-semibold">Память исследований и пути</h1>
      <p className="mt-1 text-muted-foreground">Архив результатов по переписке и проверенным таблицам. Он добавляется автоматически и хранится в состоянии приложения; не заменяет исходные базы. Новые расчёты сюда автоматически не попадают.</p>
      <div className="mt-3 border-t">
        {records.map((entry) => <details key={entry.id} className="border-b" open>
          <summary className="cursor-pointer py-2"><span className="font-medium">{entry.title}</span><span className="ml-2 font-mono text-[10px] text-muted-foreground">{entry.status}</span></summary>
          <div className="pb-3 pl-2">
            <div className="text-[10px] uppercase text-muted-foreground">Источник</div><p className="mt-0.5 whitespace-pre-wrap break-words">{entry.source}</p>
            <div className="mt-2 text-[10px] uppercase text-muted-foreground">Результат</div><p className="mt-0.5 whitespace-pre-wrap break-words font-mono text-[11px]">{entry.results}</p>
            <div className="mt-2 text-[10px] uppercase text-muted-foreground">Ограничения</div><p className="mt-0.5 whitespace-pre-wrap break-words">{entry.limitations}</p>
            <div className="mt-2 text-[10px] uppercase text-muted-foreground">Файлы и относительные пути, доступность не проверена</div>
            <ul className="mt-0.5 font-mono text-[10px]">{entry.files.map((file) => <li key={file} className="break-all">{file}</li>)}</ul>
          </div>
        </details>)}
      </div>
      <section className="mt-4 border-t">
        <h2 className="py-2 font-medium">Пути этого компьютера</h2>
        {!fly && <p className="text-muted-foreground">В браузере пути компьютера недоступны; откройте приложение через START.bat.</p>}
        {error && <p className="text-muted-foreground">Не удалось получить пути: {error}</p>}
        {paths && <div className="space-y-2 border-b pb-2">
          {[['Рабочая папка', paths.workspace], ['Текущая папка данных', paths.data], ['Код', paths.scripts], ['Прогоны', paths.runs], ['Шаблоны', paths.templates]].map(([label, value]) => <div key={label}><span>{label}</span><div className="break-all font-mono text-[10px]">{value}</div></div>)}
        </div>}
        {links && <div className="space-y-2 border-b py-2">
          {([['shiu_connections','Авторские связи Shiu v630'], ['shiu_neurons','Авторский список нейронов Shiu v630'], ['connections','Подключённая таблица связей'], ['annotations','Аннотации'], ['cell_types','Типы клеток'], ['neurotransmitters','Нейромедиаторы']] as const).map(([key,label]) => <div key={key}><span>{label}: {links[key].path ? links[key].available ? 'файл доступен' : 'файл недоступен' : 'не выбран'}</span>{links[key].path && <div className="break-all font-mono text-[10px]">{links[key].path}</div>}</div>)}
        </div>}
        {shared.length > 0 && <div className="space-y-2 border-b py-2"><div>Общие наборы, найденные приложением</div>{shared.map((item) => <div key={item.id}><span>{item.label}</span><div className="break-all font-mono text-[10px]">{item.path}</div></div>)}</div>}
        <div className="space-y-2 border-b py-2"><p>Ожидаемые пути в текущей папке данных. Если нужный набор не найден, замените &lt;Study_ID&gt; его именем; наличие файлов не проверено.</p>{derived.map((item) => <div key={item.label}><span>{item.label}</span><div className="break-all font-mono text-[10px]">{derivedPath(item.relative)}</div></div>)}</div>
        <div className="space-y-2 py-2"><div>Исторические пути из переписки</div>{historical.map((item) => <div key={item.label}><span>{item.label}</span><div className="break-all font-mono text-[10px]">{item.path}</div><div className="text-[10px] text-muted-foreground">{item.note}</div></div>)}<p>Путь к папке Colab/Google Drive и актуальный ход Colab неизвестны. Имена файлов <span className="font-mono">frequency_trials.csv</span> и отчётов зависят от выбранного прогона.</p></div>
      </section>
    </div>
  </div>;
}
