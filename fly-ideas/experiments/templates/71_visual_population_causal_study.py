#!/usr/bin/env python3
"""Series 71: preregistration and audited FlyVis population capture.

The script does not invent FlyVis→FlyWire mappings. It freezes a causal lesion plan,
can record central output-cell activity from an official pretrained FlyVis network,
and creates exact-name mapping candidates that remain blocked until human review.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, platform, subprocess, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path
import importlib.util

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

def load_local(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def discover_series69():
 root=Path("workspace/runs/ideas/i-observational/matched-encoder-ablation")
 found=[]
 for result in root.glob("*/result"):
  if all((result/f"holdout_{i:03d}"/"metrics.json").is_file() for i in range(1,6)) and all((result.parent/"input"/f"holdout_{i:03d}.json").is_file() for i in range(1,6)):found.append(result.parent)
 if not found:raise ValueError("Не найден полный запуск серии 69 с папками input и result.")
 return max(found,key=lambda p:p.stat().st_mtime_ns)

def prepare_movies(out,series69=None):
 import numpy as np
 here=Path(__file__).resolve().parent;studio=load_local("causal_studio",here/"50_two_flies_wing_studio_pilot.py");engine=load_local("causal_engine",here/"38_two_flies_observation.py");scene=studio.Scene(engine)
 run=Path(series69).resolve() if series69 else discover_series69().resolve()
 if run.name=="result":run=run.parent
 if run.name.startswith("holdout_"):run=run.parent.parent
 prepared=[]
 for i in range(1,6):
  source=run/"input"/f"holdout_{i:03d}.json"
  if not source.is_file():raise ValueError(f"Не найден {source}")
  raw=source.read_bytes();obj=json.loads(raw.decode("utf-8-sig"));times,angles=studio.sample(obj);rgb=scene.render(angles)
  if rgb.shape!=(len(times),2,32,48,3) or rgb.dtype.name!="uint8":raise ValueError("Renderer вернул неожиданный RGB формат.")
  target=out/f"rgb_holdout_{50+i:03d}.npy";np.save(target,rgb,allow_pickle=False);prepared.append({"movement":50+i,"file":target.name,"sha256":digest(target),"shape":list(rgb.shape),"source_sha256":hashlib.sha256(raw).hexdigest()})
 manifest={"schema":"series71-retinal-source-v1","series69":str(run),"scientific_result":False,"files":prepared,"note":"RGB двух камер перерендерен из пяти frozen holdout серии 69; следующий этап переводит его в hexal input официальным BoxEye FlyVis."};atomic_json(out/"retinal_sources.json",manifest)
 ROOT.mkdir(parents=True,exist_ok=True);(ROOT/"latest_prepared.txt").write_text(str(out.resolve()),encoding="utf8");return manifest

def install_datamate_h5_workaround():
 """Avoid datamate 1.0 reopening then unlinking its own HDF5 file on Windows."""
 if os.name!="nt":return False
 import h5py, numpy as np
 import datamate.directory as directory_module
 import datamate.io as io_module
 def safe_write(path,val):
  path=Path(path);array=np.asarray(val)
  if path.is_file():
   # A datamate Directory name already encodes its config. Reusing a valid cache
   # is required here: regenerated set ordering can differ between Python
   # processes and must not make datamate truncate its own open Windows file.
   try:
    with h5py.File(path,"r",libver="latest",swmr=True) as f:
     if "data" in f and f["data"].shape==array.shape and f["data"].dtype==array.dtype:return
   except Exception:pass
  # datamate 1.0's writer is broken even for a new Windows path: it opens
  # mode='w', immediately reads the not-yet-created dataset, then tries to
  # unlink the still-open file. Always use a closed temporary file instead.
  path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f".{os.getpid()}.repair")
  try:
   if tmp.exists():tmp.unlink()
   with h5py.File(tmp,"w",libver="latest") as f:
    f["data"]=array;f.swmr_mode=True;f.flush()
   os.replace(tmp,path)
  finally:
   if tmp.exists():tmp.unlink()
 directory_module._write_h5=safe_write;io_module._write_h5=safe_write
 return True

def capture_flyvis(movie_path:Path,out,dt:float,model:str):
 import numpy as np
 workaround=install_datamate_h5_workaround()
 import flyvis
 movie=np.load(movie_path,allow_pickle=False)
 if movie.ndim==5:
  if movie.shape[1]!=2 or movie.shape[-1]!=3:raise ValueError("RGB movie must have shape (frames, 2, height, width, 3).")
  import torch
  from flyvis.datasets.rendering import BoxEye
  gray=movie.astype(np.float32).mean(axis=-1)/255
  eye=BoxEye(extent=15,kernel_size=13);movie=np.stack([eye(torch.tensor(gray[:,i][None])).detach().cpu().numpy()[0,:,0] for i in range(2)])
 if movie.ndim==2:movie=movie[None,:,:]
 if movie.ndim!=3 or movie.shape[0] not in (1,2):raise ValueError("Movie must have shape (eyes, frames, hexals), or RGB (frames, 2, height, width, 3).")
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
  "flyvis_version":getattr(flyvis,"__version__","unknown"),"model":model,"dt_s":dt,"windows_datamate_h5_workaround":workaround,"output_types":types,"primary_types_present":all(x in types for x in PRIMARY),"activity_sha256":digest(out/"flyvis_activity.csv"),
  "note":"PRETRAINED FlyVis activity; not yet mapped to FlyWire or passed through Shiu."}
 atomic_json(out/"flyvis_manifest.json",meta);return meta

def batch_flyvis(prepared:Path,dt:float,model:str):
 """Run every movie in a fresh process so FlyVis/datamate closes its HDF5 handles."""
 manifest=json.loads((prepared/"retinal_sources.json").read_text(encoding="utf8"));results=[]
 for item in manifest.get("files",[]):
  movement=int(item["movement"]);target=prepared/f"flyvis_{movement:03d}";target.mkdir(exist_ok=True);summary=target/"summary.json";fm=target/"flyvis_manifest.json";activity=target/"flyvis_activity.csv"
  if summary.is_file() and fm.is_file() and activity.is_file():
   old=json.loads(summary.read_text(encoding="utf8"));meta=json.loads(fm.read_text(encoding="utf8"))
   if old.get("status")=="completed" and meta.get("activity_sha256")==digest(activity):
    results.append({"movement":movement,"folder":target.name,"activity_sha256":meta["activity_sha256"]});print(f"FlyVis: движение {movement} уже готово, SHA проверен.",flush=True);continue
  command=[sys.executable,str(Path(__file__).resolve()),"--stage","flyvis","--movie",str((prepared/item["file"]).resolve()),"--output",str(target.resolve()),"--dt",str(dt),"--model",model]
  error=""
  for attempt in range(1,4):
   proc=subprocess.run(command,env=os.environ.copy())
   data=json.loads(summary.read_text(encoding="utf8")) if summary.is_file() else {}
   if proc.returncode==0 and data.get("status")=="completed":break
   error=str(data.get("error") or f"child exit {proc.returncode}");detail=str(data.get("traceback") or error)
   print("\nДиагностика дочернего FlyVis:\n"+"\n".join(detail.splitlines()[-18:]),flush=True)
   if "PermissionError" not in detail and "WinError 32" not in detail:raise RuntimeError(f"FlyVis movement {movement}: {error}")
   print(f"FlyVis: инициализация HDF5 не завершилась, попытка {attempt}/3; жду перед повтором...",flush=True);time.sleep(3*attempt)
  else:raise RuntimeError(f"FlyVis movement {movement}: {error}; traceback printed above")
  meta=json.loads((target/"flyvis_manifest.json").read_text(encoding="utf8"));results.append({"movement":movement,"folder":target.name,"activity_sha256":meta["activity_sha256"]});print(f"FlyVis: движение {movement}, готово; отдельный процесс закрыт.",flush=True)
 report={"schema":"series71-flyvis-batch-v1","scientific_result":False,"movements":results,"mapping_reviewed":False,"process_isolation":"one FlyVis process per movement to release datamate HDF5 handles"};atomic_json(prepared/"flyvis_batch.json",report);return report

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
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--stage",choices=["protocol","prepare","flyvis","batch-flyvis","mapping","validate"],default="protocol");ap.add_argument("--output");ap.add_argument("--series69");ap.add_argument("--prepared");ap.add_argument("--movie");ap.add_argument("--activity");ap.add_argument("--neurons");ap.add_argument("--mapping");ap.add_argument("--dt",type=float,default=0.04);ap.add_argument("--model",default="flow/0000/000");a=ap.parse_args()
 out=output_dir(a.output);out.mkdir(parents=True,exist_ok=True);result={"stage":a.stage,"scientific_result":False}
 try:
  write_protocol(out)
  if a.stage=="prepare":result["retinal_sources"]=prepare_movies(out,a.series69)
  elif a.stage=="flyvis":
   if not a.movie:raise ValueError("--movie is required")
   result["flyvis"]=capture_flyvis(Path(a.movie),out,a.dt,a.model)
  elif a.stage=="batch-flyvis":
   prepared=Path(a.prepared or out);result["flyvis_batch"]=batch_flyvis(prepared,a.dt,a.model)
  elif a.stage=="mapping":
   if not a.activity or not a.neurons:raise ValueError("--activity and --neurons are required")
   result["mapping_candidates"]=mapping_candidates(Path(a.activity),Path(a.neurons),out)
  elif a.stage=="validate":
   if not a.mapping:raise ValueError("--mapping is required")
   result["mapping_gate"]=validate_mapping(Path(a.mapping),out)
  result["status"]="completed";code=0
 except Exception as exc:result.update(status="blocked",error=f"{type(exc).__name__}: {exc}",traceback=traceback.format_exc());code=1
 atomic_json(out/"summary.json",result);print("Серия 71:",result["status"],"\nПапка:",out.resolve());return code
if __name__=="__main__":raise SystemExit(main())
