import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'NodePilot Learning Assistant',
    description: 'AI-powered annotation and personalized teaching for technical articles',
    version: '1.0.0',
    permissions: ['storage', 'activeTab'],
    content_scripts: [
      {
        matches: ['https://manus.im/blog/*'],
        js: ['content-scripts/content.js'],
      },
    ],
  },
});
