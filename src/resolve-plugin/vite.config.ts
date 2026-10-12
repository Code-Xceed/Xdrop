import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@xdrop/shared-types': path.resolve(__dirname, '../../packages/shared-types/src/index.ts'),
      '@xdrop/protocol': path.resolve(__dirname, '../../packages/protocol/src/index.ts'),
      '@xdrop/utilities': path.resolve(__dirname, '../../packages/utilities/src/index.ts'),
      '@resolvefetch/shared-types': path.resolve(__dirname, '../../packages/shared-types/src/index.ts'),
      '@resolvefetch/protocol': path.resolve(__dirname, '../../packages/protocol/src/index.ts'),
      '@resolvefetch/utilities': path.resolve(__dirname, '../../packages/utilities/src/index.ts'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
      '/thumbnails': {
        target: 'http://127.0.0.1:8484',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8484',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
