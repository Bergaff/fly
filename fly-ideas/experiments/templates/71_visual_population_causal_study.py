#!/usr/bin/env python3
"""Series 71: preregistration and audited FlyVis population capture.

The script does not invent FlyVis→FlyWire mappings. It freezes a causal lesion plan,
can record central output-cell activity from an official pretrained FlyVis network,
and creates exact-name mapping candidates that remain blocked until human review.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, platform, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path("workspace/runs/ideas/i-observational/visual-population-causality")
PRIMARY=["T4a","T4b","T4c","T4d","T5a","T5b","T5c","T5d"]
GROUPS={"T4_all":PRIMARY[:4],"T5_all":PRIMARY[4:],"T4_T5_all":PRIMARY}

def digest(path:Path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest()

def atomic_json(path:Path,value):
 tmp=path.with_suffix(path.suffix+".tmp")
 with tmp.open("w",encoding="utf8") as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def output_dir(value):
 if value:return Path(value)
 ROOT.mkdir(parents=True,exist_ok=True);p=ROOT/("visual_causal_"+datetime.now().strftime("%Y%m%d_%H%M%S"));p.mkdir();return p

def protocol():
 conditions=[{"id":"normal","kind":"normal","targets":[]}]
 conditions += [{"id":"lesion_"+x,"kind":"zero_population","targets":[x]} for x in PRIMARY]
 conditions += [{"id":"lesion_"+k,"kind":"zero_population","targets":v} for k,v in GROUPS.items()]
 conditions += [
  {"id":"temporal_shuffle","kind":"within_population_time_shuffle","targets":PRIMARY},
  {"id":"zero_post_observation_state","kind":"state_control","targets":PRIMARY},
  {"id":"mapping_permutation","kind":"matched_mapping_control","targets":PRIMARY},
 ]
 return {"schema":"visual-population-causal-preregistration-v1","frozen_before_shiu_results":True,
  "question":"Which FlyVis motion populations and reviewed corresponding FlyWire v630 cells are necessary for delayed autonomous replay?",
  "primary_populations":PRIMARY,"population_rationale":"T4/T5 direction-selective motion channels; fixed before Shiu lesion outcomes.",
  "conditions":conditions,"delay_s":0.5,"holdouts":[51,52,53,54,55],"seeds":list(range(10)),
  "primary_endpoint":"change in six-angle replay RMSE relative to normal, radians",
  "secondary_endpoints":["state retention after 0.5 s","six axis RMSE","reviewed DN activity","body trajectory only after preregistered readout"],
  "decision_rule":"A population is necessary only if its preregistered lesion worsens replay RMSE versus paired normal in the same direction across at least 4/5 holdouts and survives the mapping-permutation control.",
  "labels":{"flyvis":"PRETRAINED","shiu":"MEASURED/CONNECTOME","adapter":"TRAINED ADAPTER","body":"HAND-DEFINED CONTROL until readout gate passes"},
  "gates":{"official_flyvis_activity":False,"reviewed_type_to_id_mapping":False,"shiu_lesions_completed":False,"preregistered_motor_readout":False},
  "limitations":["Exact name matches are candidates, not reviewed biological mappings.","T4/T5 necessity in this model would not prove necessity in a living fly.","No motor or body conclusion is allowed before the readout gate passes."]}

def write_protocol(out):
 p=protocol();p["created_utc"]=datetime.now(timezone.utc).isoformat();p["platform"]=platform.platform();atomic_json(out/"preregistration.json",p)
 with (out/"conditions.csv").open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.writer(f);w.writerow(["condition","kind","targets"]);w.writerows((x["id"],x["kind"],"|".join(x["targets"])) for x in p["conditions"])
 return p

def capture_flyvis(movie_path:Path,out,dt:float,model:str):
 import numpy as np
 import flyvis
 from flyvis.utils.activity_utils import LayerActivity
 movie=np.load(movie_path,allow_pickle=False)
 if movie.ndim==2:movie=movie[None,:,:]
 if movie.ndim!=3 or movie.shape[0] not in (1,2):raise ValueError("Movie must have shape (eyes, frames, hexals) with one or two eyes.")
 if movie.shape[1]<2 or not np.isfinite(movie).all() or float(movie.min())<0 or float(movie.max())>1:raise ValueError("Movie must contain at least two finite frames scaled to [0,1].")
 view=flyvis.NetworkView(flyvis.results_dir/model);network=view.init_network();types=network.connectome.output_cell_types[:].astype(str).tolist()
 indices=network.connectome.central_cells_index[:];all_types=network.connectome.unique_cell_types[:].astype(str).tolist();lookup=dict(zip(all_types,map(int,indices)))
 rows=[]
 for eye in range(movie.shape[0]):
  x=np.asarray(movie[eye],dtype=np.float32);state=network.fade_in_state(1.0,dt,x[[0]])
  response=network.simulate(x[None],dt,initial_state=state).detach().cpu().numpy()[0]
  for frame in range(response.shape[0]):
   for typ in types:rows.append((eye,frame,frame*dt,typ,float(response[frame,lookup[typ]])))
 with (out/"flyvis_activity.csv").open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.writer(f);w.writerow(["eye","frame","time_s","flyvis_type","central_activity_au"]);w.writerows(rows)
 meta={"schema":"flyvis-central-activity-v1","created_utc":datetime.now(timezone.utc).isoformat(),"scientific_result":False,
  "source_movie":{"path":str(movie_path.resolve()),"sha256":digest(movie_path),"shape":list(movie.shape),"range":[float(movie.min()),float(movie.max())]},
  "flyvis_version":getattr(flyvis,"__version__","unknown"),"model":model,"dt_s":dt,"output_types":types,"primary_types_present":all(x in types for x in PRIMARY),"activity_sha256":digest(out/"flyvis_activity.csv"),
  "note":"PRETRAINED FlyVis activity; not yet mapped to FlyWire or passed through Shiu."}
 atomic_json(out/"flyvis_manifest.json",meta);return meta

def find_col(names,choices):
 low={x.lower():x for x in names}
 for c in choices:
  if c in low:return low[c]
 return None

def mapping_candidates(activity:Path,neurons:Path,out):
 with activity.open(encoding="utf-8-sig",newline="") as f:types=sorted({r["flyvis_type"].strip() for r in csv.DictReader(f) if r.get("flyvis_type")})
 with neurons.open(encoding="utf-8-sig",newline="") as f:
  reader=csv.DictReader(f);rid=find_col(reader.fieldnames or [],["root_id","rootid","id"]);tc=[x for x in (find_col(reader.fieldnames or [],["cell_type","celltype","type"]),find_col(reader.fieldnames or [],["hemibrain_type"])) if x]
  if not rid or not tc:raise ValueError("Neuron table needs root_id and cell_type/type or hemibrain_type.")
  hits={t:set() for t in types};matched_by={t:set() for t in types}
  for row in reader:
   for col in tc:
    value=(row.get(col) or "").strip()
    if value in hits and (row.get(rid) or "").strip():hits[value].add((row[rid] or "").strip());matched_by[value].add(col)
 with (out/"mapping_candidates.csv").open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.writer(f);w.writerow(["flyvis_type","primary","exact_candidate_count","candidate_flywire_ids","matched_annotation_columns","review_decision","review_note"])
  for t in types:w.writerow([t,t in PRIMARY,len(hits[t]),"|".join(sorted(hits[t],key=lambda x:(len(x),x))),"|".join(sorted(matched_by[t])),"UNREVIEWED",""])
 review={"schema":"flyvis-flywire-v630-mapping-review-v1","reviewed":False,"reviewer":"","reviewed_utc":"","activity_sha256":digest(activity),"neurons_sha256":digest(neurons),
  "candidate_table_sha256":digest(out/"mapping_candidates.csv"),"primary_populations":PRIMARY,"entries":[],
  "instructions":"Review candidates against authoritative annotations. Add one entry per primary population with flyvis_type, flywire_ids, evidence, rate_rule, sign, min_hz, max_hz. Then set reviewed true, reviewer and reviewed_utc. Do not approve by name equality alone."}
 atomic_json(out/"mapping_review.json",review)
 return {"types":len(types),"primary_with_exact_candidates":sum(bool(hits[x]) for x in PRIMARY),"reviewed":False}

def validate_mapping(path:Path,out):
 data=json.loads(path.read_text(encoding="utf8"));errors=[]
 if data.get("schema")!="flyvis-flywire-v630-mapping-review-v1":errors.append("wrong schema")
 if data.get("reviewed") is not True or not str(data.get("reviewer","")).strip() or not str(data.get("reviewed_utc","")).strip():errors.append("review approval is incomplete")
 entries=data.get("entries") if isinstance(data.get("entries"),list) else [];by={x.get("flyvis_type"):x for x in entries if isinstance(x,dict)}
 for typ in PRIMARY:
  x=by.get(typ)
  if not x:errors.append(f"missing {typ}");continue
  ids=x.get("flywire_ids");
  if not isinstance(ids,list) or not ids or any(not isinstance(v,(str,int)) or not str(v).isdigit() for v in ids):errors.append(f"invalid IDs for {typ}")
  if not str(x.get("evidence","")).strip() or not str(x.get("rate_rule","")).strip() or x.get("sign") not in (-1,1) or not all(isinstance(x.get(k),(int,float)) and math.isfinite(x[k]) for k in ("min_hz","max_hz")):errors.append(f"incomplete rule for {typ}")
 result={"schema":"visual-mapping-gate-v1","mapping":str(path.resolve()),"mapping_sha256":digest(path),"passed":not errors,"errors":errors,"conditions_unlocked":[x["id"] for x in protocol()["conditions"]] if not errors else []}
 atomic_json(out/"mapping_gate.json",result)
 if errors:raise ValueError("Mapping gate failed: "+"; ".join(errors))
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--stage",choices=["protocol","flyvis","mapping","validate"],default="protocol");ap.add_argument("--output");ap.add_argument("--movie");ap.add_argument("--activity");ap.add_argument("--neurons");ap.add_argument("--mapping");ap.add_argument("--dt",type=float,default=0.04);ap.add_argument("--model",default="flow/0000/000");a=ap.parse_args()
 out=output_dir(a.output);out.mkdir(parents=True,exist_ok=True);result={"stage":a.stage,"scientific_result":False}
 try:
  write_protocol(out)
  if a.stage=="flyvis":
   if not a.movie:raise ValueError("--movie is required")
   result["flyvis"]=capture_flyvis(Path(a.movie),out,a.dt,a.model)
  elif a.stage=="mapping":
   if not a.activity or not a.neurons:raise ValueError("--activity and --neurons are required")
   result["mapping_candidates"]=mapping_candidates(Path(a.activity),Path(a.neurons),out)
  elif a.stage=="validate":
   if not a.mapping:raise ValueError("--mapping is required")
   result["mapping_gate"]=validate_mapping(Path(a.mapping),out)
  result["status"]="completed";code=0
 except Exception as exc:result.update(status="blocked",error=f"{type(exc).__name__}: {exc}");code=1
 atomic_json(out/"summary.json",result);print("Серия 71:",result["status"],"\nПапка:",out.resolve());return code
if __name__=="__main__":raise SystemExit(main())
