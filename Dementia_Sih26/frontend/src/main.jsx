import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { startSyncManager } from "./utils/syncManager";

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
startSyncManager();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
