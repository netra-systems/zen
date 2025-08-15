// Config index file - exports configuration
export * from './api';

// If there's a default export in api.ts, re-export it
import api from './api';
export const config = api;
export default api;