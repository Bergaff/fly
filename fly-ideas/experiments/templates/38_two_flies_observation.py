#!/usr/bin/env python3
"""Kinematic MuJoCo scene, image-driven toy LIF observer; not a connectome model."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Brian2 uses its NumPy target to avoid compiler load during other experiments.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np
import mujoco
import brian2 as b
from PIL import Image

XML = '''<mujoco model="two_flies_kinematic">
<compiler angle="radian"/><option gravity="0 0 0"/>
<worldbody>
 <body name="observer" pos="0 0 0.4">
  <geom name="observer_body" type="ellipsoid" size="0.65 0.32 0.30" rgba="0.32 0.28 0.22 1"/>
  <geom name="observer_head" type="ellipsoid" pos="0.68 0 0.04" size="0.27 0.29 0.25" rgba="0.4 0.3 0.23 1"/>
  <geom name="observer_eye_left" type="ellipsoid" pos="0.74 0.23 0.09" size="0.18 0.10 0.16" rgba="0.35 0.14 0.10 1"/>
  <geom name="observer_eye_right" type="ellipsoid" pos="0.74 -0.23 0.09" size="0.18 0.10 0.16" rgba="0.35 0.14 0.10 1"/>
  <geom name="observer_left_wing" type="ellipsoid" pos="-0.1 0.75 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>
  <geom name="observer_right_wing" type="ellipsoid" pos="-0.1 -0.75 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>
 </body>
 <body name="demonstrator" pos="4 0 0.4">
  <geom name="demo_body" type="ellipsoid" size="0.65 0.32 0.30" rgba="0.32 0.28 0.22 1"/>
  <geom name="demo_head" type="ellipsoid" pos="-0.68 0 0.04" size="0.27 0.29 0.25" rgba="0.4 0.3 0.23 1"/>
  <geom name="demo_eye_left" type="ellipsoid" pos="-0.74 0.23 0.09" size="0.18 0.10 0.16" rgba="0.35 0.14 0.10 1"/>
  <geom name="demo_eye_right" type="ellipsoid" pos="-0.74 -0.23 0.09" size="0.18 0.10 0.16" rgba="0.35 0.14 0.10 1"/>
  <body name="left_wing" pos="0 0.30 0.18">
   <joint name="left_hinge" type="hinge" axis="1 0 0"/>
   <geom name="demo_left_wing" type="ellipsoid" pos="0 0.65 0" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>
  </body>
  <body name="right_wing" pos="0 -0.30 0.18">
   <joint name="right_hinge" type="hinge" axis="1 0 0"/>
   <geom name="demo_right_wing" type="ellipsoid" pos="0 -0.65 0" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>
  </body>
 </body>
</worldbody></mujoco>'''

CONDITIONS = ('moving', 'stationary', 'occluded', 'shuffled')


def write_csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def camera(origin, target, width, height, fov=65):
    origin = np.array(origin, dtype=float)
    forward = np.array(target, dtype=float) - origin
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    y, x = np.mgrid[0:height, 0:width]
    scale = math.tan(math.radians(fov / 2))
    u = (2 * (x + .5) / width - 1) * scale
    v = (1 - 2 * (y + .5) / height) * scale * height / width
    rays = forward + u[..., None] * right + v[..., None] * up
    rays /= np.linalg.norm(rays, axis=2, keepdims=True)
    return origin, rays


def render(model, data, cam, exclude_observer=False):
    """Ray/ellipsoid intersections using MuJoCo's actual world geometry transforms."""
    origin, rays = cam
    h, w = rays.shape[:2]
    rgb = np.empty((h, w, 3), dtype=float)
    rgb[:] = [0.69, 0.70, 0.66]
    nearest = np.full((h, w), np.inf)
    ground = np.divide(-origin[2], rays[..., 2], out=np.full((h, w), np.inf), where=rays[..., 2] < -1e-9)
    ground = np.where(ground > 0, ground, np.inf)
    rgb[ground < nearest] = [0.48, 0.47, 0.40]
    nearest = ground
    for i in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, i)
        if exclude_observer and name.startswith('observer_'):
            continue
        rot = data.geom_xmat[i].reshape(3, 3)
        center = data.geom_xpos[i]
        size = model.geom_size[i]
        o = ((origin - center) @ rot) / size
        d = (rays @ rot) / size
        a = np.sum(d * d, axis=2)
        half_b = np.sum(d * o, axis=2)
        discriminant = half_b * half_b - a * (np.dot(o, o) - 1)
        t = (-half_b - np.sqrt(np.maximum(discriminant, 0))) / a
        hit = (discriminant >= 0) & (t > 0) & (t < nearest)
        if np.any(hit):
            local = (o + t[..., None] * d) / size
            normal = local @ rot.T
            normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-12)
            light = np.array([-0.35, -0.4, 0.85]); light /= np.linalg.norm(light)
            shade = .4 + .6 * np.clip(normal @ light, 0, 1)
            color = model.geom_rgba[i, :3]
            rgb[hit] = (shade[..., None] * color)[hit]
            nearest[hit] = t[hit]
    return np.uint8(np.clip(rgb * 255, 0, 255))


