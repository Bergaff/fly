#!/usr/bin/env python3
"""Series100: official FlyGym two-body physics preflight.

This is a short technical gate for a new embodied line. It does not load or fit the
old synthetic models and does not claim visual imitation or biological mapping.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,platform,sys,threading,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path

EXPECTED_FLYGYM="2.1.1"
ROOT=Path("workspace/runs/ideas/i-observational/flygym-two-body-preflight")
DURATION_S=.36
TIMESTEP_S=.0005
SAMPLE_EVERY=20
DELAY_S=.08

def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_json(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def manifest(folder):return {str(p.relative_to(folder)).replace("\\","/"):sha256(p) for p in sorted(Path(folder).rglob("*")) if p.is_file() and p.name!="complete.json"}
def finite_tree(value):
 if isinstance(value,dict):return all(finite_tree(v) for v in value.values())
 if isinstance(value,(list,tuple)):return all(finite_tree(v) for v in value)
 if isinstance(value,float):return math.isfinite(value)
 return True

def fixture_result():
 rows=[]
 for step in range(24):
  t=step*.01;demo=.12*math.sin(2*math.pi*3*t);observer=.12*math.sin(2*math.pi*3*max(0,t-DELAY_S))
  rows.append({"time_s":t,"demonstrator_front_response_rad":demo,"observer_front_response_rad":observer,"demonstrator_contact_legs":3,"observer_contact_legs":3,"demonstrator_force_norm":.2+abs(demo),"observer_force_norm":.2+abs(observer),"demonstrator_thorax_z_mm":.7,"observer_thorax_z_mm":.7})
 return rows,{"runtime":"fixture","flygym_version":EXPECTED_FLYGYM,"mujoco_version":"fixture","two_official_bodies":True,"body_names":["demonstrator","observer"],"actuated_dofs_each":42,"physics_steps":480,"sampled_rows":len(rows),"all_finite":True,"demonstrator_command_response_rad":.12,"observer_delayed_response_rad":.12,"nonzero_actuator_force":True,"ground_contact_both":True,"minimum_thorax_z_mm":.7,"maximum_thorax_z_mm":.7}

def real_result(progress):
 import numpy as np
 import flygym,mujoco
 from flygym.anatomy import AxisOrder,JointPreset,ActuatedDOFPreset,Skeleton
 from flygym.compose.fly import NeuroMechFly,ActuatorType
 from flygym.compose.pose import KinematicPosePreset
 from flygym.compose.world import FlatGroundWorld
 from flygym.simulation import Simulation
 from flygym.utils.math import Rotation3D
 version=getattr(flygym,"__version__","unknown")
 if version!=EXPECTED_FLYGYM:raise RuntimeError(f"Нужен FlyGym {EXPECTED_FLYGYM}, найден {version}.")
 progress("Создаются два официальных тела NeuroMechFly…",.08)
 axis=AxisOrder.YAW_PITCH_ROLL;skeleton=Skeleton(axis_order=axis,joint_preset=JointPreset.LEGS_ONLY);pose=KinematicPosePreset.NEUTRAL.get_pose_by_axis_order(axis)
 flies=[]
 for name in ("demonstrator","observer"):
  fly=NeuroMechFly(name=name);fly.add_joints(skeleton,neutral_pose=pose);dofs=fly.skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY);fly.add_actuators(dofs,ActuatorType.POSITION,neutral_input=pose,kp=35);fly.add_leg_adhesion(gain=1.0);flies.append(fly)
 world=FlatGroundWorld(name="two_fly_physics_world")
 world.add_fly(flies[0],[-1.6,0,.7],Rotation3D("quat",[1,0,0,0]))
 world.add_fly(flies[1],[1.6,0,.7],Rotation3D("quat",[0,0,0,1]))
 sim=Simulation(world,timestep=TIMESTEP_S);sim.reset();sim.step()
 progress("MuJoCo-модель собрана. Проверяются приводы, силы и контакты…",.22)
 actuated=[fly.get_actuated_jointdofs_order(ActuatorType.POSITION) for fly in flies];all_dofs=[fly.get_jointdofs_order() for fly in flies]
 if len(actuated[0])==0 or len(actuated[0])!=len(actuated[1]):raise RuntimeError("FlyGym не создал одинаковые leg actuators для двух тел.")
 neutral=np.array([pose.joint_angles_lookup_rad[d.name] for d in actuated[0]],dtype=float)
 front=np.array([i for i,d in enumerate(actuated[0]) if ("-lf_" in d.name or "-rf_" in d.name) and ("coxa" in d.name or "tibia" in d.name)],dtype=int)
 if len(front)<4:raise RuntimeError("Не найдены front-leg actuator DOF.")
 all_front=[[all_dofs[k].index(actuated[k][i]) for i in front] for k in (0,1)]
 thorax_index=[[x.name for x in fly.get_bodysegs_order()].index("c_thorax") for fly in flies]
 steps=round(DURATION_S/TIMESTEP_S);delay_steps=round(DELAY_S/TIMESTEP_S);history=[];rows=[];max_response=[0.,0.];max_force=[0.,0.];contact_seen=[False,False];min_z=[float("inf"),float("inf")];max_z=[-float("inf"),-float("inf")]
 for n in range(steps):
  t=n*TIMESTEP_S;wave=.14*math.sin(2*math.pi*3*t);demo=neutral.copy();demo[front]+=wave*np.where(np.arange(len(front))%2==0,1.,-1.);history.append(demo.copy());obs=history[max(0,n-delay_steps)]
  sim.set_actuator_inputs("demonstrator",ActuatorType.POSITION,demo);sim.set_actuator_inputs("observer",ActuatorType.POSITION,obs);sim.set_leg_adhesion_states("demonstrator",np.ones(6,dtype=bool));sim.set_leg_adhesion_states("observer",np.ones(6,dtype=bool));sim.step()
  if n%SAMPLE_EVERY==0 or n==steps-1:
   record={"time_s":float(sim.time)}
   for k,name in enumerate(("demonstrator","observer")):
    q=sim.get_joint_angles(name);force=sim.get_actuator_forces(name,ActuatorType.POSITION);found,*_=sim.get_ground_contact_info(name);z=float(sim.get_body_positions(name)[thorax_index[k],2]);response=float(np.max(np.abs(q[all_front[k]]-np.array([pose.joint_angles_lookup_rad[all_dofs[k][j].name] for j in all_front[k]]))))
    max_response[k]=max(max_response[k],response);force_norm=float(np.linalg.norm(force));max_force[k]=max(max_force[k],force_norm);contacts=int(np.count_nonzero(found>.5));contact_seen[k]|=contacts>0;min_z[k]=min(min_z[k],z);max_z[k]=max(max_z[k],z);record.update({f"{name}_front_response_rad":response,f"{name}_contact_legs":contacts,f"{name}_force_norm":force_norm,f"{name}_thorax_z_mm":z})
   rows.append(record)
  if n%max(1,steps//8)==0:progress(f"Физика: {n}/{steps} шагов",.22+.68*n/steps)
 metrics={"runtime":"official_flygym","flygym_version":version,"mujoco_version":mujoco.__version__,"two_official_bodies":all(type(x).__name__=="NeuroMechFly" for x in flies),"body_names":[x.name for x in flies],"actuated_dofs_each":len(actuated[0]),"physics_steps":steps,"sampled_rows":len(rows),"all_finite":finite_tree(rows),"demonstrator_command_response_rad":max_response[0],"observer_delayed_response_rad":max_response[1],"nonzero_actuator_force":min(max_force)>1e-6,"maximum_actuator_force_norm":max_force,"ground_contact_both":all(contact_seen),"minimum_thorax_z_mm":min(min_z),"maximum_thorax_z_mm":max(max_z)}
 return rows,metrics

def decision(metrics,fixture=False):
 checks={"exact_flygym_version":metrics["flygym_version"]==EXPECTED_FLYGYM,"two_official_bodies":metrics["two_official_bodies"] and metrics["body_names"]==["demonstrator","observer"],"actuators_present":metrics["actuated_dofs_each"]>=30,"finite_physics":metrics["all_finite"],"demonstrator_responds":metrics["demonstrator_command_response_rad"]>=.015,"observer_responds_after_delay":metrics["observer_delayed_response_rad"]>=.015,"real_actuator_force":metrics["nonzero_actuator_force"],"ground_contact_for_both":metrics["ground_contact_both"],"bodies_remain_supported":metrics["minimum_thorax_z_mm"]>=.15 and metrics["maximum_thorax_z_mm"]<=2.5}
 return {"checks":checks,"passed":all(checks.values()),"scientific_result":False,"next_authorized_step":"frozen89E policy adapter prototype" if all(checks.values()) and not fixture else None}

def run(output_root=ROOT,fixture=False,progress=lambda text,fraction:None):
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);run_dir=root/("flygym_body_"+datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:8]);temp=run_dir/"result_incomplete";temp.mkdir(parents=True)
 protocol={"schema":"flygym-two-body-preflight-v1","line":"new official-body roadmap; not synthetic Stage97","script_sha256":sha256(__file__),"created_utc":datetime.now(timezone.utc).isoformat(),"fixture":fixture,"flygym_version":EXPECTED_FLYGYM,"duration_s":DURATION_S,"timestep_s":TIMESTEP_S,"observer_command_delay_s":DELAY_S,"training_allowed":False,"visual_inference_present":False,"primary_rule":"exact FlyGym2.1.1; two NeuroMechFly bodies; >=30 actuators each; finite response>=0.015rad; nonzero force; contact both; thorax z in[0.15,2.5]mm"};save_json(run_dir/"protocol.json",protocol)
 try:
  rows,metrics=fixture_result() if fixture else real_result(progress);primary=decision(metrics,fixture);headers=list(rows[0]);
  with (temp/"physics_trace.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(rows)
  report={"schema":"flygym-two-body-preflight-result-v1","status":"fixture_completed" if fixture else "completed","protocol":protocol,"platform":platform.platform(),"python":sys.version,"metrics":metrics,"primary":primary,"limitations":["Short technical body/runtime gate, not a scientific observation-to-action result.","Observer receives a delayed diagnostic motor command, not visual input or frozen89E state.","No training, FlyVis, connectome mapping, biological neuron claim, or live-fly claim."]};save_json(temp/"summary.json",report);(temp/"ИТОГ.txt").write_text("СЕРИЯ 100: OFFICIAL FLYGYM TWO-BODY PREFLIGHT\n\nТехнический gate: "+("ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН")+".\nЭто не научный результат наблюдения или биологический вывод.\n",encoding="utf-8-sig");save_json(temp/"complete.json",{"files":manifest(temp)});temp.rename(run_dir/"result");progress("Готово",1.);return run_dir/"result"
 except Exception as exc:
  (run_dir/"ОШИБКА.txt").write_text(type(exc).__name__+": "+str(exc)+"\n\n"+traceback.format_exc(),encoding="utf-8-sig");raise RuntimeError(f"{exc}\nОтчёт: {run_dir/'ОШИБКА.txt'}") from exc

def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title("FlyGym: два физических тела");root.geometry("680x300+180+120");root.attributes("-topmost",True);status=tk.StringVar(value="Короткая проверка официального FlyGym 2.1.1");fraction=tk.DoubleVar(value=0.);tk.Label(root,text="Серия 100: настоящее тело FlyGym",font=("Arial",13,"bold"),pady=16).pack();tk.Label(root,text="Две полные модели NeuroMechFly, MuJoCo-приводы, силы и контакты.\nЭто технический preflight без обучения и без старых synthetic runners.",justify="center").pack();tk.Label(root,textvariable=status,pady=14).pack();tk.Scale(root,variable=fraction,from_=0,to=100,orient="horizontal",length=520,state="disabled",showvalue=True).pack();button=tk.Button(root,text="Запустить короткую проверку",padx=20,pady=7);button.pack(pady=12)
 def update(text,value):root.after(0,lambda:(status.set(text),fraction.set(round(value*100))))
 def work():
  try:
   result=run(progress=update);root.after(0,lambda:(os.startfile(str(result)) if os.name=="nt" else None,messagebox.showinfo("FlyGym","Проверка завершена. Папка результата открыта.",parent=root),button.config(state="normal")))
  except Exception as exc:root.after(0,lambda:(messagebox.showerror("FlyGym: ошибка",str(exc),parent=root),button.config(state="normal")))
 def start():button.config(state="disabled");threading.Thread(target=work,daemon=True).start()
 button.config(command=start);root.mainloop()

def main():
 p=argparse.ArgumentParser();p.add_argument("--gui",action="store_true");p.add_argument("--fixture",action="store_true");p.add_argument("--output-root",default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 else:print(run(a.output_root,a.fixture))
if __name__=="__main__":main()
