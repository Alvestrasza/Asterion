"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { AnimationAction, Material, Object3D, Texture } from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { AsterionClip } from "@/lib/companion-3d";
import { setCompanionArmorVisible, type CompanionArmorState } from "@/lib/companion-equipment";

export type AsterionView = "hero" | "front" | "side" | "rear";

type Runtime = {
  play: (clip: AsterionClip) => void;
  setView: (view: AsterionView) => void;
  setArmorVisible: (visible: boolean) => void;
  dispose: () => void;
};

type LoadPhase = "fallback" | "loading" | "ready";

const LOOPING_CLIPS = new Set<AsterionClip>(["idle", "sleep", "walk"]);
const VIEW_DIRECTIONS: Record<AsterionView, [number, number, number]> = {
  hero: [0.8, 0.3, 1.2],
  front: [0, 0.1, 1],
  side: [1, 0.1, 0],
  rear: [0, 0.1, -1]
};

function disposeModel(root: Object3D) {
  root.traverse((child) => {
    const mesh = child as Object3D & {
      geometry?: { dispose: () => void };
      material?: Material | Material[];
    };
    mesh.geometry?.dispose();
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    for (const material of materials) {
      for (const value of Object.values(material)) {
        const texture = value as Texture | undefined;
        if (texture?.isTexture) texture.dispose();
      }
      material.dispose();
    }
  });
}

