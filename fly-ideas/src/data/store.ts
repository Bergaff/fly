import { useCallback, useEffect, useMemo, useState } from "react";
import type { AppState, Idea, IdeaStatus, Project } from "./types";
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
    })),
  };
}

function load(): AppState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return structuredClone(SEED_STATE);
    const parsed = JSON.parse(raw) as AppState;
    if (parsed.version !== 1 || !Array.isArray(parsed.ideas)) return structuredClone(SEED_STATE);
    return normalize(parsed);
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
    () => ({ addIdea, updateIdea, deleteIdea, toggleCheck, duplicateIdea, moveIdea, setStatus, addProject, updateProject, deleteProject, exportJson, importJson, reset }),
    [addIdea, updateIdea, deleteIdea, toggleCheck, duplicateIdea, moveIdea, setStatus, addProject, updateProject, deleteProject, exportJson, importJson, reset],
  );

  return { state, ...api };
}

export type Store = ReturnType<typeof useStore>;
