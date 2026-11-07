// Событие завершения может прийти раньше ответа IPC на запрос запуска.
// Отслеживаем оба порядка и не запускаем второй процесс в том же пространстве.
export class RunLaunchTracker {
  private pending = new Map<string, Set<string>>();
  private active = new Map<string, string>();

  begin(scope: string): boolean {
    if (this.pending.has(scope) || this.active.has(scope)) return false;
    this.pending.set(scope, new Set());
    return true;
  }

  exit(scope: string, runId: string): void {
    this.pending.get(scope)?.add(runId);
    if (this.active.get(scope) === runId) this.active.delete(scope);
  }

  resolved(scope: string, runId: string): boolean {
    const alreadyExited = this.pending.get(scope)?.has(runId) ?? false;
    this.pending.delete(scope);
    if (!alreadyExited) this.active.set(scope, runId);
    return !alreadyExited;
  }

  adopt(scope: string, runId: string): boolean {
    if (this.pending.has(scope) || this.active.has(scope)) return false;
    this.active.set(scope, runId);
    return true;
  }

  failed(scope: string): void { this.pending.delete(scope); }
}
