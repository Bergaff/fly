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
  wingLeft: number;
  wingRight: number;
};

const ZERO_POSE: MirrorPose = { forelegLeft: 0, forelegRight: 0, headYaw: 0, headPitch: 0, reach: 0, bodyShift: 0, wingLeft: 0, wingRight: 0 };

function cylinder(a: THREE.Vector3, b: THREE.Vector3, material: THREE.Material, radius = .024) {
  const delta = b.clone().sub(a);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius * .75, radius, delta.length(), 7), material);
  mesh.position.copy(a).add(b).multiplyScalar(.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.normalize());
  return mesh;
}

function makeArticulatedFly() {
  const root = new THREE.Group();
  const shell = new THREE.MeshStandardMaterial({ color: 0x6f5a3f, roughness: .72, metalness: .03 });
  const abdomenMat = new THREE.MeshStandardMaterial({ color: 0x9a8056, roughness: .8 });
  const stripeMat = new THREE.MeshStandardMaterial({ color: 0x3b3025, roughness: .9 });
  const eye = new THREE.MeshStandardMaterial({ color: 0x6e241d, roughness: .45, metalness: .08 });
  const limb = new THREE.MeshStandardMaterial({ color: 0x302a22, roughness: .9 });
  const wingMat = new THREE.MeshPhysicalMaterial({ color: 0xb6c5c2, transparent: true, opacity: .42, side: THREE.DoubleSide, depthWrite: false, roughness: .35, transmission: .08 });
  const veinMat = new THREE.LineBasicMaterial({ color: 0x5e6863, transparent: true, opacity: .65 });
  const ellipsoid = (parent: THREE.Object3D, position: [number, number, number], scale: [number, number, number], material: THREE.Material) => {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 20), material);
    mesh.position.set(...position); mesh.scale.set(...scale); parent.add(mesh); return mesh;
  };
  ellipsoid(root, [.38, 0, .04], [.76, .31, .29], abdomenMat);
  for (const x of [.05,.28,.51,.73]) { const ring = new THREE.Mesh(new THREE.TorusGeometry(.275, .018, 8, 32), stripeMat); ring.position.set(x, 0, .04); ring.rotation.y = Math.PI / 2; ring.scale.z = .9; root.add(ring); }
  ellipsoid(root, [-.28, 0, .08], [.42, .36, .33], shell);
  ellipsoid(root, [-.3, 0, .28], [.24, .22, .08], stripeMat);
  const head = new THREE.Group(); head.position.set(-.7, 0, .1); root.add(head);
  ellipsoid(head, [0, 0, 0], [.27, .25, .24], shell);
  ellipsoid(head, [-.05, .2, .05], [.19, .135, .18], eye);
  ellipsoid(head, [-.05, -.2, .05], [.19, .135, .18], eye);
  for (const side of [-1, 1]) {
    const base = new THREE.Vector3(-.16, side * .1, .12), tip = new THREE.Vector3(-.38, side * .18, .28);
    head.add(cylinder(base, tip, limb, .012));
    ellipsoid(head, [tip.x, tip.y, tip.z], [.035,.035,.035], limb);
  }
  for (const y of [-.065,0,.065]) ellipsoid(head, [-.22, y, .19], [.025,.025,.018], eye);

  const forelegs: THREE.Group[] = [];
  const wings: THREE.Group[] = [];
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
    const wing = new THREE.Group(); wing.position.set(.02, side * .31, .28); wing.userData.side = side; root.add(wing); wings.push(wing);
    const shape = new THREE.Shape(); shape.moveTo(0,0); shape.bezierCurveTo(.28,side*.36,.92,side*.38,1.2,side*.12); shape.bezierCurveTo(.98,side*-.08,.34,side*-.16,0,0);
    const surface = new THREE.Mesh(new THREE.ShapeGeometry(shape, 18), wingMat); wing.add(surface);
    for (const offset of [-.08,.02,.12]) { const points = [new THREE.Vector3(.05,0,.004),new THREE.Vector3(.48,side*(offset+.08),.004),new THREE.Vector3(1.02,side*(offset+.12),.004)]; wing.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), veinMat)); }
  }
  return { root, head, forelegs, wings };
}

function applyPose(fly: ReturnType<typeof makeArticulatedFly>, pose: MirrorPose) {
  fly.root.position.x = Number(fly.root.userData.baseX || 0) + pose.bodyShift * .28;
  fly.head.rotation.z = pose.headYaw * .65;
  fly.head.rotation.y = pose.headPitch * .5;
  fly.forelegs[0].rotation.set(-pose.reach * .45, pose.forelegLeft * .8, pose.forelegLeft * .55);
  fly.forelegs[1].rotation.set(-pose.reach * .45, -pose.forelegRight * .8, -pose.forelegRight * .55);
  fly.wings.forEach((wing, index) => { const side = Number(wing.userData.side); const stroke = index === 0 ? pose.wingLeft : pose.wingRight; wing.rotation.set(.08 + Math.abs(stroke) * .22, stroke * .85, side * (.18 + stroke * .42), "XYZ"); });
}

export function PublicMirrorScene({ teacher = ZERO_POSE, observer = ZERO_POSE, teacherVisible = true, phase }: { teacher?: MirrorPose; observer?: MirrorPose; teacherVisible?: boolean; phase: string }) {
  const host = useRef<HTMLDivElement>(null);
  const sceneState = useRef<{ teacher: ReturnType<typeof makeArticulatedFly>; observer: ReturnType<typeof makeArticulatedFly>; draw: () => void; resetView: () => void } | null>(null);
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
    const resetView = () => { camera.position.set(4.4, 6.5, 10.5); camera.up.set(0, 1, 0); controls.target.set(0, 0, 0); controls.update(); draw(); };
    const resize = () => { const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); draw(); };
    const observerSize = new ResizeObserver(resize); observerSize.observe(el); controls.addEventListener("change", draw); sceneState.current = { teacher: a, observer: b, draw, resetView }; resize();
    return () => { sceneState.current = null; observerSize.disconnect(); controls.removeEventListener("change", draw); controls.dispose(); scene.traverse(object => { if (object instanceof THREE.Mesh || object instanceof THREE.Line) { object.geometry.dispose(); const materials = Array.isArray(object.material) ? object.material : [object.material]; materials.forEach(m => m.dispose()); } }); renderer.dispose(); renderer.domElement.remove(); };
  }, []);
  useEffect(() => {
    const current = sceneState.current; if (!current) return;
    current.teacher.root.visible = teacherVisible; applyPose(current.teacher, teacher); applyPose(current.observer, observer); current.draw();
  }, [teacher, observer, teacherVisible]);
  return <div className="relative h-[360px] w-full overflow-hidden border md:h-[520px]" ref={host} aria-label="Интерактивная схема двух мух">
    <div className="pointer-events-none absolute left-3 top-3 z-10 border bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-[.12em]">{phase}</div>
    <button type="button" className="absolute right-3 top-3 z-10 border bg-background/90 px-2 py-1 text-[10px] hover:bg-secondary" onClick={() => sceneState.current?.resetView()}>Исходный вид</button>
    {error && <p className="p-4 text-sm">{error}</p>}
  </div>;
}
