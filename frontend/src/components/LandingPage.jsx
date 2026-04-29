import React from 'react';

const LandingPage = ({ onUpload, status, error, backendHealthy }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4">
      <div className="mb-8">
        <h2 className="text-5xl font-extrabold mb-4 text-white tracking-tight">
          Intelligent <span className="text-[--color-brand-primary]">Document Analysis</span>
        </h2>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto">
          Automate your logistics workflow. Instantly parse invoices, extract key data, and assess fraud risk using advanced AI models.
        </p>
      </div>

      <div className={`panel p-10 w-full max-w-lg transition-all duration-300 ${status === 'processing' ? 'animate-processing' : ''}`}>
        <div className="w-20 h-20 bg-[rgba(19,91,236,0.1)] rounded-2xl flex items-center justify-center mx-auto mb-6 text-[--color-brand-primary]">
          <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        
        <h3 className="text-2xl font-bold mb-2">Upload Document</h3>
        <p className="text-sm text-gray-400 mb-8">Drag and drop your invoice here, or click to browse (PDF, PNG, JPG).</p>

        <input
          type="file"
          onChange={(e) => {
            if(e.target.files && e.target.files[0]) {
              onUpload(e.target.files[0]);
            }
          }}
          className="glass-input w-full mb-6 text-sm"
          disabled={status === "uploading" || status === "processing" || !backendHealthy}
        />
        
        <button
          disabled={status === "uploading" || status === "processing" || !backendHealthy}
          className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-2"
        >
          {status === "uploading" && <span className="animate-spin inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full"></span>}
          {status === "processing" && <span className="animate-spin inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full"></span>}
          {status === "uploading" ? "Uploading..." : status === "processing" ? "AI is analyzing..." : "Analyze Document"}
        </button>

        {error && (
          <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-start text-left gap-3">
            <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <p>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LandingPage;
