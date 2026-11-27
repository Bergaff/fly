#!/usr/bin/env python3
"""Independent verifier for uploaded or persisted series89B5 summary."""
from __future__ import annotations
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
SOURCE='c14bbb13d7900ae017e5248b65d0eaac19e85c53c03e5124e4d6d0b3cf32b8e1';SCRIPT='6ebd6af6910ec1e5b30984d9247e3fc7374031393466e7959ad37cfd1fc697fc';B4='1f86189bc11e1822c81c488e1c85a377247ffd2d6d8286589d780e729cf07c2f';B4_EXTRACT='3c69f14b2f4554594b199b638abf96ad166c5d5c423b30058cf73773fd144150';B4_UPLOAD='334c4a89a87a9cbbac357cc533b99863caa25e9045fba5e8f9ac50c57aff975f';MODEL84Z='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0';ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');ANGLE=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');CONTACT=('soft_mixture','angle_only','common_contact','oracle_expert')+ANGLE

def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-12)
def load(path):
 p=Path(path);d=json.loads(p.read_text(encoding='utf8'));actual=hashlib.sha256(p.read_bytes()).hexdigest()
 if d.get('source_file_sha256'):
  assert d['source_file_sha256']==SOURCE and d['reported_schema']=='predicted-hard-contact-development-result-v1' and d['reported_status']=='completed'
 else:assert actual==SOURCE and d['schema']=='predicted-hard-contact-development-result-v1' and d['status']=='completed'
 return d
def verify(path):
 d=load(path);p=d['protocol'];reported=d.get('reported_primary',d.get('primary'));rows=d['tests']
 assert p['mode']=='full' and p['script_sha256']==SCRIPT and p['runner89b4_sha256']==B4 and p['series89b4_nogo_extract_sha256']==B4_EXTRACT and p['series89b4_upload_sha256']==B4_UPLOAD
 assert p['frozen84z_model_sha256']==MODEL84Z==p['selected_model_sha256'];assert p['candidate_inference_uses_truth_action'] is False and p['oracle_control_uses_truth_action'] is True and p['final_used_for_fit'] is False and p['source84z_training_allowed'] is False
 motions=p['motions'];assert [x['id'] for x in motions if x['role']=='development']==list(range(747,765));assert [x['id'] for x in motions if x['role']=='final']==list(range(765,783));assert len({x['motion_sha256'] for x in motions})==36;assert len(p['development_views'])==8 and len(p['final_views'])==12
 assert len(rows)==216 and len({(x['id'],x['corner_id']) for x in rows})==216 and Counter(x['action'] for x in rows)==Counter({a:72 for a in ACTIONS});assert all(x['oracle_control_only_uses_truth_action'] is True for x in rows)
 identity=sum(x['action']==x['predicted_action'] for x in rows);identity_by={a:sum(x['predicted_action']==a for x in rows if x['action']==a) for a in ACTIONS};assert identity==216 and identity_by=={a:72 for a in ACTIONS}
 flat=[(r,t) for r in rows for t in r['trials']];assert len(flat)==648 and Counter(t['initial_profile'] for r,t in flat)==Counter({x:216 for x in PROFILES}) and len({t['initial_seed'] for r,t in flat})==648
 means={c:{m:sum(t['controls'][c][m] for r,t in flat)/648 for m in ('angle_rmse_truth','contact_mae_truth')} for c in p['controls']};aw={c:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][c]['angle_rmse_truth'] for r,t in flat) for c in ANGLE};cw={c:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][c]['contact_mae_truth'] for r,t in flat) for c in CONTACT};action_cw={a:{c:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][c]['contact_mae_truth'] for r,t in flat if r['action']==a) for c in ('angle_only','common_contact')} for a in ACTIONS}
 safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=1.25+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(t['controls']['candidate']) for r,t in flat);recovered=sum(t['controls']['candidate']['recovered'] for r,t in flat);completed=sum(t['controls']['candidate']['completion_ratio']>=.65 for r,t in flat)
 assert aw=={c:648 for c in ANGLE};assert cw=={'soft_mixture':561,'angle_only':635,'common_contact':617,'oracle_expert':0,'uncalibrated':568,'zero_state':648,'shuffled_state':648,'open_loop':647,'shared_lesion':648};assert action_cw=={'foreleg_rubbing':{'angle_only':208,'common_contact':188},'head_directed_grooming':{'angle_only':216,'common_contact':216},'reach_withdraw':{'angle_only':211,'common_contact':213}};assert safety==648 and recovered==645 and completed==648
 for c in means:
  for m in means[c]:assert close(means[c][m],reported['means'][c][m])
 identity_gate=identity>=195 and all(identity_by[a]>=65 for a in ACTIONS);angle=all(aw[c]>=584 for c in ANGLE) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact=cw['angle_only']>=584 and cw['common_contact']>=584 and all(action_cw[a][c]>=195 for a in ACTIONS for c in ('angle_only','common_contact')) and sum(cw[c]>=584 for c in CONTACT)>=7 and means['candidate']['contact_mae_truth']<=means['soft_mixture']['contact_mae_truth'] and means['candidate']['contact_mae_truth']<=means['oracle_expert']['contact_mae_truth']+.02
 assert identity_gate and angle and contact is False and reported['identity_gate_passed'] is True and reported['angle_gate_passed'] is True and reported['contact_gate_passed'] is False and reported['passed'] is False
 assert close(means['candidate']['contact_mae_truth'],.12182673445772269) and close(means['soft_mixture']['contact_mae_truth'],.12601062590948323);assert all(t['controls']['candidate']==t['controls']['oracle_expert'] for r,t in flat)
 assert reported['identity_correct']==identity and reported['identity_by_action']==identity_by and reported['candidate_safety_passed']==safety and reported['candidate_recovered']==recovered and reported['candidate_completed']==completed and reported['candidate_angle_wins']==aw and reported['candidate_contact_wins']==cw and reported['candidate_action_contact_wins']==action_cw
 return {'source_sha256':SOURCE,'cases':216,'trials':648,'identity':identity,'safety':safety,'recovered':recovered,'completed':completed,'contact_wins':cw,'action_contact_wins':action_cw,'candidate_contact_mean':means['candidate']['contact_mae_truth'],'soft_contact_mean':means['soft_mixture']['contact_mae_truth'],'passed':False}
def main():
 q=argparse.ArgumentParser();q.add_argument('summary');a=q.parse_args();print(json.dumps(verify(a.summary),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
