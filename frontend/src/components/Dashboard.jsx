import React from 'react';

const Dashboard = ({ uploadHistory, onViewDocument }) => {
  return (
    <div className="w-full max-w-6xl mx-auto mt-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Operations Dashboard</h2>
          <p className="text-gray-400 text-sm mt-1">Recent document processing history</p>
        </div>
        <div className="text-sm text-gray-400 bg-[--color-brand-surface] px-4 py-2 rounded-lg border border-[--color-brand-border]">
          Total Processed: <span className="text-white font-bold ml-1">{uploadHistory.length}</span>
        </div>
      </div>

      {uploadHistory.length === 0 ? (
        <div className="panel p-12 text-center text-gray-400 border-dashed">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          <p>No documents processed yet. Upload a document to get started.</p>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[--color-brand-bg] border-b border-[--color-brand-border]">
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Invoice #</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Party</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Amount</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Risk Score</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold">Status</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-gray-400 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {uploadHistory.map((item, idx) => (
                  <tr key={idx} className="border-b border-[--color-brand-border] hover:bg-[rgba(255,255,255,0.02)] transition-colors group">
                    <td className="p-4 font-medium text-white">{item.invoice_number || 'N/A'}</td>
                    <td className="p-4 truncate max-w-[200px] text-gray-300" title={item.party}>{item.party || 'N/A'}</td>
                    <td className="p-4 text-gray-300">{item.total_amount || '₹0'}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-16 h-1.5 bg-[--color-brand-bg] rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${item.risk_score > 60 ? 'bg-red-500' : 'bg-green-500'}`}
                            style={{ width: `${item.risk_score || 0}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-mono text-gray-300">{item.risk_score || 0}%</span>
                      </div>
                    </td>
                    <td className="p-4">
                      {item.is_flagged ? (
                        <span className="px-2.5 py-1 bg-red-500/10 text-red-400 rounded border border-red-500/20 text-xs font-semibold uppercase tracking-wide">Flagged</span>
                      ) : (
                        <span className="px-2.5 py-1 bg-green-500/10 text-green-400 rounded border border-green-500/20 text-xs font-semibold uppercase tracking-wide">Clear</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => onViewDocument(item)}
                        className="text-[--color-brand-primary] hover:text-white text-sm font-medium transition-colors opacity-0 group-hover:opacity-100"
                      >
                        View Details →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
