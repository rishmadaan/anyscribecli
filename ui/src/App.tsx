import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import TranscribePage from "./pages/TranscribePage";
import HistoryPage from "./pages/HistoryPage";
import TranscriptView from "./pages/TranscriptView";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<TranscribePage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="history/:id" element={<TranscriptView />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
