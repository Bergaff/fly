import { useEffect, useState } from "react";
import type { AppState } from "@/data/types";
import { fly, type SyncInfo, type SyncProgress, type SyncUi } from "@/lib/bridge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

function capture(state: AppState): SyncUi {
  const chats: Record<string, string> = {};
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith("fly-ideas:chat:")) chats[key] = localStorage.getItem(key) ?? "[]";
  }
  return { state, chats, rates: localStorage.getItem("fly-ideas:api-rates") };
}

export function SyncDialog({ open, onClose, state, dirty }: { open: boolean; onClose: () => void; state: AppState; dirty: boolean }) {
  const [info, setInfo] = useState<SyncInfo | null>(null);
  const [includeData, setIncludeData] = useState(false);
  const [source, setSource] = useState<"shared" | "backup">("shared");
  const [id, setId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const refresh = async () => { if (fly) setInfo(await fly.syncInfo()); };
  useEffect(() => {
    if (!open || !fly) return;
    void refresh().catch((e) => setMessage(String(e)));
    return fly.onSyncProgress(setProgress);
  }, [open]);
  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setMessage(""); setProgress(null);
    try { await fn(); } catch (e) { setMessage(String(e)); }
    finally { setBusy(false); }
  };
  const upload = () => void run(async () => {
    if (!fly) return;
    const result = await fly.syncUpload(capture(state), includeData);
    setMessage(`Снимок записан: ${result.id}. Дождитесь окончания загрузки в приложении Google Диска перед переходом на другой компьютер.`);
    await refresh();
  });
  const restore = () => {
    if (!fly || !id || !confirm("Заменить локальные идеи, историю чатов, учёт API и совпадающие файлы выбранным снимком? Перед заменой будет создана локальная резервная копия. Объединения изменений нет.")) return;
    void run(async () => {
      if (!fly) return;
      const result = await fly.syncRestore(source, id, capture(state));
      try {
        sessionStorage.setItem("fly-ideas:sync-applying", "1");
        const keys: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key?.startsWith("fly-ideas:chat:")) keys.push(key);
        }
        keys.forEach((key) => localStorage.removeItem(key));
        for (const [key, value] of Object.entries(result.ui.chats)) localStorage.setItem(key, value);
        if (result.ui.rates === null) localStorage.removeItem("fly-ideas:api-rates");
        else localStorage.setItem("fly-ideas:api-rates", result.ui.rates);
        localStorage.setItem("fly-ideas:state:v1", JSON.stringify(result.ui.state));
        await fly.syncFinish(true);
      } catch (e) {
        alert(`Не удалось применить состояние окна. Локальная резервная копия: ${result.backup.path}. После перезапуска выберите её в списке резервных копий. ${String(e)}`);
        await fly.syncFinish(true).catch(() => window.location.reload());
      }
    });
  };
  const snapshots = source === "shared" ? info?.shared : info?.backups;
  return <Dialog open={open} onOpenChange={(next) => { if (!next && !busy) onClose(); }}>
    <DialogContent className="sm:max-w-2xl" onEscapeKeyDown={(e) => { if (busy) e.preventDefault(); }} onPointerDownOutside={(e) => { if (busy) e.preventDefault(); }}>
      <DialogHeader><DialogTitle>Синхронизация через Google Диск</DialogTitle><DialogDescription>Снимки создаются в выбранной папке Google Диска на этом компьютере. Саму загрузку выполняет Google Drive for desktop.</DialogDescription></DialogHeader>
      <div className="space-y-3 text-[12px] leading-relaxed">
        <p>На обоих компьютерах установите Google Диск и выберите одну и ту же папку. Отправьте снимок на первом компьютере, дождитесь его загрузки в Google Диск, затем дождитесь скачивания на втором и выберите снимок ниже.</p>
        <div className="border p-2"><div className="label">папка Google Диска</div><div className="break-all font-mono">{info?.folder || "не выбрана"}</div><Button variant="outline" size="sm" disabled={busy} onClick={() => void run(async () => { await fly?.chooseSyncFolder(); await refresh(); })}>Выбрать папку</Button></div>
        <p>Передаются идеи, этапы, исходный код, результаты, история чатов, тарифы и журнал API. Ключи API, настройки приложения, зависимости и .venv не передаются. В коде и чатах могут быть секреты: проверьте их перед отправкой. Дополнительное сквозное шифрование не применяется.</p>
        <label className="flex items-start gap-2"><input type="checkbox" checked={includeData} onChange={(e) => setIncludeData(e.target.checked)} disabled={busy} /> Включить папку данных и вручную подключённые таблицы. Они могут занимать много места и копироваться долго.</label>
        {dirty && <p className="border p-2">Сохраните открытый файл, отправьте или очистите черновик чата и дождитесь ответа помощника.</p>}
        <Button size="sm" disabled={busy || dirty || !info?.folder} onClick={upload}>Отправить снимок</Button>
        <div className="border-t pt-3 space-y-2">
          <p>Снимки не объединяются. Загрузка заменяет состояние и совпадающие файлы; лишние файлы не удаляются. Перед заменой программа сохраняет локальную резервную копию.</p>
          <div className="flex flex-wrap gap-2">
            <select className="border bg-background p-1" disabled={busy} value={source} onChange={(e) => { setSource(e.target.value as "shared" | "backup"); setId(""); }}><option value="shared">Google Диск</option><option value="backup">Локальные резервные копии</option></select>
            <Button variant="outline" size="sm" disabled={busy} onClick={() => void run(refresh)}>Обновить список</Button>
          </div>
          <select aria-label="Снимок" className="w-full border bg-background p-1 font-mono text-[11px]" disabled={busy} value={id} onChange={(e) => setId(e.target.value)}>
            <option value="">Выберите снимок</option>
            {snapshots?.map((s) => <option key={s.id} value={s.id}>{s.createdAt} / {s.id} / файлов: {s.fileCount}{s.includeData ? " / с данными" : ""}</option>)}
          </select>
          <Button size="sm" disabled={busy || dirty || !id} onClick={restore}>Загрузить выбранный снимок</Button>
          <p className="break-all text-muted-foreground">Локальные копии: {info?.backupRoot || "..."}</p>
        </div>
        {info?.error && <p>{info.error}</p>}
        {busy && <p>Выполняется{progress ? `: ${progress.phase} ${progress.done}/${progress.total} ${progress.file}` : "..."}</p>}
        {message && <p className="border p-2 break-words" role="status">{message}</p>}
      </div>
    </DialogContent>
  </Dialog>;
}
