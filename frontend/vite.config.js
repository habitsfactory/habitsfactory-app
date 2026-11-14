import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    // Installable app: web manifest + a service worker that caches the app
    // shell. API calls are never cached — the data always comes from the server.
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo_edition.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'Habits Factory',
        short_name: 'Habits',
        description: 'Daily evolution, quantified.',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        theme_color: '#1490c9',
        background_color: '#0e2b3f',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        // The full icon set is big and only needed once habits are shown:
        // cache it on first use instead of at install time.
        globIgnores: ['**/lucide-all-*.js'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => /\/assets\/lucide-all-.*\.js$/.test(url.pathname),
            handler: 'CacheFirst',
            options: { cacheName: 'icon-set', expiration: { maxEntries: 2 } },
          },
        ],
        navigateFallback: '/index.html',
        // Served by Django, not by the SPA
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/static\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
    },
  },
})
