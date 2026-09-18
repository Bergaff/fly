import { useCallback, useEffect, useMemo, useState } from "react";
import type { AppState, ExperimentEntry, Idea, IdeaStatus, Project, Reference } from "./types";
import { SEED_STATE, makeChecklist } from "./seed";
import { uid } from "@/lib/utils";

export { uid };

const KEY = "fly-ideas:state:v1";

/** Дополняет идеи из старых сохранений новыми полями */
function normalize(state: AppState): AppState {
 return {
 ...state,
 ideas: state.ideas.map((i) => ({
 ...i,
 links: i.links ?? [],
 notes: i.notes ?? "",
 checklist: Array.isArray(i.checklist) ? i.checklist : makeChecklist(),
 deadline: i.deadline ?? null,
 dependsOn: Array.isArray(i.dependsOn) ? i.dependsOn : [],
 experiments: Array.isArray(i.experiments) ? i.experiments : [],
 citations: Array.isArray(i.citations) ? i.citations : [],
 })),
 references: Array.isArray(state.references) ? state.references : [],
 };
}

/** Добавляет в сохранение стартовые идеи и источники, которых в нём ещё нет.
 *  Правки пользователя не трогает: свои идеи остаются как есть. */
function withNewSeed(state: AppState): AppState {
  const seeded = new Set(state.seeded ?? []);
  const freshIdeas = SEED_STATE.ideas.filter((i) => !seeded.has(i.id) && !state.ideas.some((x) => x.id === i.id));
  const freshRefs = SEED_STATE.references.filter((r) => !seeded.has(r.id) && !state.references.some((x) => x.id === r.id));
  if (!freshIdeas.length && !freshRefs.length) return state;
  return {
    ...state,
    ideas: [...state.ideas, ...freshIdeas],
    references: [...state.references, ...freshRefs],
    seeded: [...seeded, ...freshIdeas.map((i) => i.id), ...freshRefs.map((r) => r.id)],
  };
}

function load(): AppState {
 try {
 const raw = localStorage.getItem(KEY);
 if (!raw) return structuredClone(SEED_STATE);
 const parsed = JSON.parse(raw) as AppState;
 if (parsed.version !== 1 || !Array.isArray(parsed.ideas)) return structuredClone(SEED_STATE);
 return withNewSeed(normalize(parsed));
 } catch {
 return structuredClone(SEED_STATE);
 }
}