def features(frames):
    # Four by four image tiles per eye. No scene state or action is passed here.
    luminance = frames.astype(np.float32).mean(axis=-1) / 255.
    delta = np.abs(np.diff(luminance, axis=0, prepend=luminance[:1]))
    n, eyes, h, w = delta.shape
    return delta.reshape(n, eyes, 4, h // 4, 4, w // 4).mean(axis=(3, 5)).reshape(n, 32)


def simulate(values, frame_dt, seed):
    b.start_scope()
    b.seed(seed)
    b.prefs.codegen.target = 'numpy'
    clock = b.Clock(dt=1 * b.ms)
    # Engineered motion detectors, not LC cells or fitted biological parameters.
    drive = 1.02 + np.clip(values * 25., 0, 3.)
    timed = b.TimedArray(drive, dt=frame_dt * b.second)
    group = b.NeuronGroup(32, 'dv/dt = (-v + timed(t, i))/(20*ms) : 1 (unless refractory)',
                          threshold='v > 1', reset='v = 0', refractory=4*b.ms,
                          method='euler', clock=clock, namespace={'timed': timed})
    # Identical initial phases across controls; no transfer from demonstrator.
    group.v = np.random.default_rng(seed).uniform(0., .8, 32)
    spikes = b.SpikeMonitor(group, record=True)
    b.Network(group, spikes).run(len(values) * frame_dt * b.second)
    return np.asarray(spikes.t / b.second), np.asarray(spikes.i), drive


def run(output_root, duration, fps, seed, width=96, height=64):
    if duration <= 0 or duration > 10 or fps not in (10, 20, 25, 50):
        raise ValueError('duration must be in (0, 10] and fps must be 10, 20, 25, or 50')
    count = round(duration * fps)
    if count < 2 or abs(count / fps - duration) > 1e-9:
        raise ValueError('duration must contain an integer number of frames, at least two')
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / ('two_flies_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    run_dir.mkdir()
    meta = dict(status='running', created_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
                duration_s=duration, fps=fps, sample_times_s='k / fps',
                model='MuJoCo kinematic ellipsoids, manually controlled wings; ray-cast cameras; 32 toy LIF neurons',
                biological_claim='No FlyWire, FlyGym, trained brain, real eye model, biomechanics, learning or mirror-neuron evidence.',
                wing_hz=3.0, wing_amplitude_rad=0.65, visual_shape=[2, height, width, 3],
                integration_dt_ms=1, eye_fov_deg=65, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                python=platform.python_version(), versions={p: importlib.metadata.version(p) for p in ['numpy', 'mujoco', 'brian2', 'pillow']},
                conditions={'moving':'wings move', 'stationary':'wings held at zero',
                            'occluded':'moving scene, eye input replaced with constant gray',
                            'shuffled':'moving scene, frame order permuted only for neuronal input'},
                note='All conditions share initial neuron phases. No random input. GIFs are visualizations; NPZ contains exact RGB.' )
    (run_dir / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    (run_dir / 'scene.xml').write_text(XML, encoding='utf-8')
    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)
    left = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'left_hinge')]
    right = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'right_hinge')]
    eye_cams = [camera([.85, y, .46], [4, 0, .55], width, height) for y in (.13, -.13)]
    overview = camera([6, -9, 5], [2, 0, .4], 240, 160, 55)
    all_frames = {}
    for condition in ('moving', 'stationary'):
        eyes, outside, scene = [], [], []
        for k in range(count):
            t = k / fps
            angle = .65 * math.sin(2 * math.pi * 3 * t) if condition == 'moving' else 0.
            data.qpos[left], data.qpos[right] = angle, -angle
            mujoco.mj_forward(model, data)
            eyes.append(np.stack([render(model, data, cam, True) for cam in eye_cams]))
            outside.append(render(model, data, overview))
            scene.append((k, t, float(data.qpos[left]), float(data.qpos[right]), 0, 0, .4, 4, 0, .4))
        all_frames[condition] = (np.stack(eyes), outside, scene)
    permutation = np.random.default_rng(seed + 1).permutation(count)
    write_csv(run_dir / 'neuron_map.csv', ['neuron_id', 'eye', 'tile_row', 'tile_col', 'model'],
              [(i, 'left' if i < 16 else 'right', (i % 16) // 4, i % 4, 'toy_LIF_motion') for i in range(32)])
    for condition in CONDITIONS:
        dest = run_dir / condition
        dest.mkdir()
        scene_key = 'stationary' if condition == 'stationary' else 'moving'
        eye_frames, outside, scene = all_frames[scene_key]
        indices = permutation if condition == 'shuffled' else np.arange(count)
        input_frames = eye_frames[indices].copy()
        if condition == 'occluded': input_frames[:] = 128
        values = features(input_frames)
        times, ids, drives = simulate(values, 1 / fps, seed)
        np.savez_compressed(dest / 'vision.npz', scene_eyes=eye_frames, neural_input=input_frames, input_source_frame=indices)
        write_csv(dest / 'scene.csv', ['frame', 'time_s', 'left_wing_rad', 'right_wing_rad', 'observer_x', 'observer_y', 'observer_z', 'demo_x', 'demo_y', 'demo_z'], scene)
        write_csv(dest / 'visual_input.csv', ['frame', 'time_s', 'neuron_id', 'motion_abs_diff', 'drive'],
                  ((k, k / fps, i, float(values[k, i]), float(drives[k, i])) for k in range(count) for i in range(32)))
        write_csv(dest / 'spikes.csv', ['time_s', 'neuron_id'], zip(times.tolist(), ids.tolist()))
        def gif(images, path):
            ims = [Image.fromarray(a) for a in images]
            ims[0].save(path, save_all=True, append_images=ims[1:], duration=round(1000 / fps), loop=0, optimize=False)
        gif(outside, dest / 'scene.gif')
        gif([np.concatenate((fr[0], fr[1]), axis=1) for fr in input_frames], dest / 'observer_input.gif')
        (dest / 'summary.json').write_text(json.dumps({'condition':condition, 'spikes':len(times),
            'mean_motion':float(values.mean()), 'frames':count, 'neural_input':'neural_input in vision.npz'}, indent=2), encoding='utf-8')
        print(condition, 'spikes=',len(times), 'mean_motion=',round(float(values.mean()), 5), flush=True)
    meta['status'] = 'completed'
    (run_dir / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RESULT_DIR=' + str(run_dir.resolve()), flush=True)
    return run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=os.environ.get('FLY_RUN_DIR', 'workspace/two-flies'))
    parser.add_argument('--duration', type=float, default=2.)
    parser.add_argument('--fps', type=int, default=20)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    run(args.output, args.duration, args.fps, args.seed)

if __name__ == '__main__':
    main()
