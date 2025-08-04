# train_model.py
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras import layers, models

# parameters
EPOCHS      = 48
BATCH_SIZE  = 40
TEST_SIZE   = 0.1
RANDOM_STATE= 42

# file paths
CSV_FILE   = 'results.csv'
BEST_IW    = 'best_iw.json'
MODEL_FILE = 'predict_model.h5'
SCALER_FILE= 'scaler.json'

def load_data():
    # 1) read CSV
    df = pd.read_csv(CSV_FILE, parse_dates=['timestamp'])
    # 2) read best_iw.json
    with open(BEST_IW) as f:
        best_map = {k:int(v['best_iw']) for k,v in json.load(f).items()}
    def lookup(row):
        key = f"({int(row.bw)}, {int(row.delay)}, {int(row.loss)})"
        return best_map[key]
    df['best_iw'] = df.apply(lookup, axis=1)
    return df

def prepare_xy(df):
    # Normalised RTT & TP (overall max/min)
    df['rtt_min'] = df.groupby(['bw','delay','loss'])['rtt'].transform('min')
    df['tp_max']  = df.groupby(['bw','delay','loss'])['throughput'].transform('max')
    df['rtt_norm']= df['rtt_min'] / df['rtt']
    df['tp_norm'] = df['throughput'] / df['tp_max']
    X = df[['bw','delay','loss','rtt_norm','tp_norm']].values.astype(np.float32)
    y = df['best_iw'].values.astype(np.float32)
    return X, y

def build_model():
    m = models.Sequential([
        layers.Input(shape=(5,)),
        layers.Dense(64, activation='relu'),
        layers.Dense(64, activation='relu'),
        layers.Dense(1)   #regression outputs a real number
    ])
    m.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return m

def main():
    df = load_data()

    # Features + labels
    X, y = prepare_xy(df)
    # Calculate and save standardised parameters
    mean = X.mean(axis=0).tolist()
    std  = X.std(axis=0).tolist()
    with open(SCALER_FILE, 'w') as f:
        json.dump({'mean':mean, 'std':std}, f, indent=2)
    # standardise
    X = (X - np.array(mean)) / np.array(std)

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # model training
    model = build_model()
    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE
    )
    model.save(MODEL_FILE)
    print(f"The model has been saved to {MODEL_FILE}")
    print(f"The standardised parameters have been saved to {SCALER_FILE}")

if __name__ == '__main__':
    main()
