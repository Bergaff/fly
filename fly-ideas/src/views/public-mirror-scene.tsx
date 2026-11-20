import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type MirrorPose = {
  forelegLeft: number;
  forelegRight: number;
  headYaw: number;
  headPitch: number;
  reach: number;
  bodyShift: number;
};

const ZERO_POSE: MirrorPose = { forelegLeft: 0, forelegRight: 0, headYaw: 0, headPitch: 0, reach: 0, bodyShift: 0 };

function cylinder(a: THREE.Vector3, b: THREE.Vector3, material: THREE.Material, radius = .024) {
  const delta = b.clone().sub(a);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius * .75, radius, delta.length(), 7), material);
  mesh.position.copy(a).add(b).multiplyScalar(.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.normalize());
  return mesh;
}

function makeArticulatedFly() {
  const root = new THREE.Group();
  const shell = new THREE.MeshStandardMaterial({ color: 0x76634d, roughness: .9 });
  const abdomenMat = new THREE.MeshStandardMaterial({ color: 0x8b775b, roughness: .94 });
  const eye = new THREE.MeshStandardMaterial({ color: 0x704235, roughness: .86 });
  const limb = new THREE.MeshStandardMaterial({ color: 0x403b32, roughness: 1 });
  const wingMat = new THREE.MeshStandardMaterial({ color: 0x9da69d, transparent: true, opacity: .55, side: THREE.DoubleSide, depthWrite: false, roughness: .9 });
  const ellipsoid = (parent: THREE.Object3D, position: [number, number, number], scale: [number, number, number], material: THREE.Material) => {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 14), material);
    mesh.position.set(...position); mesh.scale.set(...scale); parent.add(mesh); return mesh;
  };
  ellipsoid(root, [.35, 0, .04], [.7, .3, .28], abdomenMat);
  ellipsoid(root, [-.28, 0, .08], [.4, .34, .31], shell);
  const head = new THREE.Group(); head.position.set(-.7, 0, .1); root.add(head);
  ellipsoid(head, [0, 0, 0], [.27, .25, .24], shell);
  ellipsoid(head, [-.05, .2, .05], [.18, .13, .17], eye);
  ellipsoid(head, [-.05, -.2, .05], [.18, .13, .17], eye);

  const forelegs: THREE.Group[] = [];
  for (const side of [-1, 1]) {
    const fore = new THREE.Group(); fore.position.set(-.48, side * .22, -.06); root.add(fore); forelegs.push(fore);
    fore.add(cylinder(new THREE.Vector3(0, 0, 0), new THREE.Vector3(-.18, side * .27, -.22), limb));
    fore.add(cylinder(new THREE.Vector3(-.18, side * .27, -.22), new THREE.Vector3(-.43, side * .4, -.1), limb, .02));
    fore.add(cylinder(new THREE.Vector3(-.43, side * .4, -.1), new THREE.Vector3(-.6, side * .47, .04), limb, .017));
    for (let j = 1; j < 3; j++) {
      const x = -.25 + j * .34;
      root.add(cylinder(new THREE.Vector3(x, side * .22, -.08), new THREE.Vector3(x + .1, side * .52, -.35), limb));
      root.add(cylinder(new THREE.Vector3(x + .1, side * .52, -.35), new THREE.Vector3(x + (j - 1.5) * .25, side * .8, -.58), limb, .02));
    }
    const wing = new THREE.Mesh(new THREE.PlaneGeometry(1.2, .48), wingMat);
    wing.position.set(.02, side * .52, .28); wing.rotation.set(.08, 0, side * .18); root.add(wing);
  }
  return { root, head, forelegs };
}

function applyPose(fly: ReturnType<typeof makeArticulatedFly>, pose: MirrorPose) {
  fly.root.position.x = Number(fly.root.userData.baseX || 0) + pose.bodyShift * .28;
  fly.head.rotation.z = pose.headYaw * .65;
  fly.head.rotation.y = pose.headPitch * .5;
  fly.forelegs[0].rotation.set(-pose.reach * .45, pose.forelegLeft * .8, pose.forelegLeft * .55);
  fly.forelegs[1].rotation.set(-pose.reach * .45, -pose.forelegRight * .8, -pose.forelegRight * .55);
}

export function PublicMirrorScene({ teacher = ZERO_POSE, observer = ZERO_POSE, teacherVisible = true, phase }: { teacher?: MirrorPose; observer?: MirrorPose; teacherVisible?: boolean; phase: string }) {
  const host = useRef<HTMLDivElement>(null);
  const sceneState = useRef<{ teacher: ReturnType<typeof makeArticulatedFly>; observer: ReturnType<typeof makeArticulatedFly>; draw: () => void } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!host.current) return;
    const el = host.current;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false }); }
    catch { setError("WebGL недоступен. Интерактивные данные ниже всё равно работают."); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setClearColor(0x25231f); el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, .1, 100); camera.position.set(4.4, 6.5, 10.5);
    const controls = new OrbitControls(camera, renderer.domElement); controls.target.set(0, 0, 0); controls.enableDamping = false; controls.minDistance = 5; controls.maxDistance = 18; controls.update();
    scene.add(new THREE.HemisphereLight(0xe4dece, 0x57534a, 2.2));
    const key = new THREE.DirectionalLight(0xd7c6a5, 2.6); key.position.set(-4, 7, 6); scene.add(key);
    const world = new THREE.Group(); world.rotation.x = -Math.PI / 2; scene.add(world);
    const a = makeArticulatedFly(), b = makeArticulatedFly(); a.root.userData.baseX = 2.1; b.root.userData.baseX = -2.1; a.root.position.x = 2.1; b.root.position.x = -2.1; b.root.rotation.z = Math.PI; world.add(a.root, b.root);
    const ground = new THREE.GridHelper(8, 16, 0x555147, 0x393731); ground.rotation.x = Math.PI / 2; ground.position.z = -.68; world.add(ground);
    const draw = () => renderer.render(scene, camera);
    const resize = () => { const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); draw(); };
    const observerSize = new ResizeObserver(resize); observerSize.observe(el); controls.addEventListener("change", draw); sceneState.current = { teacher: a, observer: b, draw }; resize();
    return () => { sceneState.current = null; observerSize.disconnect(); controls.removeEventListener("change", draw); controls.dispose(); scene.traverse(object => { if (object instanceof THREE.Mesh || object instanceof THREE.Line) { object.geometry.dispose(); const materials = Array.isArray(object.material) ? object.material : [object.material]; materials.forEach(m => m.dispose()); } }); renderer.dispose(); renderer.domElement.remove(); };
  }, []);
  useEffect(() => {
    const current = sceneState.current; if (!current) return;
    current.teacher.root.visible = teacherVisible; applyPose(current.teacher, teacher); applyPose(current.observer, observer); current.draw();
  }, [teacher, observer, teacherVisible]);
  return <div className="relative h-[360px] w-full overflow-hidden border md:h-[520px]" ref={host} aria-label="Интерактивная схема двух мух">
    <div className="pointer-events-none absolute left-3 top-3 z-10 border bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-[.12em]">{phase}</div>
    {error && <p className="p-4 text-sm">{error}</p>}
  </div>;
}
