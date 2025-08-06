// API Configuration
// Centralized configuration for backend API URL

// Get API base URL from environment variable, fallback to localhost for development
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'


// Export for convenience
export default API_BASE