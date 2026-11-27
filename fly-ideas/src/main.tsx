import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { PublicResearchShowcase } from "./views/public-research-showcase.tsx";

const publicShowcase = import.meta.env.VITE_PUBLIC_SHOWCASE === "1";
if (publicShowcase) document.documentElement.classList.add("dark");
else document.documentElement.classList.toggle("dark", localStorage.getItem("fly-ideas:theme") !== "light");

createRoot(document.getElementById("root")!).render(
 <StrictMode>
 {publicShowcase ? <PublicResearchShowcase /> : <App />}
 </StrictMode>,
);
