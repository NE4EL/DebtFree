import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loading, NavBar } from "./components/ui";
import { AuthProvider, PlanProvider, useAuth } from "./context";
import AuthPage from "./pages/AuthPage";
import ComparePage from "./pages/ComparePage";
import DebtFormPage from "./pages/DebtFormPage";
import DebtSchedulePage from "./pages/DebtSchedulePage";
import DebtsPage from "./pages/DebtsPage";
import PlanPage from "./pages/PlanPage";
import { ScenarioPage, ScenariosPage } from "./pages/ScenariosPage";
import "./styles.css";

function App() {
  const { user, ready } = useAuth();
  if (!ready) return <Loading />;
  if (!user) return <AuthPage />;
  return (
    <PlanProvider>
      <NavBar />
      <main className="container">
        <Routes>
          <Route path="/debts" element={<DebtsPage />} />
          <Route path="/debts/new" element={<DebtFormPage />} />
          <Route path="/debts/:id/edit" element={<DebtFormPage />} />
          <Route path="/debts/:id/schedule" element={<DebtSchedulePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/scenarios" element={<ScenariosPage />} />
          <Route path="/scenarios/:id" element={<ScenarioPage />} />
          <Route path="*" element={<Navigate to="/debts" replace />} />
        </Routes>
      </main>
    </PlanProvider>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
