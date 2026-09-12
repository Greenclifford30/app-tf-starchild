import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The MVP is fully statically generated. Static export keeps it compatible
  // with Amplify Hosting while the project is on Next.js 16.
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
