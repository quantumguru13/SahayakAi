/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  optimizeFonts: false,
  // Every page here is a client component, so the app ships to Firebase Hosting
  // as plain static HTML/JS. `npm run dev` is unaffected.
  output: "export",
  // Firebase Hosting has no Next image optimizer.
  images: { unoptimized: true },
};

export default nextConfig;
