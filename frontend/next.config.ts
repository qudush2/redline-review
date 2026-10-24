import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Forward /api/* to the FastAPI server, so the browser only ever talks to
  // localhost:3000 and we don't need any cross-origin (CORS) setup.
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
