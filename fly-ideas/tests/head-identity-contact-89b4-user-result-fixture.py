#!/usr/bin/env python3
"""Independent verifier for the uploaded or persisted series89B4 summary."""
from __future__ import annotations
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
EXPECTED_SOURCE='334c4a89a87a9cbbac357cc533b99863caa25e9045fba5e8f9ac50c57aff975f'
SCRIPT='1f86189bc11e1822c81c488e1c85a377247ffd2d6d8286589d780e729cf07c2f';B3='b6252829d81ea92c106554f8413cae6b842868c06f69b18fdcd99e5d512ef259';B2='ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3';EXTRACT_B3='99e07b32e0bd6f9bf7fe0c1ad7761db4973f74d9fd4c21d9c37ba009c4164bae';UPLOAD_B3='dd16e35af84f5fe40d5319a9cc2720637639d51f7ac1c442af06cfd632bcccfb';MODEL84Z='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0';ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');ANGLE=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');CONTACT=('angle_only','common_contact','hard_expert','oracle_expert')+ANGLE

def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-12)
def load(path):
 p=Path(path);d=json.loads(p.read_text(encoding='utf8'));actual=hashlib.sha256(p.read_bytes()).hexdigest()
 if d.get('source_file_sha256'):
  assert d['source_file_sha256']==EXPECTED_SOURCE
  assert d['reported_schema']=='head-identity-contact-development-result-v1' and d['reported_status']=='completed'
 else:assert actual==EXPECTED_SOURCE and d['schema']=='head-identity-contact-development-result-v1' and d['status']=='completed'
 return d
def verify(path):
 d=load(path);p=d['protocol'];reported=d.get('reported_primary',d.get('primary'));rows=d['tests']
 assert p['mode']=='full' and p['script_sha256']==SCRIPT and p['runner89b3_sha256']==B3 and p['runner89b2_sha256']==B2
 assert p['series89b3_nogo_extract_sha256']==EXTRACT_B3 and p['series89b3_upload_sha256']==UPLOAD_B3
 assert p['frozen84z_model_sha256']==MODEL84Z==p['selected_model_sha256']
 assert p['candidate_inference_uses_truth_action'] is False and p['oracle_control_uses_truth_action'] is True and p['final_used_for_fit'] is False and p['source84z_training_allowed'] is False
 motions=p['motions'];assert [x['id'] for x in motions if x['role']=='development']==list(range(711,729));assert [x['id'] for x in motions if x['role']=='final']==list(range(729,747));assert len({x['motion_sha256'] for x in motions})==36
 assert len(p['development_views'])==8 and len(p['final_views'])==12 and len(rows)==216 and len({(x['id'],x['corner_id']) for x in rows})==216
 assert Counter(x['action'] for x in rows)==Counter({a:72 for a in ACTIONS});assert all(x['oracle_control_only_uses_truth_action'] is True for x in rows)
 identity=sum(x['action']==x['predicted_action'] for x in rows);assert identity==216
 flat=[(r,t) for r in rows for t in r['trials']];assert len(flat)==648 and Counter(t['initial_profile'] for r,t in flat)==Counter({x:216 for x in PROFILES});assert len({t['initial_seed'] for r,t in flat})==648
 means={};
 for c in p['controls']:
  means[c]={m:sum(t['controls'][c][m] for r,t in flat)/648 for m in ('angle_rmse_truth','contact_mae_truth')}
 aw={c:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][c]['angle_rmse_truth'] for r,t in flat) for c in ANGLE}
 cw={c:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][c]['contact_mae_truth'] for r,t in flat) for c in CONTACT}
 safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=1.25+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(t['controls']['candidate']) for r,t in flat);recovered=sum(t['controls']['candidate']['recovered'] for r,t in flat);completed=sum(t['controls']['candidate']['completion_ratio']>=.65 for r,t in flat)
 assert aw=={'uncalibrated':648,'zero_state':648,'shuffled_state':648,'open_loop':648,'shared_lesion':648}
 assert cw=={'angle_only':624,'common_contact':607,'hard_expert':57,'oracle_expert':57,'uncalibrated':559,'zero_state':648,'shuffled_state':648,'open_loop':635,'shared_lesion':648}
 assert safety==648 and recovered==645 and completed==648
 for c in means:
  for m in means[c]:assert close(means[c][m],reported['means'][c][m])
 angle=all(aw[c]>=584 for c in ANGLE) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth']
 contact=cw['angle_only']>=584 and cw['common_contact']>=584 and sum(cw[c]>=584 for c in CONTACT)>=6 and means['candidate']['contact_mae_truth']<=means['hard_expert']['contact_mae_truth'] and means['candidate']['contact_mae_truth']<=means['oracle_expert']['contact_mae_truth']+.02
 assert angle is True and contact is False and reported['passed'] is False and reported['contact_gate_passed'] is False
 assert close(means['candidate']['contact_mae_truth'],.12728798253263357) and close(means['hard_expert']['contact_mae_truth'],.12206758497022584)
 assert all(t['controls']['hard_expert']==t['controls']['oracle_expert'] for r,t in flat)
 assert reported['identity_correct']==identity and reported['candidate_safety_passed']==safety and reported['candidate_recovered']==recovered and reported['candidate_completed']==completed and reported['candidate_angle_wins']==aw and reported['candidate_contact_wins']==cw
 return {'source_sha256':EXPECTED_SOURCE,'cases':len(rows),'trials':len(flat),'identity':identity,'safety':safety,'recovered':recovered,'completed':completed,'angle_wins':aw,'contact_wins':cw,'candidate_contact_mean':means['candidate']['contact_mae_truth'],'hard_oracle_contact_mean':means['hard_expert']['contact_mae_truth'],'passed':False}
def main():
 q=argparse.ArgumentParser();q.add_argument('summary');a=q.parse_args();print(json.dumps(verify(a.summary),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
