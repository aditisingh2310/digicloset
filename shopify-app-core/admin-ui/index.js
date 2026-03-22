// admin-ui/index.js
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

const root = createRoot(document.getElementById('root'));
root.render(<App />);
import express from "express";
import bodyParser from "body-parser";
import { handleWebhook } from "./webhook.js";

const app = express();

app.use(
  "/webhooks",
  bodyParser.raw({ type: "application/json" })
);

app.post("/webhooks", handleWebhook);

app.listen(3000, () => {
  console.log("Server running on port 3000");
});
