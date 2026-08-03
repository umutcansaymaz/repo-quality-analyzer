import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  /* config options here */
  reactStrictMode: true,
  serverExternalPackages: [],
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
  },
  // Sprint 15: validation_workspace/ and validation_results/ contain thousands of
  // cloned repo files which can exhaust OS inotify watch limits during dev.
  // Exclude them from output file tracing so the build stays fast and lean.
  outputFileTracingExcludes: {
    "*": [
      "./validation_workspace/**/*",
      "./validation_results/**/*",
      "./benchmarks/**/*",
      "./mini-services/**/*",
      "./docs/**/*",
      "./db/**/*",
      "./tests/**/*",
    ],
  },
};

export default nextConfig;
