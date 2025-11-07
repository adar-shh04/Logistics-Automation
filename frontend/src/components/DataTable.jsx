import React from "react";

export default function DataTable() {
  return (
    <div style={{ marginTop: "2rem" }}>
      <h3>Recent Transactions</h3>
      <table style={{ width: "100%", marginTop: "1rem", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#e3f2fd" }}>
            <th style={cell}>Date</th>
            <th style={cell}>Country</th>
            <th style={cell}>Product</th>
            <th style={cell}>Amount</th>
            <th style={cell}>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style={cell}>2025-11-03</td>
            <td style={cell}>India</td>
            <td style={cell}>Electronics</td>
            <td style={cell}>₹45,000</td>
            <td style={cell}>Exported</td>
          </tr>
          <tr>
            <td style={cell}>2025-10-29</td>
            <td style={cell}>USA</td>
            <td style={cell}>Textiles</td>
            <td style={cell}>₹38,000</td>
            <td style={cell}>Imported</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

const cell = {
  padding: "12px 8px",
  borderBottom: "1px solid #ddd",
  textAlign: "left",
};
