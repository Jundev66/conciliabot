import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import InvoiceDetail from "./pages/InvoiceDetail";
import AuditLogPage from "./pages/AuditLog";
import Ingest from "./pages/Ingest";
import Data from "./pages/Data";
import Evals from "./pages/Evals";
import Settings from "./pages/Settings";
import Legal from "./pages/Legal";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import LegalNotice from "./pages/LegalNotice";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/facturas/:id" element={<InvoiceDetail />} />
        <Route path="/ingesta" element={<Ingest />} />
        <Route path="/datos" element={<Data />} />
        <Route path="/auditoria" element={<AuditLogPage />} />
        <Route path="/evals" element={<Evals />} />
        <Route path="/configuracion" element={<Settings />} />
        <Route path="/legal" element={<Legal />} />
        <Route path="/legal/terminos" element={<Terms />} />
        <Route path="/legal/privacidad" element={<Privacy />} />
        <Route path="/legal/aviso" element={<LegalNotice />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
