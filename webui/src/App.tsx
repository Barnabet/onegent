import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { ChatPage } from "@/pages/ChatPage";
import { RunsPage } from "@/pages/RunsPage";
import { ToolsPage } from "@/pages/ToolsPage";
import { SkillsPage } from "@/pages/SkillsPage";
import { PacksPage } from "@/pages/PacksPage";
import { EvalsPage } from "@/pages/EvalsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ChatPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="packs" element={<PacksPage />} />
          <Route path="evals" element={<EvalsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
