import axios from "axios";

const api = axios.create({ baseURL: process.env.REACT_APP_API_URL || "http://localhost:5000/api" });
export default api;

// Backend stores some fields as JSON strings; parse safely.
export const parse = (v) => {
  if (v && typeof v === "object") return v;
  try { return JSON.parse(v || "{}"); } catch { return {}; }
};
export const asList = (d) => (Array.isArray(d) ? d : d?.adaptations || d?.activities || d?.items || []);
