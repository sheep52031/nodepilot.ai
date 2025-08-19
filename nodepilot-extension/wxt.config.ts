import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'NodePilot Learning Assistant',
    description: 'AI-powered annotation and personalized teaching for technical articles',
    version: '1.0.0',
    permissions: ['storage', 'activeTab'],
    host_permissions: ['https://manus.im/*', 'http://127.0.0.1:8000/*'],
  },
});
