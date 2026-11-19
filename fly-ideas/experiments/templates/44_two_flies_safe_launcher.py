"""Launcher-side handling of temporary progress and CSV locks; study 44 stays unchanged."""
import importlib
import multiprocessing as mp
import sys
import time

study = importlib.import_module('44_two_flies_large_study')
_original_status = study.status
_original_export = study.export_summary
_progress_retry_at = 0.0
_progress_blocked = False
_PROGRESS_COOLDOWN = 30.0
_CSV_RETRIES = 20
_CSV_DELAY = 0.5


def status_with_lock_recovery(folder, state, done, total, started, reason='', initial=0):
    global _progress_retry_at, _progress_blocked
    # progress.json is only a display; SQLite group transactions are never skipped.
    if state == 'running' and time.monotonic() < _progress_retry_at:
        return
    try:
        result = _original_status(folder, state, done, total, started, reason, initial)
    except PermissionError as exc:
        if not _progress_blocked or state != 'running':
            print('ПРЕДУПРЕЖДЕНИЕ: не удалось обновить progress.json: '
                  f'{exc}. Данные групп записываются отдельно в SQLite; '
                  'файл прогресса может отставать. Счётчик виден в окне. '
                  'Закройте программы, открывшие progress.json или progress.json.tmp.',
                  file=sys.stderr, flush=True)
        _progress_blocked = True
        _progress_retry_at = time.monotonic() + _PROGRESS_COOLDOWN
        return
    if _progress_blocked:
        print('Обновление progress.json восстановлено.', flush=True)
    _progress_blocked = False
    _progress_retry_at = 0.0
    return result


def export_with_lock_recovery(db, folder):
    # These CSVs are regenerated from the committed database. Never claim an
    # export succeeded when an error persists; restart the entire export on retry.
    while True:
        last_error = None
        for attempt in range(_CSV_RETRIES + 1):
            try:
                result = _original_export(db, folder)
                if attempt:
                    print('Сохранение CSV восстановлено.', flush=True)
                return result
            except PermissionError as exc:
                last_error = exc
                if attempt == 0:
                    print(f'Windows заблокировала экспорт CSV: {exc}. '
                          'Закройте эти CSV в Excel и других программах. '
                          'Повторяем сохранение автоматически; SQLite не изменяется этим экспортом.',
                          file=sys.stderr, flush=True)
                if attempt < _CSV_RETRIES:
                    time.sleep(_CSV_DELAY)
        print('CSV всё ещё недоступен. Закройте открытые таблицы или проверьте права папки.', file=sys.stderr, flush=True)
        if not sys.stdin.isatty():
            raise PermissionError('Не удалось сохранить CSV после повторов; интерактивный повтор недоступен.') from last_error
        try:
            answer = input('Enter: повторить сохранение; Q: безопасно остановить расчёт: ').strip().lower()
        except EOFError:
            raise PermissionError('Не удалось сохранить CSV: ввод недоступен.') from last_error
        if answer in ('q', 'й'):
            raise PermissionError('Сохранение CSV остановлено пользователем. Завершённые группы остаются в SQLite.') from last_error


def main():
    study.status = status_with_lock_recovery
    study.export_summary = export_with_lock_recovery
    print('Включена защита прогресса и повтор сохранения CSV. SQLite не обходится.', flush=True)
    study.main()


if __name__ == '__main__':
    mp.freeze_support()
    try:
        main()
    except Exception as e:
        print(f'ОШИБКА: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
        sys.exit(1)
