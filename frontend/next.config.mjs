/** @type {import('next').NextConfig} */

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// Parse the backend URL so we can use hostname/port in image patterns
const parsedApi = new URL(apiUrl);
const apiHostname = parsedApi.hostname;
const apiPort     = parsedApi.port || undefined;
const apiProtocol = /** @type {"http" | "https"} */ (parsedApi.protocol.replace(":", ""));

const nextConfig = {
  // Allow Next.js <Image> to load photos served by the backend
  images: {
    remotePatterns: [
      {
        protocol: apiProtocol,
        hostname: apiHostname,
        ...(apiPort ? { port: apiPort } : {}),
        pathname: "/uploads/**",
      },
    ],
  },

  // In production the frontend calls the backend directly via NEXT_PUBLIC_API_URL.
  // The rewrite below is kept only for local dev so you can run without setting
  // the env var — it proxies /api/* through Next.js to avoid CORS issues in dev.
  ...(process.env.NODE_ENV !== "production" && {
    async rewrites() {
      return [
        {
          source: "/api/:path*",
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    },
  }),
};

export default nextConfig;
