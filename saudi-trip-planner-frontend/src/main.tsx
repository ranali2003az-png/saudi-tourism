import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import Landing from "./pages/Landing";
import Plan from "./pages/Plan";
import Results from "./pages/Results";
import { TripProvider } from "./lib/TripContext";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <TripProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/results" element={<Results />} />
        </Routes>
      </TripProvider>
    </BrowserRouter>
  </React.StrictMode>
);
