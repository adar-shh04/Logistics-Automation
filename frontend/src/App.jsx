import React, { useState } from "react";
import { uploadInvoice, checkHealth } from "./api";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file first!");
      return;
    }

    try {
      const res = await uploadInvoice(file);
      setResult(res);
      setError("");
    } catch (err) {
      setError("Upload failed. Check backend connection.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <h1 className="text-3xl font-bold mb-4 text-gray-800">
        🌐 Digital Import-Export Automation
      </h1>

      <div className="bg-white shadow-md rounded-2xl p-8 w-[400px] text-center">
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          className="mb-4"
        />
        <div className="space-x-2">
          <button
            onClick={handleUpload}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            📤 Upload Invoice
          </button>
        </div>

        {error && <p className="text-red-500 mt-4">{error}</p>}

        {result && (
          <div className="mt-4 text-left text-sm">
            <p><strong>Invoice:</strong> {result.invoice_number}</p>
            <p><strong>Party:</strong> {result.party}</p>
            <p><strong>Amount:</strong> {result.total_amount}</p>
            <p><strong>Risk Score:</strong> {result.risk_score}%</p>
            <p className="mt-2 text-green-700">{result.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}
