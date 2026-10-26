import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the floating Next.js dev badge so it doesn't cover the app in demos.
  devIndicators: false,

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
