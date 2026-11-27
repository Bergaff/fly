#!/usr/bin/env python3
"""Independent verifier for uploaded or persisted series89B6 summary."""
from __future__ import annotations
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
SOURCE='f1c362073c81f505a28ada36306bf51160ec9f3051ad3997b123c4777dc2fcc2';SCRIPT='1d308cb1ff20a7f6934775c0da62df99bdf062b1fc5e1395328f4f94594c0cb6';B5='6ebd6af6910ec1e5b30984d9247e3fc7374031393466e7959ad37cfd1fc697fc';B5_EXTRACT='0729aac36bef0208e0a3a6354536e92066e43a95a55960447da3ae2a92744b2e';B5_UPLOAD='c14bbb13d7900ae017e5248b65d0eaac19e85c53c03e5124e4d6d0b3cf32b8e1';MODEL84Z='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0';ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');ANGLE=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');BROAD=('soft_mixture','angle_only','common_contact')+ANGLE;CONTACT=('standard_hard','oracle_expert')+BROAD

def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-12)
def load(path):
 p=Path(path);d=json.loads(p.read_text(encoding='utf8'));actual=hashlib.sha256(p.read_bytes()).hexdigest()
 if d.get('source_file_sha256'):assert d['source_file_sha256']==SOURCE and d['reported_schema']=='robust-foreleg-contact-development-result-v1' and d['reported_status']=='completed'
 else:assert actual==SOURCE and d['schema']=='robust-foreleg-contact-development-result-v1' and d['status']=='completed'
 return d
def verify(path):
 d=load(path);p=d['protocol'];reported=d.get('reported_primary',d.get('primary'));rows=d['tests']
 assert p['mode']=='full' and p['script_sha256']==SCRIPT and p['runner89b5_sha256']==B5 and p['series89b5_nogo_extract_sha256']==B5_EXTRACT and p['series89b5_upload_sha256']==B5_UPLOAD and p['frozen84z_model_sha256']==MODEL84Z==p['selected_model_sha256']
 assert p['candidate_inference_uses_truth_action'] is False and p['oracle_control_uses_truth_action'] is True and p['final_used_for_fit'] is False and p['source84z_training_allowed'] is False
 motions=p['motions'];assert [x['id'] for x in motions if x['role']=='development']==list(range(783,801));assert [x['id'] for x in motions if x['role']=='final']==list(range(801,819));assert len({x['motion_sha256'] for x in motions})==36 and len(p['development_views'])==8 and len(p['final_views'])==12
 assert len(rows)==216 and len({(x['id'],x['corner_id']) for x in rows})==216 and Counter(x['action'] for x in rows)==Counter({a:72 for a in ACTIONS}) and all(x['oracle_control_only_uses_truth_action'] is True for x in rows)
 identity=sum(x['action']==x['predicted_action'] for x in rows);identity_by={a:sum(x['predicted_action']==a for x in rows if x['action']==a) for a in ACTIONS};assert identity==216 and identity_by=={a:72 for a in ACTIONS}
 flat=[(r,t) for r in rows for t in r['trials']];assert len(flat)==648 and Counter(t['initial_profile'] for r,t in flat)==Counter({x:216 for x in PROFILES}) and len({t['initial_seed'] for r,t in flat})==648
 means={c:{m:sum(t['controls'][c][m] for r,t in flat)/648 for m in ('angle_rmse_truth','contact_mae_truth')} for c in p['controls']};aw={c:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][c]['angle_rmse_truth'] for r,t in flat) for c in ANGLE};cw={c:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][c]['contact_mae_truth'] for r,t in flat) for c in CONTACT};action_cw={a:{c:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][c]['contact_mae_truth'] for r,t in flat if r['action']==a) for c in ('angle_only','common_contact')} for a in ACTIONS};foreleg_standard=sum(t['controls']['candidate']['contact_mae_truth']<t['controls']['standard_hard']['contact_mae_truth'] for r,t in flat if r['action']=='foreleg_rubbing')
 safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=1.25+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(t['controls']['candidate']) for r,t in flat);recovered=sum(t['controls']['candidate']['recovered'] for r,t in flat);completed=sum(t['controls']['candidate']['completion_ratio']>=.65 for r,t in flat)
 assert aw=={'uncalibrated':648,'zero_state':648,'shuffled_state':648,'open_loop':644,'shared_lesion':648};assert cw=={'standard_hard':126,'oracle_expert':0,'soft_mixture':587,'angle_only':638,'common_contact':633,'uncalibrated':557,'zero_state':648,'shuffled_state':648,'open_loop':639,'shared_lesion':648};assert action_cw=={'foreleg_rubbing':{'angle_only':214,'common_contact':201},'head_directed_grooming':{'angle_only':213,'common_contact':216},'reach_withdraw':{'angle_only':211,'common_contact':216}} and foreleg_standard==126;assert safety==648 and recovered==645 and completed==648
 for c in means:
  for m in means[c]:assert close(means[c][m],reported['means'][c][m])
 identity_gate=identity>=195 and all(identity_by[a]>=65 for a in ACTIONS);angle=all(aw[c]>=584 for c in ANGLE) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];broad_pass=sum(cw[c]>=584 for c in BROAD);contact=cw['angle_only']>=584 and cw['common_contact']>=584 and all(action_cw[a][c]>=195 for a in ACTIONS for c in ('angle_only','common_contact')) and broad_pass>=7 and means['candidate']['contact_mae_truth']<=means['standard_hard']['contact_mae_truth'] and means['candidate']['contact_mae_truth']<=means['soft_mixture']['contact_mae_truth'] and means['candidate']['contact_mae_truth']<=means['oracle_expert']['contact_mae_truth']+.02
 assert identity_gate and angle and contact and broad_pass==7 and reported['identity_gate_passed'] is True and reported['angle_gate_passed'] is True and reported['contact_gate_passed'] is True and reported['passed'] is True
 assert close(means['candidate']['contact_mae_truth'],.12261123683061008) and close(means['standard_hard']['contact_mae_truth'],.12264350262967895) and close(means['soft_mixture']['contact_mae_truth'],.12698217444321885);assert all(t['controls']['candidate']==t['controls']['oracle_expert'] for r,t in flat)
 assert d['model']['foreleg_boost_selected']['boost']==4.0 and d['model']['foreleg_boost_selected']['common_wins']==46
 assert reported['identity_correct']==identity and reported['identity_by_action']==identity_by and reported['candidate_safety_passed']==safety and reported['candidate_recovered']==recovered and reported['candidate_completed']==completed and reported['candidate_angle_wins']==aw and reported['candidate_contact_wins']==cw and reported['candidate_action_contact_wins']==action_cw and reported['foreleg_wins_standard_hard']==foreleg_standard and reported['broad_controls_passed']==broad_pass
 return {'source_sha256':SOURCE,'cases':216,'trials':648,'identity':identity,'safety':safety,'recovered':recovered,'completed':completed,'boost':4.0,'contact_wins':cw,'action_contact_wins':action_cw,'broad_controls_passed':broad_pass,'candidate_contact_mean':means['candidate']['contact_mae_truth'],'passed':True}
def main():
 q=argparse.ArgumentParser();q.add_argument('summary');a=q.parse_args();print(json.dumps(verify(a.summary),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
