import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Angles } from "@/lib/wing-trajectory";

// A hand-built visual illustration. The learning renderer uses simpler ellipsoids.
function makeFly() {
  const fly = new THREE.Group();
  const shell = new THREE.MeshStandardMaterial({ color: 0x67523e, roughness: .88 });
  const abdomen = new THREE.MeshStandardMaterial({ color: 0x816b51, roughness: .94 });
  const eye = new THREE.MeshStandardMaterial({ color: 0x673b2c, roughness: .88 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x413a30, roughness: 1 });
  const vein = new THREE.LineBasicMaterial({ color: 0x6c7267, transparent: true, opacity: .68 });
  const membrane = new THREE.MeshStandardMaterial({ color: 0xb0b8aa, side: THREE.DoubleSide, transparent: true, opacity: .69, roughness: .9, depthWrite: false });
  const ellipsoid = (mat: THREE.Material, pos: number[], size: number[]) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), mat); m.position.set(pos[0], pos[1], pos[2]); m.scale.set(size[0], size[1], size[2]); fly.add(m);
  };
  ellipsoid(abdomen, [.38, 0, 0], [.67, .29, .27]);
  ellipsoid(shell, [-.22, 0, .04], [.38, .32, .3]);
  ellipsoid(shell, [-.68, 0, .02], [.25, .25, .23]);
  for (const side of [-1, 1]) {
    ellipsoid(eye, [-.73, side * .21, .08], [.18, .13, .17]);
    const leg = (points: number[][]) => {
      for (let i = 1; i < points.length; i++) {
        const a = new THREE.Vector3(...points[i - 1] as [number, number, number]), b = new THREE.Vector3(...points[i] as [number, number, number]);
        const v = b.clone().sub(a); const m = new THREE.Mesh(new THREE.CylinderGeometry(.018, .026, v.length(), 6), dark); m.position.copy(a.add(b).multiplyScalar(.5)); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v.normalize()); fly.add(m);
      }
    };
    for (let j = 0; j < 3; j++) { const x = -.3 + j * .25; leg([[x, side * .22, -.1], [x + .08, side * .48, -.25], [x + (j - 1) * .2, side * .67, -.61], [x + (j - 1) * .27, side * .8, -.65]]); }
    leg([[-.84, side * .1, .1], [-1.03, side * .19, .22], [-1.15, side * .25, .18]]);
  }
  const wings: THREE.Group[] = [];
  for (const side of [1, -1]) {
    const wing = new THREE.Group(); wing.position.set(-.05, side * .28, .2);
    const shape = new THREE.Shape(); shape.moveTo(0, 0); shape.bezierCurveTo(-.45, side * .35, -.52, side * 1.12, -.15, side * 1.5); shape.bezierCurveTo(.12, side * 1.76, .62, side * 1.2, .56, side * .68); shape.bezierCurveTo(.5, side * .25, .18, side * .06, 0, 0);
    const geometry = new THREE.ShapeGeometry(shape, 32); const surface = new THREE.Mesh(geometry, membrane); wing.add(surface);
    const curve = (pts: number[][]) => { const path = new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(p[0], side * p[1], .006))); wing.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.getPoints(32)), vein)); };
    curve([[0,0],[-.2,.45],[-.25,1],[-.15,1.5]]); curve([[0,0],[.05,.55],[.02,1.15],[-.15,1.5]]); curve([[0,0],[.25,.45],[.35,.9],[.18,1.35]]); curve([[-.25,.85],[.02,.9],[.35,.9]]);
    const outline = shape.getPoints(60).map(p => new THREE.Vector3(p.x, p.y, .008)); wing.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(outline), vein));
    fly.add(wing); wings.push(wing);
  }
  return { fly, wings };
}

export function WingScene({ teacher, observer, teacherVisible }: { teacher: Angles; observer: Angles; teacherVisible: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const state = useRef<{ a: ReturnType<typeof makeFly>; b: ReturnType<typeof makeFly>; draw: () => void } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!host.current) return;
    const el = host.current;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false }); } catch { setError("Не удалось открыть 3D. Проверьте поддержку WebGL в системе."); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setClearColor(0xd4d0c4); el.appendChild(renderer.domElement);
    const scene = new THREE.Scene(); const camera = new THREE.PerspectiveCamera(38, 1, .1, 100); camera.position.set(3.8, 5.6, 9.5);
    const controls = new OrbitControls(camera, renderer.domElement); controls.target.set(0, 0, 0); controls.enableDamping = false; controls.minDistance = 4; controls.maxDistance = 22; controls.update();
    scene.add(new THREE.HemisphereLight(0xf0eee1, 0x777269, 2)); const light = new THREE.DirectionalLight(0xf2e7d3, 2); light.position.set(-3, 6, 5); scene.add(light);
    // Three uses y-up; the study coordinate system is z-up.
    const world = new THREE.Group(); world.rotation.x = -Math.PI / 2; scene.add(world);
    const a = makeFly(), b = makeFly(); a.fly.position.x = 2.2; b.fly.position.x = -2.2; b.fly.rotation.z = Math.PI; world.add(a.fly, b.fly);
    const draw = () => renderer.render(scene, camera);
    const resize = () => { const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); draw(); };
    const observerSize = new ResizeObserver(resize); observerSize.observe(el); controls.addEventListener("change", draw); state.current = { a, b, draw }; resize();
    return () => { state.current = null; observerSize.disconnect(); controls.removeEventListener("change", draw); controls.dispose(); scene.traverse(o => { if (o instanceof THREE.Mesh || o instanceof THREE.Line) { o.geometry.dispose(); const materials = Array.isArray(o.material) ? o.material : [o.material]; materials.forEach(m => m.dispose()); } }); renderer.dispose(); renderer.domElement.remove(); };
  }, []);
  useEffect(() => {
    if (!state.current) return;
    const { a, b, draw } = state.current;
    function set(f: ReturnType<typeof makeFly>, values: Angles) { for (let i = 0; i < 2; i++) f.wings[i].rotation.set(...values.slice(i * 3, i * 3 + 3).map(n => n * Math.PI / 180) as [number, number, number], "XYZ"); }
    a.fly.visible = teacherVisible; set(a, teacher); set(b, observer); draw();
  }, [teacher, observer, teacherVisible]);
  return <div ref={host} className="relative h-[340px] w-full overflow-hidden border md:h-[440px]" aria-label="Трёхмерная иллюстрация двух мух. Вращайте сцену мышью.">{error && <p className="p-4 text-sm">{error}</p>}</div>;
}
