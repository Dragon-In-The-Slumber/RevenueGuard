import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output ships only the files the server needs, instead of the
  // whole node_modules tree — a much smaller Docker/Render image.
  output: "standalone",

  // NEXT_PUBLIC_* is inlined at BUILD time. If NEXT_PUBLIC_API_URL is unset when
  // the image is built, the deployed dashboard calls http://localhost:8000 from
  // the visitor's browser and every request fails. This proxy means same-origin
  // /api/* requests work even then, because the rewrite is resolved server-side
  // at runtime.
  async rewrites() {
    const api = process.env.API_PROXY_TARGET;
    if (!api) return [];
    return [
      { source: "/api/:path*", destination: `${api.replace(/\/$/, "")}/api/:path*` },
      { source: "/health", destination: `${api.replace(/\/$/, "")}/health` },
    ];
  },

  // The workspace has two lockfiles; name the root explicitly so the build does
  // not guess and warn.
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
