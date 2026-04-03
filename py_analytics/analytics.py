import zmq
import json
import pandas as pd
from sklearn.ensemble import IsolationForest

def start_analytics_engine():
    # ZeroMQ (the receiver)
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    receiver.bind("tcp://127.0.0.1:5555")

    model = IsolationForest(contamination=0.05, random_state=42)
    is_model_trained = False

    print("--- [PYTHON] Analytics Engine Online ---")
    print("Waiting for C++ data on port 5555")

    while True:
        # Wait for data from C++
        message = receiver.recv_string()
        print("\n[PYTHON] Data received from C++!")

        # Parsing JSON and converting to DataFrame
        data = json.loads(message)
        df = pd.DataFrame(data['datapoints'])
        
        X = list(df['value'])
        print(df.head())

        if len(X) > 10:  # Ensure we have enough data to actually look for anomalies
            if not is_model_trained:
                print("Training initial model...")
                model.fit(X)
                is_model_trained = True
            
            predictions = model.predict(X)
            df['is_anomaly'] = predictions
            
            # Count the anomalies
            anomaly_count = (predictions == -1).sum()
            print(f"Analysis Complete: Found {anomaly_count} anomalies out of {len(X)} points.")
            
            # Show the anomalies if there are any
            if anomaly_count > 0:
                print("Detected Anomalies:")
                print(df[df['is_anomaly'] == -1])
        else:
            print("Not enough data points in this batch to run IsolationForest.")

if __name__ == "__main__":
    start_analytics_engine()