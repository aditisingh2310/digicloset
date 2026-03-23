import React from "react";
import { createRoot } from "react-dom/client";
import "@shopify/polaris/build/esm/styles.css";
import AdminApp from "../admin-ui/src/AdminApp.jsx";

const root = createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <AdminApp />
  </React.StrictMode>
);
