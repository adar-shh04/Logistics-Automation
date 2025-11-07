import React, { useState } from "react";

export default function UploadSection() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleAnalyze = () => {
    if (!file) {
      alert("Please upload a document first!");
      return;
    }
    // simulate analysis
    setTimeout(() => {
      setResult({
        docId: "INV-" + Math.floor(Math.random() * 9999),
        txnId: "TXN-" + Math.floor(Math.random() * 9999),
        invoice: "INV-2025-001",
        party: "ABC Imports Ltd.",
        gstin: "27ABCDE1234F1Z9",
        total: "₹ 2,45,000",
        risk: (Math.random() * 100).toFixed(2),
      });
    }, 1000);
  };

  return (
    <section className="upload-section">
      <h2>Upload Invoice / Bill of Entry</h2>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleAnalyze}>🚀 Upload & Analyze</button>

      {result && (
        <div className="result-card">
          <h3>
            {result.risk > 50 ? "⚠️ High-Risk Transaction" : "✅ Safe Transaction"}
          </h3>
          <p><b>Document ID:</b> {result.docId}</p>
          <p><b>Transaction ID:</b> {result.txnId}</p>
          <p><b>Invoice #:</b> {result.invoice}</p>
          <p><b>Party:</b> {result.party}</p>
          <p><b>GSTIN:</b> {result.gstin}</p>
          <p><b>Total Amount:</b> {result.total}</p>
          <p><b>Risk Score:</b> {result.risk}%</p>
          <small>Prototype — AI OCR + NLP + Fraud Detection</small>
        </div>
      )}
    </section>
  );
}
