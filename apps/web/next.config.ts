import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["lucide-react"]
  },
  async rewrites() {
    const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://api:8000";
    const ragInternalUrl = process.env.RAG_INTERNAL_URL ?? "http://rag-api:8090";

    return [
      {
        source: "/api/rag/:path*",
        destination: `${ragInternalUrl}/:path*`
      },
      {
        source: "/api/:path*",
        destination: `${apiInternalUrl}/api/:path*`
      }
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "minio" }
    ]
  }
};

export default nextConfig;