export function useStore() {
 const [state, setState] = useState<AppState>(load);

 useEffect(() => {
 localStorage.setItem(KEY, JSON.stringify(state));
 }, [state]);

 const stamp = () => new Date().toISOString();

 const addIdea = useCallback((projectId: string, partial?: Partial<Idea>): Idea => {
 const t = stamp();
 const created: Idea = {
 id: uid("i"),
 projectId,
 title: "Новая идея",
 question: "",
 method: "",
 validation: "",
 venues: [],
 timeline: "",
 tags: [],
 status: "backlog",
 scores: { effort: 5, impact: 5, novelty: 5, speed: 5, risk: 5 },
 notes: "",
 links: [],
 checklist: makeChecklist(),
 deadline: null,
 dependsOn: [],
 experiments: [],
 citations: [],
 createdAt: t,
 updatedAt: t,
 ...partial,
 };
 setState((s) => ({ ...s, ideas: [created, ...s.ideas] }));
 return created;
 }, []);

 const updateIdea = useCallback((id: string, patch: Partial<Idea>) => {
 setState((s) => ({
 ...s,
 ideas: s.ideas.map((i) => (i.id === id ? { ...i, ...patch, updatedAt: stamp() } : i)),
 }));
 }, []);

 const deleteIdea = useCallback((id: string) => {
 setState((s) => ({
 ...s,
 ideas: s.ideas.filter((i) => i.id !== id).map((i) => (i.dependsOn.includes(id) ? { ...i, dependsOn: i.dependsOn.filter((d) => d !== id) } : i)),
 }));
 }, []);

 const toggleCheck = useCallback((ideaId: string, itemId: string) => {
 setState((s) => ({
 ...s,
 ideas: s.ideas.map((i) =>
 i.id !== ideaId
 ? i
 : {
 ...i,
 updatedAt: stamp(),
 checklist: i.checklist.map((c) => (c.id === itemId ? { ...c, done: !c.done, doneAt: !c.done ? stamp() : null } : c)),
 },
 ),
 }));
 }, []);

 const duplicateIdea = useCallback((id: string, toProjectId?: string) => {
 setState((s) => {
 const src = s.ideas.find((i) => i.id === id);
 if (!src) return s;
 const t = stamp();
 const copy: Idea = {
 ...structuredClone(src),
 id: uid("i"),
 projectId: toProjectId ?? src.projectId,
 title: toProjectId ? src.title : `${src.title} (копия)`,
 checklist: src.checklist.map((c) => ({ ...c, id: uid("c") })),
 experiments: src.experiments.map((e) => ({ ...e, id: uid("e") })),
 createdAt: t,
 updatedAt: t,
 };
 return { ...s, ideas: [copy, ...s.ideas] };
 });
 }, []);

 const moveIdea = useCallback((id: string, projectId: string) => {
 setState((s) => ({
 ...s,
 ideas: s.ideas.map((i) => (i.id === id ? { ...i, projectId, updatedAt: stamp() } : i)),
 }));
 }, []);

 const setStatus = useCallback((id: string, status: IdeaStatus) => {
 setState((s) => ({ ...s, ideas: s.ideas.map((i) => (i.id === id ? { ...i, status, updatedAt: stamp() } : i)) }));
 }, []);

 // ---- Журнал экспериментов ----
 const addExperiment = useCallback((ideaId: string, entry?: Partial<ExperimentEntry>): ExperimentEntry => {
 const t = stamp();
 const e: ExperimentEntry = {
 id: uid("e"),
 date: t.slice(0, 10),
 title: "",
 params: "",
 result: "",
 conclusion: "",
 outcome: "inconclusive",
 createdAt: t,
 ...entry,
 };
 setState((s) => ({ ...s, ideas: s.ideas.map((i) => (i.id === ideaId ? { ...i, updatedAt: t, experiments: [e, ...i.experiments] } : i)) }));
 return e;
 }, []);

 const updateExperiment = useCallback((ideaId: string, entryId: string, patch: Partial<ExperimentEntry>) => {
 setState((s) => ({
 ...s,
 ideas: s.ideas.map((i) => (i.id === ideaId ? { ...i, updatedAt: stamp(), experiments: i.experiments.map((e) => (e.id === entryId ? { ...e, ...patch } : e)) } : i)),
 }));
 }, []);

 const deleteExperiment = useCallback((ideaId: string, entryId: string) => {
 setState((s) => ({ ...s, ideas: s.ideas.map((i) => (i.id === ideaId ? { ...i, updatedAt: stamp(), experiments: i.experiments.filter((e) => e.id !== entryId) } : i)) }));
 }, []);

 // ---- Библиография ----
 const addReference = useCallback((partial?: Partial<Reference>): Reference => {
 const r: Reference = { id: uid("r"), authors: "", year: null, title: "", venue: "", doi: "", url: "", tags: [], notes: "", createdAt: stamp(), ...partial };
 setState((s) => ({ ...s, references: [r, ...s.references] }));
 return r;
 }, []);

 const updateReference = useCallback((id: string, patch: Partial<Reference>) => {
 setState((s) => ({ ...s, references: s.references.map((r) => (r.id === id ? { ...r, ...patch } : r)) }));
 }, []);

 const deleteReference = useCallback((id: string) => {
 setState((s) => ({
 ...s,
 references: s.references.filter((r) => r.id !== id),
 ideas: s.ideas.map((i) => (i.citations.some((c) => c.refId === id) ? { ...i, citations: i.citations.filter((c) => c.refId !== id) } : i)),
 }));
 }, []);

 const setCitations = useCallback((ideaId: string, citations: Idea["citations"]) => {
 setState((s) => ({ ...s, ideas: s.ideas.map((i) => (i.id === ideaId ? { ...i, updatedAt: stamp(), citations } : i)) }));
 }, []);

 const addProject = useCallback((name: string): Project => {
 const palette = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
 const p: Project = {
 id: uid("p"),
 name,
 description: "",
 color: palette[Math.floor(Math.random() * palette.length)],
 createdAt: stamp(),
 };
 setState((s) => ({ ...s, projects: [...s.projects, p] }));
 return p;
 }, []);

 const updateProject = useCallback((id: string, patch: Partial<Project>) => {
 setState((s) => ({ ...s, projects: s.projects.map((p) => (p.id === id ? { ...p, ...patch } : p)) }));
 }, []);

 const deleteProject = useCallback((id: string, moveIdeasTo?: string) => {
 setState((s) => {
 if (s.projects.length <= 1) return s;
 const target = moveIdeasTo ?? s.projects.find((p) => p.id !== id)!.id;
 return {
 ...s,
 projects: s.projects.filter((p) => p.id !== id),
 ideas: s.ideas.map((i) => (i.projectId === id ? { ...i, projectId: target } : i)),
 };
 });
 }, []);

 const exportJson = useCallback(() => JSON.stringify(state, null, 2), [state]);

 const importJson = useCallback((json: string) => {
 const parsed = JSON.parse(json) as AppState;
 if (parsed.version !== 1 || !Array.isArray(parsed.ideas) || !Array.isArray(parsed.projects)) {
 throw new Error("Неверный формат файла");
 }
 setState(normalize(parsed));
 }, []);

 const reset = useCallback(() => setState(structuredClone(SEED_STATE)), []);

 const api = useMemo(
 () => ({ addIdea, updateIdea, deleteIdea, toggleCheck, duplicateIdea, moveIdea, setStatus, addExperiment, updateExperiment, deleteExperiment, addReference, updateReference, deleteReference, setCitations, addProject, updateProject, deleteProject, exportJson, importJson, reset }),
 [addIdea, updateIdea, deleteIdea, toggleCheck, duplicateIdea, moveIdea, setStatus, addExperiment, updateExperiment, deleteExperiment, addReference, updateReference, deleteReference, setCitations, addProject, updateProject, deleteProject, exportJson, importJson, reset],
 );

 return { state, ...api };
}

export type Store = ReturnType<typeof useStore>;
