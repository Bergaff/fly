import { useCallback, useEffect, useState } from "react";

export type Theme = "dark" | "light";
const KEY = "fly-ideas:theme";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(KEY) === "light" ? "light" : "dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(KEY, theme);
  }, [theme]);
  const toggle = useCallback(() => setTheme((t) => (t === "dark" ? "light" : "dark")), []);
  return { theme, toggle };
}
