import React, { useEffect, useState } from "react";

export default function RiskGauge({ score }) {
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    let start = 0;
    const id = setInterval(() => {
      start += (score - start) * 0.2;
      setAnimated(start);
      if (Math.abs(start - score) < 0.5) clearInterval(id);
    }, 60);
    return () => clearInterval(id);
  }, [score]);

  const pct = Math.min(Math.max(animated, 0), 100);
  const deg = (pct / 100) * 180;

  return (
    <div className="gauge">
      <div className="arc">
        <div className="needle" style={{ transform: `rotate(${deg - 90}deg)` }} />
      </div>
      <div className="label">{pct.toFixed(1)}%</div>
    </div>
  );
}
