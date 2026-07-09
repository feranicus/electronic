import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Connections from "./pages/Connections.jsx";
import Scout from "./pages/Scout.jsx";
import Pipeline from "./pages/Pipeline.jsx";
import Hermes from "./pages/Hermes.jsx";

export default function App() {
  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scout" element={<Scout />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/hermes" element={<Hermes />} />
          <Route path="/connections" element={<Connections />} />
        </Routes>
      </main>
    </div>
  );
}
