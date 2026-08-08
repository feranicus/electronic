import { Routes, Route } from "react-router-dom";
import Impressum from "./pages/Impressum.jsx";
import Contact from "./pages/Contact.jsx";
import Experience from "./pages/Experience.jsx";
import Privacy from "./pages/Privacy";
import Landing from "./pages/Landing.jsx";
import Partners from "./pages/Partners.jsx";
import Demo from "./pages/Demo.jsx";
import Login from "./pages/Login.jsx";
import Cabinet from "./pages/Cabinet.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/demo" element={<Demo />} />
      <Route path="/partners" element={<Partners />} />
      <Route path="/login" element={<Login />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/impressum" element={<Impressum />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/experience" element={<Experience />} />
      <Route path="/app/*" element={<Cabinet />} />
    </Routes>
  );
}
