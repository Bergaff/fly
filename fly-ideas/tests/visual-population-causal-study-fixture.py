from pathlib import Path
import csv, importlib.util, json, tempfile
root=Path(__file__).parents[1]
script=root/'experiments/templates/71_visual_population_causal_study.py'
spec=importlib.util.spec_from_file_location('visual_causal',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);out=p/'out';out.mkdir()
 proto=m.write_protocol(out)
 assert proto['primary_populations']==['T4a','T4b','T4c','T4d','T5a','T5b','T5c','T5d']
 assert len(proto['conditions'])==15 and proto['frozen_before_shiu_results'] is True
 activity=p/'activity.csv'
 with activity.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['eye','frame','time_s','flyvis_type','central_activity_au'])
  for t in m.PRIMARY:w.writerow([0,0,0,t,.1])
 neurons=p/'neurons.csv'
 with neurons.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['root_id','cell_type']);w.writerows([[1000+i,t] for i,t in enumerate(m.PRIMARY)])
 result=m.mapping_candidates(activity,neurons,out)
 assert result=={'types':8,'primary_with_exact_candidates':8,'reviewed':False}
 review=json.loads((out/'mapping_review.json').read_text())
 assert review['reviewed'] is False and review['entries']==[]
 try:m.validate_mapping(out/'mapping_review.json',out)
 except ValueError:pass
 else:raise AssertionError('unreviewed mapping must stay blocked')
 review.update(reviewed=True,reviewer='fixture reviewer',reviewed_utc='2026-09-18T00:00:00Z',entries=[{'flyvis_type':t,'flywire_ids':[str(1000+i)],'evidence':'fixture only','rate_rule':'linear fixture','sign':1,'min_hz':0,'max_hz':100} for i,t in enumerate(m.PRIMARY)])
 approved=p/'approved.json';approved.write_text(json.dumps(review))
 gate=m.validate_mapping(approved,out)
 assert gate['passed'] is True and len(gate['conditions_unlocked'])==15
 print('visual population causal fixture: OK')
