import React, { useState, useEffect } from "react";
import { uploadInvoice, getDocumentStatus, checkHealth } from "./api";
import LandingPage from "./components/LandingPage";
import Dashboard from "./components/Dashboard";
import RiskReview from "./components/RiskReview";

export default function App() {
  const [status, setStatus] = useState("idle"); // idle, uploading, processing, complete, error
  const [currentDocId, setCurrentDocId] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [backendHealthy, setBackendHealthy] = useState(true);
  
  // Navigation state: 'home', 'review'
  const [currentView, setCurrentView] = useState('home');
  const [selectedDocument, setSelectedDocument] = useState(null);

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
            setStatus("idle");
            setHistory(prev => [res, ...prev]);
            setSelectedDocument(res);
            setCurrentView('review');
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, currentDocId]);

  const handleUpload = async (file) => {
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

  const handleViewDocument = (doc) => {
    setSelectedDocument(doc);
    setCurrentView('review');
  };

  const handleBackToHome = () => {
    setCurrentView('home');
    setSelectedDocument(null);
  };

  return (
    <div className="min-h-screen flex flex-col pt-8 pb-20 px-6 sm:px-12 max-w-7xl mx-auto w-full">
      {/* Top Navigation / Header */}
      <header className="mb-12 flex justify-between items-center pb-6 border-b border-[--color-brand-border]">
        <div className="flex items-center gap-4 cursor-pointer" onClick={handleBackToHome}>
          <div className="w-10 h-10 bg-[--color-brand-primary] rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(19,91,236,0.5)]">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Logistics<span className="text-[--color-brand-primary]">Auto</span>
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-400 hidden sm:inline-block">
            {backendHealthy ? 'API Connected' : 'API Offline'}
          </span>
          <div className={`w-3 h-3 rounded-full ${backendHealthy ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.6)]'}`}></div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full">
        {currentView === 'home' && (
          <div className="animate-in fade-in duration-500">
            <LandingPage 
              onUpload={handleUpload} 
              status={status} 
              error={error} 
              backendHealthy={backendHealthy} 
            />
            
            {history.length > 0 && (
              <div className="mt-12 pt-12 border-t border-[--color-brand-border]">
                <Dashboard 
                  uploadHistory={history} 
                  onViewDocument={handleViewDocument} 
                />
              </div>
            )}
          </div>
        )}

        {currentView === 'review' && selectedDocument && (
          <RiskReview 
            data={selectedDocument} 
            onBack={handleBackToHome} 
          />
        )}
      </main>
    </div>
  );
}
