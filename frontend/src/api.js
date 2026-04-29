import axios from "axios";

// Allow overriding via Vite env vars
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const uploadInvoice = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  } catch (error) {
    console.error("Upload error:", error);
    throw error;
  }
};

export const getDocumentStatus = async (uid) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/status/${uid}`);
    return response.data;
  } catch (error) {
    console.error("Status check error:", error);
    throw error;
  }
};

export const checkHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/health`);
    return res.data;
  } catch (error) {
    return { status: "offline" };
  }
};
