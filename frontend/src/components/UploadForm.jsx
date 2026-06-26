import React from "react";

export default function UploadForm() {
  return (
    <div style={{ marginTop: "1.5rem" }}>
      <h3>Upload CSV</h3>
      <input type="file" accept=".csv" />
      <button style={{ marginLeft: "1rem" }}>Upload</button>
    </div>
  );
}
