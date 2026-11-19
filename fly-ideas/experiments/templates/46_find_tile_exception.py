#!/usr/bin/env python3
"""Extract tile_scramble timing differences from an existing paired CSV analysis."""
import argparse
import csv
from datetime import datetime
import os
from pathlib import Path
import sys
import uuid

GROUP_FIELDS = {'group_id', 'frequency_hz', 'phase_deg', 'distance', 'offset', 'control', 'wings_spikes', 'control_spikes', 'neurons_different_times', 'unmatched_spike_events', 'max_abs_feature_diff'}
PAIR_FIELDS = {'group_id', 'frequency_hz', 'control', 'neuron_id', 'wings_spikes', 'control_spikes', 'matched_spikes_same_tick', 'unmatched_spike_events'}


def rows(path, required):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f'{path.name}: отсутствуют столбцы {", ".join(sorted(missing))}')
        yield from reader


def find(folder):
    folder = Path(folder).resolve()
    if (folder / 'INCOMPLETE.txt').exists():
        raise ValueError('Этот парный анализ отмечен как незавершённый (INCOMPLETE.txt). Выберите другую папку.')
    group_file, pair_file = folder / 'groups.csv', folder / 'neuron_pairs.csv'
    if not group_file.is_file() or not pair_file.is_file():
        raise ValueError('В папке должны находиться оба файла: groups.csv и neuron_pairs.csv.')
    groups = {}
    for row in rows(group_file, GROUP_FIELDS):
        if row['control'] == 'tile_scramble' and int(row['neurons_different_times']) > 0:
            if row['group_id'] in groups:
                raise ValueError('Повтор группы tile_scramble в groups.csv.')
            groups[row['group_id']] = row
    # Empty results are reported as such: no claim is made about the rest of the database.
    if not groups:
        return ['В выбранном groups.csv нет групп tile_scramble с различающимися временами.',
                'Это результат поиска по CSV; база SQLite и полнота таблиц не проверялись.']
    found = {key: {} for key in groups}
    for row in rows(pair_file, PAIR_FIELDS):
        key = row['group_id']
        if row['control'] != 'tile_scramble' or key not in found:
            continue
        neuron = row['neuron_id']
        if neuron in found[key]:
            raise ValueError(f'Группа {key}: повтор нейрона {neuron} в neuron_pairs.csv.')
        found[key][neuron] = row
    result = ['ПОИСК РАСХОЖДЕНИЙ TILE_SCRAMBLE', f'Источник: {folder}',
              f'Групп с разными временами: {len(groups)}',
              'Сравнение: один и тот же нейрон и один и тот же шаг 1 мс.', '']
    for key, group in groups.items():
        pairs = found[key]
        if set(pairs) != {str(i) for i in range(32)}:
            raise ValueError(f'Группа {key}: в neuron_pairs.csv найден неполный или некорректный набор 32 нейронов.')
        different = [p for p in pairs.values() if int(p['unmatched_spike_events']) > 0]
        if len(different) != int(group['neurons_different_times']) or sum(int(p['unmatched_spike_events']) for p in different) != int(group['unmatched_spike_events']):
            raise ValueError(f'Группа {key}: строки groups.csv и neuron_pairs.csv не согласуются.')
        for p in pairs.values():
            a, b, m, u = (int(p[x]) for x in ('wings_spikes', 'control_spikes', 'matched_spikes_same_tick', 'unmatched_spike_events'))
            if min(a, b, m, u) < 0 or m > min(a, b) or a + b - 2*m != u:
                raise ValueError(f'Группа {key}, нейрон {p["neuron_id"]}: некорректные счёты.')
        if sum(int(p['wings_spikes']) for p in pairs.values()) != int(group['wings_spikes']) or sum(int(p['control_spikes']) for p in pairs.values()) != int(group['control_spikes']):
            raise ValueError(f'Группа {key}: суммарные счёты CSV не совпадают.')
        result.extend([f'Группа: {key}; частота: {group["frequency_hz"]} Гц; фаза: {group["phase_deg"]}; расстояние: {group["distance"]}; смещение: {group["offset"]}',
                       f'Всего спайков: wings {group["wings_spikes"]}, tile_scramble {group["control_spikes"]}; максимальная разность входа в группе: {group["max_abs_feature_diff"]}'])
        for p in different:
            a, b, m = (int(p[x]) for x in ('wings_spikes', 'control_spikes', 'matched_spikes_same_tick'))
            result.append(f'Нейрон {p["neuron_id"]}: wings {a}, tile_scramble {b}; совпало {m}; без совпадения wings {a-m}, tile_scramble {b-m}.')
        result.append('')
    result.extend(['Эти таблицы не содержат точных времён несовпавших спайков и не устанавливают причину различий.',
                   'Это поиск по готовым CSV; SQLite, контрольные суммы и полнота всего анализа повторно не проверялись.'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', help='Папка готового парного анализа (ручной запуск)')
    args = parser.parse_args()
    if not args.folder:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        try:
            selection = filedialog.askopenfilename(title='Выберите groups.csv из папки paired_analysis_...', filetypes=[('CSV', '*.csv'), ('Все файлы', '*.*')])
        finally:
            root.destroy()
        if not selection:
            print('Выбор отменён.'); return
        if Path(selection).name.lower() != 'groups.csv':
            raise ValueError('Выберите именно groups.csv из папки готового парного анализа.')
        args.folder = str(Path(selection).parent)
    result = find(args.folder)
    output = Path(args.folder).resolve() / f'tile_exception_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.txt'
    with output.open('x', encoding='utf-8-sig') as handle:
        handle.write('\n'.join(result) + '\n')
    print('\n'.join(result)); print(f'\nСохранено: {output}')
    if os.name == 'nt':
        try: os.startfile(str(output))
        except OSError as exc: print(f'Не удалось открыть файл автоматически: {exc}\nОткройте его по указанному пути.')


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}\nИсходные CSV и база не изменены.', file=sys.stderr, flush=True)
        sys.exit(1)
