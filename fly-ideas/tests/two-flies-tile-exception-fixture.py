import csv
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
script = root / 'experiments/templates/46_find_tile_exception.py'
spec = importlib.util.spec_from_file_location('tile_find', script)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def save(path, fields, data):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(data)


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def fails(fn, message):
    try: fn()
    except ValueError as e: assert message in str(e), str(e)
    else: raise AssertionError('expected ValueError')

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    group = dict(group_id='1234', frequency_hz='2', phase_deg='60', distance='4.2', offset='0.4', control='tile_scramble', wings_spikes='65', control_spikes='65', neurons_different_times='1', unmatched_spike_events='10', max_abs_feature_diff='1e-8')
    pairs = [dict(group_id='1234', frequency_hz='2', control='tile_scramble', neuron_id=str(n), wings_spikes='2', control_spikes='2', matched_spikes_same_tick='2', unmatched_spike_events='0') for n in range(32)]
    pairs[7].update(wings_spikes='3', control_spikes='3', matched_spikes_same_tick='-2', unmatched_spike_events='10')
    # Five unmatched on each side requires at least five spikes.
    group.update(wings_spikes='68', control_spikes='68')
    pairs[7].update(wings_spikes='6', control_spikes='6', matched_spikes_same_tick='1', unmatched_spike_events='10')
    gf, pf = folder/'groups.csv', folder/'neuron_pairs.csv'
    save(gf, sorted(mod.GROUP_FIELDS), [group]); save(pf, sorted(mod.PAIR_FIELDS), pairs)
    before = (digest(gf), digest(pf))
    lines = '\n'.join(mod.find(folder))
    assert 'Группа: 1234' in lines and 'Нейрон 7: wings 6, tile_scramble 6; совпало 1; без совпадения wings 5, tile_scramble 5' in lines
    for i in range(2):
        r = subprocess.run([sys.executable, str(script), '--folder', str(folder)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    reports = list(folder.glob('tile_exception_*.txt')); assert len(reports) == 2
    assert (digest(gf), digest(pf)) == before
    (folder/'INCOMPLETE.txt').write_text('incomplete')
    fails(lambda: mod.find(folder), 'незавершённый')
    (folder/'INCOMPLETE.txt').unlink()
    save(pf, sorted(mod.PAIR_FIELDS), pairs[:-1]); fails(lambda: mod.find(folder), 'неполный')
    save(pf, sorted(mod.PAIR_FIELDS), pairs + [pairs[7]]); fails(lambda: mod.find(folder), 'повтор нейрона')
    pairs[7]['unmatched_spike_events'] = '9'; save(pf, sorted(mod.PAIR_FIELDS), pairs); fails(lambda: mod.find(folder), 'не согласуются')
    group.update(neurons_different_times='0', unmatched_spike_events='0'); save(gf, sorted(mod.GROUP_FIELDS), [group])
    assert 'нет групп' in '\n'.join(mod.find(folder))
    pf.unlink(); fails(lambda: mod.find(folder), 'оба файла')
print('tile exception extraction: OK')
