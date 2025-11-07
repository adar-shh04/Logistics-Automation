import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000"; // FastAPI backend

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

export const checkHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/health`);
    return res.data;
  } catch (error) {
    return { status: "offline" };
  }
};