export function AsterionModel({
  alt,
  armorVisible = true,
  clip,
  enabled,
  fallbackSrc,
  interactive = false,
  modelAsset,
  reducedMotion,
  replayKey,
  view = "hero",
  viewKey = 0
}: {
  alt: string;
  armorVisible?: boolean;
  clip: AsterionClip;
  enabled: boolean;
  fallbackSrc: string;
  interactive?: boolean;
  modelAsset: string;
  reducedMotion: boolean;
  replayKey: number;
  view?: AsterionView;
  viewKey?: number;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const canvasHostRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<Runtime | null>(null);
  const latestClipRef = useRef(clip);
  const latestViewRef = useRef(view);
  const latestArmorVisibleRef = useRef(armorVisible);
  const [loadRequested, setLoadRequested] = useState(false);
  const [phase, setPhase] = useState<LoadPhase>("fallback");
  const [armorState, setArmorState] = useState<CompanionArmorState | null>(null);

  latestClipRef.current = clip;
  latestViewRef.current = view;
  latestArmorVisibleRef.current = armorVisible;

  useEffect(() => {
    if (!enabled || reducedMotion) {
      setLoadRequested(false);
      return;
    }

    const root = rootRef.current;
    if (!root || !("IntersectionObserver" in window)) {
      setLoadRequested(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        setLoadRequested(true);
        observer.disconnect();
      },
      { rootMargin: "180px" }
    );
    observer.observe(root);
    return () => observer.disconnect();
  }, [enabled, reducedMotion]);

  useEffect(() => {
    if (!enabled || reducedMotion || !loadRequested) {
      runtimeRef.current?.dispose();
      runtimeRef.current = null;
      canvasHostRef.current?.replaceChildren();
      setPhase("fallback");
      setArmorState(null);
      return;
    }

    const host = canvasHostRef.current;
    if (!host) return;
    let cancelled = false;
    let pendingRuntime: Runtime | null = null;
    let pendingCleanup: (() => void) | null = null;
    setPhase("loading");
    setArmorState(null);

    void Promise.all([
      import("three"),
      import("three/addons/loaders/GLTFLoader.js"),
      import("three/addons/libs/meshopt_decoder.module.js"),
      import("three/addons/environments/RoomEnvironment.js"),
      interactive ? import("three/addons/controls/OrbitControls.js") : Promise.resolve(null)
    ]).then(async ([THREE, { GLTFLoader }, { MeshoptDecoder }, { RoomEnvironment }, orbitModule]) => {
      if (cancelled) return;

      const renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "high-performance"
      });
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.04;
      renderer.domElement.className = "asterion-model-canvas";
      renderer.domElement.setAttribute("aria-hidden", "true");
      host.replaceChildren(renderer.domElement);
      let controls: OrbitControls | null = null;
      let environment: { dispose: () => void } | null = null;
      pendingCleanup = () => {
        controls?.dispose();
        environment?.dispose();
        renderer.dispose();
        renderer.forceContextLoss();
        renderer.domElement.remove();
        pendingCleanup = null;
      };

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(31, 1, 0.05, 100);
      const studio = new RoomEnvironment();
      const pmrem = new THREE.PMREMGenerator(renderer);
      const studioMap = pmrem.fromScene(studio, 0.04);
      environment = studioMap;
      scene.environment = studioMap.texture;
      scene.environmentIntensity = 1.2;
      studio.dispose();
      pmrem.dispose();
      scene.add(new THREE.HemisphereLight(0xfff5e5, 0x657080, 2.5));

      const key = new THREE.DirectionalLight(0xfff0dc, 4.0);
      key.position.set(-4.2, 5.4, 3.8);
      scene.add(key);

      const fill = new THREE.DirectionalLight(0xe4eeff, 2.8);
      fill.position.set(3.6, 3.2, 4.0);
      scene.add(fill);

      const loader = new GLTFLoader();
      loader.setMeshoptDecoder(MeshoptDecoder);
      const gltf = await loader.loadAsync(modelAsset);
      if (cancelled) {
        disposeModel(gltf.scene);
        pendingCleanup?.();
        return;
      }

      gltf.scene.traverse((child) => {
        const mesh = child as Object3D & { isMesh?: boolean; frustumCulled: boolean };
        if (mesh.isMesh) mesh.frustumCulled = true;
      });
      scene.add(gltf.scene);

      const setArmorVisible = (visible: boolean) => {
        setArmorState(setCompanionArmorVisible(gltf.scene, visible));
      };
      setArmorVisible(latestArmorVisibleRef.current);

      const bounds = new THREE.Box3().setFromObject(gltf.scene);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      gltf.scene.position.sub(center);
      const maximumDimension = Math.max(size.x, size.y, size.z);
      const boundingRadius = size.length() / 2;
      const cameraTarget = new THREE.Vector3(0, maximumDimension * 0.015, 0);
      const corners = [-1, 1].flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) =>
        new THREE.Vector3(x * size.x / 2, y * size.y / 2, z * size.z / 2).sub(cameraTarget)
      )));
      let currentView = latestViewRef.current;

      const fitCamera = (direction: InstanceType<typeof THREE.Vector3>) => {
        direction.normalize();
        const right = new THREE.Vector3(0, 1, 0).cross(direction).normalize();
        const up = direction.clone().cross(right).normalize();
        const verticalLimit = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.9;
        const horizontalLimit = verticalLimit * camera.aspect;
        // Each corner must fit both projected axes, including its depth.
        // Horizontal FOV becomes the limiting factor on narrow viewports.
        const distance = Math.max(...corners.map((corner) => corner.dot(direction) + Math.max(
          Math.abs(corner.dot(right)) / horizontalLimit,
          Math.abs(corner.dot(up)) / verticalLimit
        )));
        camera.position.copy(cameraTarget).addScaledVector(direction, distance);
        camera.near = Math.max(0.01, maximumDimension / 1_000);
        camera.far = Math.max(100, distance * 5);
        camera.lookAt(cameraTarget);
        camera.updateProjectionMatrix();
        if (controls) {
          controls.target.copy(cameraTarget);
          controls.minDistance = Math.max(boundingRadius * 1.05, distance * 0.45);
          controls.maxDistance = distance * 3;
          controls.update();
        }
      };
      const setView = (nextView: AsterionView) => {
        currentView = nextView;
        fitCamera(new THREE.Vector3(...VIEW_DIRECTIONS[nextView]));
      };
      setView(currentView);
      if (orbitModule) {
        controls = new orbitModule.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = false;
        controls.enablePan = false;
        controls.target.copy(cameraTarget);
      }

      const mixer = new THREE.AnimationMixer(gltf.scene);
      const actions = new Map<AsterionClip, AnimationAction>();
      for (const animation of gltf.animations) {
        actions.set(animation.name as AsterionClip, mixer.clipAction(animation));
      }

      let currentAction: AnimationAction | null = null;
      let finishedListener: ((event: { action: AnimationAction }) => void) | null = null;
      const play = (nextClip: AsterionClip) => {
        const nextAction = actions.get(nextClip) ?? actions.get("idle");
        if (!nextAction) return;
        if (finishedListener) {
          mixer.removeEventListener("finished", finishedListener);
          finishedListener = null;
        }
        if (currentAction && currentAction !== nextAction) currentAction.fadeOut(0.18);
        nextAction.reset();
        nextAction.enabled = true;
        nextAction.clampWhenFinished = !LOOPING_CLIPS.has(nextClip);
        nextAction.setLoop(
          LOOPING_CLIPS.has(nextClip) ? THREE.LoopRepeat : THREE.LoopOnce,
          LOOPING_CLIPS.has(nextClip) ? Infinity : 1
        );
        nextAction.fadeIn(0.18).play();
        currentAction = nextAction;

        if (!LOOPING_CLIPS.has(nextClip)) {
          finishedListener = ({ action }) => {
            if (action !== nextAction || cancelled) return;
            mixer.removeEventListener("finished", finishedListener!);
            finishedListener = null;
            play("idle");
          };
          mixer.addEventListener("finished", finishedListener);
        }
      };

      const resize = () => {
        const width = Math.max(1, host.clientWidth);
        const height = Math.max(1, host.clientHeight);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        fitCamera(controls
          ? camera.position.clone().sub(cameraTarget)
          : new THREE.Vector3(...VIEW_DIRECTIONS[currentView]));
      };
      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(host);
      resize();

      let animationFrame = 0;
      let previousFrameTime = performance.now();
      const render = (frameTime: number) => {
        const delta = Math.min(Math.max((frameTime - previousFrameTime) / 1_000, 0), 0.05);
        previousFrameTime = frameTime;
        if (!document.hidden) {
          mixer.update(delta);
          renderer.render(scene, camera);
        }
        animationFrame = window.requestAnimationFrame(render);
      };
      animationFrame = window.requestAnimationFrame(render);

      pendingRuntime = {
        play,
        setView,
        setArmorVisible,
        dispose: () => {
          cancelled = true;
          window.cancelAnimationFrame(animationFrame);
          resizeObserver.disconnect();
          if (finishedListener) mixer.removeEventListener("finished", finishedListener);
          mixer.stopAllAction();
          controls?.dispose();
          environment?.dispose();
          disposeModel(gltf.scene);
          renderer.dispose();
          renderer.forceContextLoss();
          renderer.domElement.remove();
        }
      };
      pendingCleanup = null;
      runtimeRef.current = pendingRuntime;
      play(latestClipRef.current);
      setPhase("ready");
    }).catch(() => {
      pendingCleanup?.();
      pendingRuntime?.dispose();
      if (!cancelled) {
        runtimeRef.current = null;
        host.replaceChildren();
        setPhase("fallback");
        setArmorState(null);
      }
    });

    return () => {
      cancelled = true;
      pendingCleanup?.();
      pendingRuntime?.dispose();
      if (runtimeRef.current === pendingRuntime) runtimeRef.current = null;
      host.replaceChildren();
    };
  }, [enabled, interactive, loadRequested, modelAsset, reducedMotion]);

  useEffect(() => {
    if (phase === "ready") runtimeRef.current?.play(clip);
  }, [clip, phase, replayKey]);

  useEffect(() => {
    if (phase === "ready") runtimeRef.current?.setView(view);
  }, [phase, view, viewKey]);

  useEffect(() => {
    if (phase === "ready") runtimeRef.current?.setArmorVisible(armorVisible);
  }, [armorVisible, phase]);

  useEffect(() => {
    if (phase !== "ready" || clip !== "idle") return;
    const timer = window.setInterval(() => runtimeRef.current?.play("blink"), 5_200);
    return () => window.clearInterval(timer);
  }, [clip, phase]);

  return (
    <div
      className={`asterion-model ${phase === "ready" ? "is-ready" : "is-fallback"}`}
      ref={rootRef}
      role="img"
      aria-label={alt}
      data-model-state={phase}
      data-model-view={view}
      data-model-armor-state={phase !== "ready" || !armorState ? "unavailable" :
        armorState.outfits === 0 ? "unsupported" : armorState.visibleMeshes === 0 ? "hidden" : "visible"}
      data-model-armor-outfits={phase === "ready" ? armorState?.outfits : undefined}
      data-model-armor-visible-outfits={phase === "ready" ? armorState?.visibleOutfits : undefined}
      data-model-armor-meshes={phase === "ready" ? armorState?.meshes : undefined}
      data-model-armor-visible-meshes={phase === "ready" ? armorState?.visibleMeshes : undefined}
    >
      <Image
        className="asterion-model-fallback"
        src={fallbackSrc}
        alt=""
        fill
        sizes="(max-width: 590px) 290px, 360px"
        priority
        unoptimized
      />
      <div
        className="asterion-model-host"
        ref={canvasHostRef}
        aria-hidden="true"
        style={interactive ? { pointerEvents: "auto", inset: 0, cursor: "grab" } : undefined}
      />
      {phase === "loading" ? <span className="asterion-model-loading">3D-Figur wird geladen …</span> : null}
    </div>
  );
}
