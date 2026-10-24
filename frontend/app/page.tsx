"use client";

import { useEffect, useState } from "react";

// Temporary Phase 0 page: proves the frontend can reach the backend.
export default function Home() {
  const [status, setStatus] = useState("Checking API…");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((data) => {
        setStatus(data.status === "ok" ? "API connected" : "API responded unexpectedly");
      })
      .catch(() => setStatus("API not reachable. Is the backend running?"));
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-xl font-medium">{status}</p>
    </main>
  );
}
