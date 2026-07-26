/** @type {import('next').NextConfig} */

const path = require("path");

// Termux-safe cache directory: falls back to a local .next-cache if HOME
// isn't set (e.g. running this same project on a normal Linux/macOS dev
// machine), so this config isn't hard-locked to Termux's filesystem layout.
const cacheDirectory = path.join(process.env.HOME || __dirname, ".next-cache");

const nextConfig = {
  // Lets the Next.js dev server accept requests/HMR from these origins.
  // Needed because Termux + some Android browsers/webviews don't always
  // present as plain "localhost".
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  typescript: {
    ignoreBuildErrors: true,
  },

  webpack: (config, { dev }) => {
    if (dev) {
      // Termux exposes a handful of Android system paths through its
      // filesystem shim. Webpack's file watcher will happily try to
      // recurse into /proc, /dev, /sys, etc. if not told otherwise,
      // which is slow at best and permission-denied noise at worst.
      config.watchOptions = {
        ...config.watchOptions,
        // Termux has no inotify support for most of the filesystem,
        // so polling is the only reliable watch strategy here.
        poll: 500,
        aggregateTimeout: 300,
        ignored: [
          "**/node_modules/**",
          "/data/**",
          "/storage/**",
          "/system/**",
          "/proc/**",
          "/dev/**",
          "/acct/**",
          "/vendor/**",
          "/product/**",
          "/apex/**",
          "/mnt/**",
        ],
      };
    }

    config.cache = {
      type: "filesystem",
      buildDependencies: {
        config: [__filename],
      },
      cacheDirectory,
    };

    return config;
  },
};

module.exports = nextConfig;
