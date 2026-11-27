#!/usr/bin/env python3
"""Recompute every series85 gate available in summary-19; RSA traces were not exported."""
import hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXPECTED='f3fc151bedebaaac8600412172696157f9491144ac23fb7c23a11d76a479d4db';AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
def pooled(rows,key):
 n=sum(r['frames'] for r in rows);return math.sqrt(sum(r['frames']*r[key]['rmse_rad']**2 for r in rows)/n)
def corr(rows,name,axis):
 s={k:sum(r['population_sufficient'][name][axis][k] for r in rows) for k in ('n','sx','sy','sxx','syy','sxy')};n=s['n'];vx=s['sxx']-s['sx']**2/n;vy=s['syy']-s['sy']**2/n;return (s['sxy']-s['sx']*s['sy']/n)/math.sqrt(vx*vy) if vx>1e-12 and vy>1e-12 else 0.
def close(a,b):return math.isclose(a,b,rel_tol=1e-7,abs_tol=2e-8)
def verify(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED;d=json.loads(raw);p=d['protocol'];assert d['schema']=='shared-latent-population-result-v1' and d['status']=='completed';assert p['script_sha256']=='cdef42fd5f4f45d7b5b37ab01f2b3ba4af22663265b1e1980254a7b44596b210';assert p['runner84aa_sha256']=='846bf4b56e7d6d221a8a5a35eb02675f16bde570ea7e7b7a8e2d822f4c33e879';assert p['selected_model_sha256']=='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0' and p['selected_variant']=='ridge_0175';assert p['shared_units']==p['private_units_each']==6 and p['common_decoder_coefficients']==72 and not p['training_allowed'];assert p['motion_seeds']==[8502,8503] and [x['id'] for x in p['holdouts']]==list(range(451,471))
 rows=d['tests'];assert len(rows)==320 and {(r['test_id'],r['corner_id']) for r in rows}=={(i,c) for i in range(451,471) for c in range(1,17)};assert sum(r['state_unchanged_during_delay'] and r['state_sha256_before_delay']==r['state_sha256_after_delay'] for r in rows)==320
 for bi in (1,2):
  rr=[r for r in rows if r['battery']==bi];reported=d['primary']['batteries'][bi-1];assert len(rr)==160 and reported['battery']==bi
  dual={}
  for axis in AXES:
   vals={name:corr(rr,name,axis) for name in ('shared_observation','private_observation','shuffled','static','closed')}
   for name,value in vals.items():assert close(value,reported['unit_correlations'][name][axis]),(bi,axis,name,value,reported['unit_correlations'][name][axis])
   dual[axis]=vals['shared_observation']>=.20 and vals['shared_observation']>max(vals[x] for x in ('shuffled','static','closed'))
  assert dual==reported['dual_active_units'] and sum(dual.values())==reported['dual_active_count']==6
  total=sum(r['frames'] for r in rr);combined={k:pooled(rr,k) for k in ('shared_observation','private_observation','execution_mode','zero')};combined.update({x:math.sqrt(sum(r['frames']*r['controls'][x]['rmse_rad']**2 for r in rr)/total) for x in ('shuffled','static','closed')});assert all(close(v,reported['combined'][k]) for k,v in combined.items());performance=combined['shared_observation']<=1.02*combined['private_observation'] and combined['shared_observation']<min(combined[k] for k in ('zero','shuffled','static','closed'));assert performance==reported['performance_passed']==True
  rsa=reported['shared_rsa'];assert rsa['permutations']==1000 and rsa['correlation']>=.30 and rsa['correlation']>rsa['shuffled_p95'] and rsa['passed'];assert reported['passed']==(sum(dual.values())>=4 and rsa['passed'] and performance)
 assert d['primary']['batteries_passed']==2 and d['primary']['batteries_required']==2 and d['primary']['passed'];a=d['audit'];assert a['accepted_total']==16384 and a['audited_count']==128 and not a['is_exhaustive'];print('Series85: correlations, controls, performance, state and reported decision are internally consistent. RSA threshold passes as reported, but RSA cannot be independently recomputed because summary lacks motion-level signatures/distances.')
def verify_extract():
 d=json.loads((ROOT/'experiments/reports/shared-latent-population-user-summary-extract.json').read_text(encoding='utf8'));assert d['source_file_sha256']==EXPECTED and d['primary']['passed'];x=d['derived'];assert x['records']==x['distinct_pairs']==x['state_unchanged_and_sha_match']==320;assert not x['rsa_independently_recomputable_from_summary'];assert x['overlap_totals']=={'under_0_001_deg':0,'under_1_deg':0,'under_5_deg':203};print('Persisted series85 extract matches the verified result and records the RSA verification limitation.')
if __name__=='__main__':verify(sys.argv[1]) if len(sys.argv)>1 else verify_extract()
