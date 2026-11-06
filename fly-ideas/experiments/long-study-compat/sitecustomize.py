"""Narrow workaround for transient Windows locks on the study progress display.

Only active when launched through RUN-TWO-FLIES-LARGE-STUDY.bat.  SQLite,
scientific payloads, and CSV exports are deliberately not intercepted.
"""
import os
import sys
import time

_original_replace = os.replace
_RETRIES = 30
_DELAY_SECONDS = 0.2


def _is_progress(src, dst):
    try:
        src, dst = os.fsdecode(src), os.fsdecode(dst)
        a, b = os.path.abspath(src), os.path.abspath(dst)
        return (os.path.basename(a).lower() == 'progress.json.tmp'
                and os.path.basename(b).lower() == 'progress.json'
                and os.path.normcase(os.path.dirname(a)) == os.path.normcase(os.path.dirname(b))
                and os.path.basename(os.path.dirname(b)).lower().startswith('large_two_flies_'))
    except (TypeError, ValueError):
        return False


def _replace_with_retry(src, dst, *args, **kwargs):
    if not _is_progress(src, dst):
        return _original_replace(src, dst, *args, **kwargs)
    for attempt in range(_RETRIES + 1):
        try:
            return _original_replace(src, dst, *args, **kwargs)
        except PermissionError as exc:
            if attempt == _RETRIES:
                print('ПРЕДУПРЕЖДЕНИЕ: Windows блокирует progress.json. '
                      'Сохранённые группы остаются в базе; этот файл может отставать. '
                      'Ориентируйтесь на счётчик в окне и закройте программы, открывшие progress.json. '
                      f'Причина: {exc}', file=sys.stderr, flush=True)
                return None
            time.sleep(_DELAY_SECONDS)


_replace_with_retry._fly_progress_retry = True
if os.environ.get('FLY_LONG_STUDY_IO_RETRY') == '1':
    os.replace = _replace_with_retry
