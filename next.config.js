// next.config.js
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
});

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  // output: "export", // Commented out for Vercel deployment, Vercel handles Next.js builds natively
  // Add other Next.js configurations here
};

module.exports = withPWA(nextConfig);

