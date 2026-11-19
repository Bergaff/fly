#!/usr/bin/env python3
"""Independently recompute exported series86 identity, RSA and population gates."""
import hashlib,json,math,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXPECTED='e66a6b52890bbf33b5071f7a2acb15d29a2e8051448a8dfae500df482b46da00';ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
def distance(x,y):return math.sqrt(sum((a-b)**2 for a,b in zip(x,y)))
def classify(v,protos,scale):return min(ACTIONS,key=lambda a:distance([x/s for x,s in zip(v,scale)],[x/s for x,s in zip(protos[a],scale)]))
def corr(x,y):
 mx=sum(x)/len(x);my=sum(y)/len(y);return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
def population_corr(rows,name,axis):
 s={k:sum(r['population_sufficient'][name][axis][k] for r in rows) for k in ('n','sx','sy','sxx','syy','sxy')};n=s['n'];vx=s['sxx']-s['sx']**2/n;vy=s['syy']-s['sy']**2/n;return (s['sxy']-s['sx']*s['sy']/n)/math.sqrt(vx*vy) if vx>1e-12 and vy>1e-12 else 0.
def pooled(rows,key):
 n=sum(r['frames'] for r in rows);return math.sqrt(sum(r['frames']*r[key]['rmse_rad']**2 for r in rows)/n)
def close(a,b):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8)
def verify(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED;d=json.loads(raw);protocol=d['protocol'];p=d['primary'];assert d['schema']=='multiaction-compositional-population-result-v1' and d['status']=='completed';assert protocol['script_sha256']=='7dc5686028a2fe82d683f091a1f0a08deab25bcc2be41320b5d52e91de6d9714' and protocol['runner85_sha256']=='cdef42fd5f4f45d7b5b37ab01f2b3ba4af22663265b1e1980254a7b44596b210';assert protocol['selected_model_sha256']=='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0' and not protocol['training_allowed'];assert protocol['actions']==list(ACTIONS) and [x['id'] for x in protocol['motions']]==list(range(471,498))
 rows=d['tests'];assert len(rows)==324 and len({(x['id'],x['corner_id']) for x in rows})==324;assert {r:sum(x['role']==r for x in rows) for r in ('calibration','identity','composition')}=={'calibration':36,'identity':192,'composition':96};assert sum(x['state_unchanged_during_delay'] and x['state_sha256_before_delay']==x['state_sha256_after_delay'] for x in rows)==324
 audit=p['representation_audit'];labels={x['id']:x['action'] for x in p['identity']['cases']};ids=sorted(labels);pred={i:classify(audit['identity_observation_features'][str(i)],audit['prototypes'],audit['scale']) for i in ids};private={i:classify(audit['identity_private_features'][str(i)],audit['private_prototypes'],audit['private_scale']) for i in ids};assert all(pred[x['id']]==x['shared_prediction'] and private[x['id']]==x['private_prediction'] for x in p['identity']['cases']);assert sum(pred[i]==labels[i] for i in ids)==p['identity']['correct']==11;assert sum(private[i]==labels[i] for i in ids)==p['identity']['private_correct']==11;assert p['identity']['per_action']=={'foreleg_rubbing':{'correct':4,'cases':4},'head_directed_grooming':{'correct':3,'cases':4},'reach_withdraw':{'correct':4,'cases':4}} and p['identity']['passed']
 obs={i:[x/s for x,s in zip(audit['identity_observation_features'][str(i)],audit['scale'])] for i in ids};exe={i:[x/s for x,s in zip(audit['identity_execution_features'][str(i)],audit['scale'])] for i in ids};pairs=[];od=[];ed=[]
 for ni,i in enumerate(ids):
  for j in ids[ni+1:]:pairs.append([i,j]);od.append(distance(obs[i],obs[j]));ed.append(distance(exe[i],exe[j]))
 rsa=p['cross_mode_rsa'];assert pairs==rsa['pairs']==audit['rsa']['pairs'];assert max(abs(x-y) for x,y in zip(od,rsa['observation_distances']))<2e-12 and max(abs(x-y) for x,y in zip(ed,rsa['execution_distances']))<2e-12;actual=corr(od,ed);assert close(actual,rsa['correlation']) and actual>=.30 and actual>rsa['shuffled_p95'] and rsa['passed'];rng=random.Random(860502);null=[]
 for _ in range(1000):
  q=ids[:];rng.shuffle(q);pd=[]
  for ni in range(len(q)):
   for nj in range(ni+1,len(q)):pd.append(distance(exe[q[ni]],exe[q[nj]]))
  null.append(corr(od,pd))
 null.sort();assert actual>null[949]
 evalrows=[x for x in rows if x['role']!='calibration'];reported=p['population'];dual={}
 for axis in AXES:
  values={name:population_corr(evalrows,name,axis) for name in ('shared_observation','shuffled','static','closed')}
  assert all(close(value,reported['correlations'][name][axis]) for name,value in values.items());dual[axis]=values['shared_observation']>=.15 and values['shared_observation']>max(values[x] for x in ('shuffled','static','closed'))
 assert dual==reported['dual_active_units'] and sum(dual.values())==reported['dual_active_count']==5;total=sum(r['frames'] for r in evalrows);combined={k:pooled(evalrows,k) for k in ('shared_observation','private_observation','execution_mode','zero')};combined.update({k:math.sqrt(sum(r['frames']*r['controls'][k]['rmse_rad']**2 for r in evalrows)/total) for k in ('shuffled','static','closed')});assert all(close(v,reported['combined'][k]) for k,v in combined.items());assert reported['performance_passed'] and reported['passed'];assert p['composition']['correct']==6 and all(x['passed'] for x in p['composition']['cases']) and p['passed'];assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive'];print(f'Series86 identity, exported RSA and population gates independently recomputed; independent RSA null p95={null[949]:.6f}. Composition is 6/6 as reported but half-feature vectors were not exported for independent classification replay.')
def verify_extract():
 d=json.loads((ROOT/'experiments/reports/multiaction-compositional-population-user-summary-extract.json').read_text());assert d['source_file_sha256']==EXPECTED and d['primary']['passed'];x=d['derived'];assert x['records']==x['distinct_pairs']==x['state_unchanged_and_sha_match']==324;assert x['identity_recomputed']['shared_correct']==x['identity_recomputed']['private_correct']==11;assert close(x['rsa_recomputed']['correlation'],.7929697692652838) and not x['composition_independently_recomputable_from_summary'];assert x['overlap_totals']=={'under_0_001_deg':0,'under_1_deg':0,'under_5_deg':295};print('Persisted series86 extract matches the verified go and composition-export limitation.')
if __name__=='__main__':verify(sys.argv[1]) if len(sys.argv)>1 else verify_extract()
