# run this inside backend container or locally to generate model file
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

def train_and_save(path="/app/models/isolation_forest.joblib"):
    # synthetic dataset for prototype
    X = []
    for i in range(1200):
        amt = float(np.random.lognormal(mean=8, sigma=1.2))
        cnt = float(np.random.poisson(3))
        X.append([amt, cnt])
    for i in range(30):
        X.append([float(np.random.lognormal(mean=12, sigma=1.5)), float(np.random.poisson(1))])
    X = np.array(X)
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    model.fit(X)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print("Model saved to", path)

if __name__ == "__main__":
    train_and_save()
