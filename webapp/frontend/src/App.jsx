import { Routes, Route } from "react-router-dom";
import Impressum from "./pages/Impressum.jsx";
import Contact from "./pages/Contact.jsx";
import Privacy from "./pages/Privacy";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Cabinet from "./pages/Cabinet.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/impressum" element={<Impressum />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/app/*" element={<Cabinet />} />
    </Routes>
  );
}
