import path from 'node:path';

export default {
  esbuild: {
    jsx: 'automatic',
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/index.tsx'),
      name: 'ShopifyTryOnWidget',
      formats: ['umd', 'es'],
      fileName: (format: string) =>
        format === 'es' ? 'shopify-tryon-widget.es.js' : 'shopify-tryon-widget.js',
    },
    rollupOptions: {
      external: [],
      output: {
        exports: 'named',
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
    cssMinify: false,
    minify: 'esbuild',
    sourcemap: true,
    outDir: 'dist',
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
};
