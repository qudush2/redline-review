import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Forward /api/* to the FastAPI server, so the browser can talk to
  // localhost:3000 for everything. One exception: file uploads go straight to
  // localhost:8000, because this dev proxy times out on large request bodies
  // (see DIRECT_API_URL in lib/api.ts and the CORS setting in backend/app/main.py).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
