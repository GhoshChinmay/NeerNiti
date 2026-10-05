/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  transpilePackages: ['deck.gl', '@deck.gl/react', '@deck.gl/layers', '@deck.gl/geo-layers'],
};

export default nextConfig;
