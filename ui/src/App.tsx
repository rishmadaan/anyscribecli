import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import OnboardingWizard from "./components/OnboardingWizard";
import TranscribePage from "./pages/TranscribePage";
import HistoryPage from "./pages/HistoryPage";
import TranscriptView from "./pages/TranscriptView";
import SettingsPage from "./pages/SettingsPage";
import { getOnboardingStatus } from "./api/client";

/**
 * Wizard trigger: on app mount, ask the backend whether onboarding has been
 * completed. If not, and the user hasn't previously dismissed the wizard, pop
 * it. A global ``window.openOnboarding()`` escape hatch lets Settings reopen
 * the wizard manually.
 */
export default function App() {
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem("scribe_onboarding_dismissed") === "1";
    if (dismissed) return;
    getOnboardingStatus()
      .then((s) => {
        if (!s.completed) setShowWizard(true);
      })
      .catch(() => {
        // Backend unreachable — wizard stays closed rather than blocking.
      });
  }, []);

  // Escape hatch: let any component (Settings page) reopen the wizard.
  useEffect(() => {
    (window as unknown as { openOnboarding?: () => void }).openOnboarding = () => {
      localStorage.removeItem("scribe_onboarding_dismissed");
      setShowWizard(true);
    };
  }, []);

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
      {showWizard && (
        <OnboardingWizard onClose={() => setShowWizard(false)} />
      )}
    </BrowserRouter>
  );
}
