import React from 'react';

const Dashboard = ({ uploadHistory }) => {
  return (
    <div className="glass-panel p-6 mt-8">
      <h2 className="text-xl font-bold mb-4 text-[--color-brand-light]">Transaction History</h2>
      {uploadHistory.length === 0 ? (
        <p className="text-gray-400">No transactions processed yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[rgba(255,255,255,0.1)]">
                <th className="p-3">Invoice #</th>
                <th className="p-3">Party</th>
                <th className="p-3">Amount</th>
                <th className="p-3">Risk Score</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {uploadHistory.map((item, idx) => (
                <tr key={idx} className="border-b border-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                  <td className="p-3">{item.invoice_number || 'N/A'}</td>
                  <td className="p-3 truncate max-w-[150px]" title={item.party}>{item.party || 'N/A'}</td>
                  <td className="p-3">{item.total_amount || '₹0'}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${item.risk_score > 60 ? 'bg-red-500' : 'bg-green-500'}`}
                          style={{ width: `${item.risk_score || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-sm">{item.risk_score || 0}%</span>
                    </div>
                  </td>
                  <td className="p-3">
                    {item.is_flagged ? (
                      <span className="px-2 py-1 bg-red-500/20 text-red-300 rounded text-xs font-medium border border-red-500/30">Flagged</span>
                    ) : (
                      <span className="px-2 py-1 bg-green-500/20 text-green-300 rounded text-xs font-medium border border-green-500/30">Clear</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
