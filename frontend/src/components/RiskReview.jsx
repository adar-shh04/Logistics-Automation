import React from 'react';

const RiskReview = ({ data, onBack }) => {
  if (!data) return null;

  const isFlagged = data.is_flagged;
  const statusColor = isFlagged ? 'red' : 'green';

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <button onClick={onBack} className="text-gray-400 hover:text-white mb-6 flex items-center gap-2 transition-colors">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
        Back to Dashboard
      </button>

      <div className={`panel p-8 relative overflow-hidden border-${statusColor}-500/30`}>
        {/* Subtle background glow based on risk */}
        <div className={`absolute -top-32 -right-32 w-96 h-96 blur-[100px] rounded-full pointer-events-none opacity-20 bg-${statusColor}-500`}></div>
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-[--color-brand-border] relative z-10">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Analysis Complete</h1>
            <p className="text-gray-400 font-mono text-sm">TXN_ID: {data.transaction_id}</p>
          </div>
          <div className={`mt-4 md:mt-0 px-6 py-3 rounded-full font-bold border flex items-center gap-2 ${isFlagged ? 'bg-red-500/10 text-red-400 border-red-500/30' : 'bg-green-500/10 text-green-400 border-green-500/30'}`}>
            {isFlagged ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            )}
            {data.message}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 relative z-10">
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-[--color-brand-bg] border border-[--color-brand-border] p-5 rounded-xl">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-semibold">Invoice Number</p>
              <p className="text-xl font-medium text-white">{data.invoice_number}</p>
            </div>
            <div className="bg-[--color-brand-bg] border border-[--color-brand-border] p-5 rounded-xl">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-semibold">Total Amount</p>
              <p className="text-xl font-medium text-white">{data.total_amount}</p>
            </div>
            <div className="bg-[--color-brand-bg] border border-[--color-brand-border] p-5 rounded-xl sm:col-span-2">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-semibold">Party / Buyer</p>
              <p className="text-xl font-medium text-white">{data.party}</p>
            </div>
            <div className="bg-[--color-brand-bg] border border-[--color-brand-border] p-5 rounded-xl sm:col-span-2">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-semibold">GSTIN</p>
              <p className="text-lg font-mono text-gray-300">{data.gstin}</p>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="bg-[--color-brand-bg] border border-[--color-brand-border] p-6 rounded-xl h-full flex flex-col justify-center items-center text-center">
              <p className="text-sm text-gray-400 uppercase tracking-wider mb-6 font-semibold">AI Fraud Risk Score</p>
              
              <div className="relative w-40 h-40 flex items-center justify-center mb-4">
                <svg className="absolute w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="var(--color-brand-surface)" strokeWidth="10" />
                  <circle 
                    cx="50" cy="50" r="45" fill="none" 
                    stroke={`var(--color-${statusColor}-500)`} 
                    strokeWidth="10" 
                    strokeDasharray={`${data.risk_score * 2.82} 282`} 
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="flex flex-col items-center">
                  <span className="text-5xl font-bold text-white tracking-tighter">{data.risk_score}<span className="text-2xl text-gray-500">%</span></span>
                </div>
              </div>
              
              <p className="text-sm text-gray-400 max-w-[200px]">
                {isFlagged ? 'Score exceeds safe threshold. Manual review required.' : 'Score is within normal operational variance.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskReview;
