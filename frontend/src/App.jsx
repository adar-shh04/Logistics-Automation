import React, { useState, useEffect } from "react";
import { uploadInvoice, getDocumentStatus, checkHealth } from "./api";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, uploading, processing, complete, error
  const [currentDocId, setCurrentDocId] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [backendHealthy, setBackendHealthy] = useState(true);

  // Health check on mount
  useEffect(() => {
    const init = async () => {
      const res = await checkHealth();
      if (res.status !== "ok") setBackendHealthy(false);
    };
    init();
  }, []);

  // Polling logic
  useEffect(() => {
    let interval;
    if (status === "processing" && currentDocId) {
      interval = setInterval(async () => {
        try {
          const res = await getDocumentStatus(currentDocId);
          if (res.status === "completed") {
            setStatus("complete");
            setHistory(prev => [res, ...prev]);
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
          // Don't kill polling on single network error, just wait for next tick
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, currentDocId]);

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file first!");
      return;
    }

    try {
      setStatus("uploading");
      setError("");
      const res = await uploadInvoice(file);
      
      if (res.status === "processing") {
        setCurrentDocId(res.document_id);
        setStatus("processing");
      }
    } catch (err) {
      setStatus("error");
      setError("Upload failed. Check backend connection.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col p-8 max-w-6xl mx-auto w-full">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[--color-brand-light] to-[--color-brand-accent]">
            Digital Import-Export
          </h1>
          <p className="text-gray-400 mt-2">AI-Powered Customs & Risk Automation</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${backendHealthy ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.6)]'}`}></div>
          <span className="text-sm font-medium">{backendHealthy ? 'System Online' : 'System Offline'}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Section */}
        <div className={`glass-panel p-8 flex flex-col items-center justify-center text-center lg:col-span-1 transition-all duration-300 ${status === 'processing' ? 'animate-processing' : ''}`}>
          <div className="w-16 h-16 bg-[rgba(255,255,255,0.1)] rounded-full flex items-center justify-center mb-6">
            <svg className="w-8 h-8 text-[--color-brand-light]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
          </div>
          
          <h2 className="text-xl font-bold mb-2">Upload Invoice</h2>
          <p className="text-sm text-gray-400 mb-6">Supported formats: PDF, PNG, JPG</p>

          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            className="glass-input w-full p-2 mb-4 text-sm file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-[rgba(91,192,190,0.2)] file:text-[--color-brand-accent] hover:file:bg-[rgba(91,192,190,0.3)]"
          />
          
          <button
            onClick={handleUpload}
            disabled={status === "uploading" || status === "processing" || !backendHealthy}
            className="w-full bg-gradient-to-r from-[--color-brand-teal] to-[--color-brand-light] text-white font-bold py-3 px-4 rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === "uploading" ? "Uploading..." : status === "processing" ? "Analyzing via AI..." : "Process Document"}
          </button>

          {error && <p className="text-red-400 mt-4 text-sm bg-red-400/10 p-2 rounded w-full">{error}</p>}
        </div>

        {/* Results / Dashboard Section */}
        <div className="lg:col-span-2">
          {status === "processing" && (
            <div className="glass-panel p-12 flex flex-col items-center justify-center h-[300px]">
              <div className="w-16 h-16 border-4 border-[--color-brand-light] border-t-transparent rounded-full animate-spin mb-4"></div>
              <h3 className="text-xl font-semibold">Extracting Data & Calculating Risk...</h3>
              <p className="text-gray-400 mt-2">Our AI is parsing the document layout.</p>
            </div>
          )}

          {status === "complete" && history.length > 0 && (
            <div className={`glass-panel p-8 relative overflow-hidden ${history[0].is_flagged ? 'border-red-500/50' : 'border-green-500/50'}`}>
              <div className={`absolute top-0 right-0 w-32 h-32 blur-3xl -z-10 ${history[0].is_flagged ? 'bg-red-500/20' : 'bg-green-500/20'}`}></div>
              
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold">Analysis Complete</h2>
                  <p className="text-gray-400">Transaction ID: {history[0].transaction_id}</p>
                </div>
                <div className={`px-4 py-2 rounded-full font-bold border ${history[0].is_flagged ? 'bg-red-500/20 text-red-400 border-red-500/50' : 'bg-green-500/20 text-green-400 border-green-500/50'}`}>
                  {history[0].message}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Invoice Number</p>
                  <p className="text-lg font-semibold">{history[0].invoice_number}</p>
                </div>
                <div className="bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Total Amount</p>
                  <p className="text-lg font-semibold text-[--color-brand-light]">{history[0].total_amount}</p>
                </div>
                <div className="bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Party</p>
                  <p className="text-lg font-semibold truncate" title={history[0].party}>{history[0].party}</p>
                </div>
                <div className="bg-[rgba(0,0,0,0.2)] p-4 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Fraud Risk Score</p>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold">{history[0].risk_score}%</span>
                    <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${history[0].risk_score > 60 ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: `${history[0].risk_score}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {(status === "idle" || status === "uploading" || status === "error") && history.length === 0 && (
             <div className="glass-panel p-12 flex flex-col items-center justify-center h-[300px] text-gray-400 text-center">
               <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
               <p>Upload a document to see the AI analysis here.</p>
             </div>
          )}
          
          {history.length > 0 && <Dashboard uploadHistory={history} />}
        </div>
      </div>
    </div>
  );
}
