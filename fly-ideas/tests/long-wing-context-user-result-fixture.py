"""Check the manually transcribed user report and derived comparisons."""
import json,math
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'experiments/reports/long-user-wing-context-intervention-user-transcribed.json'
o=json.loads(p.read_text(encoding='utf-8'))
assert o['segment_s']==[1.44,1.60] and o['delta_deg']==10
rows={r['condition']:r for r in o['conditions']}
assert len(rows)==12
base=rows['baseline'];only=rows['only_right_x'];ryp=rows['right_y_plus_10deg'];rzp=rows['right_z_plus_10deg']
assert abs((1-only['new_rmse_rad']/base['new_rmse_rad'])*100-80.7936576658)<1e-9
assert abs((1-only['old_rmse_rad']/base['old_rmse_rad'])*100-81.6126527709)<1e-9
assert abs((only['new_rmse_rad']/only['old_rmse_rad']-1)*100-13.5268410795)<1e-9
assert abs(only['new_mean_delta_rad']*180/math.pi-55.18236739)<1e-8
assert abs((1-ryp['new_rmse_rad']/base['new_rmse_rad'])*100-20.3683875738)<1e-9
assert abs((1-rzp['new_rmse_rad']/base['new_rmse_rad'])*100-10.0758322565)<1e-9
single=[r for r in o['conditions'] if r['condition'] not in ('baseline','only_right_x')]
assert max(single,key=lambda r:abs(r['new_mean_delta_rad']))['condition']=='right_y_plus_10deg'
positive=sum(rows[name]['new_mean_delta_rad'] for name in ('left_x_plus_10deg','left_y_minus_10deg','left_z_minus_10deg','right_y_plus_10deg','right_z_plus_10deg'))
assert abs(positive-.489925)<1e-12 and positive<only['new_mean_delta_rad']
print('context user result transcription passed')
