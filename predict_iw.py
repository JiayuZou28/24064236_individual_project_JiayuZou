
import sys, json, numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

# 1) Parameter checking
if len(sys.argv) != 6:
    print("Usage: python3 predict_iw.py <bw> <delay> <loss> <rtt> <throughput>")
    sys.exit(1)
bw, delay, loss, rtt, tp = map(float, sys.argv[1:6])

# 2) Reading and standardising features
try:
    # 2.1) Normalise RTT and TP
    df = pd.read_csv('results.csv')
    tp_max  = df[(df.bw==bw)&(df.delay==delay)&(df.loss==loss)]['throughput'].max()
    rtt_min = df[(df.bw==bw)&(df.delay==delay)&(df.loss==loss)]['rtt'].min()
    tp_norm  = tp / tp_max
    rtt_norm = rtt_min / rtt
except Exception:
    # Any error returns a default IW
    print(10)
    sys.exit(0)

# 3) Loading standardised parameters
with open('scaler.json') as f:
    scaler = json.load(f)
mean = np.array(scaler['mean'], dtype=np.float32)
std  = np.array(scaler['std'],  dtype=np.float32)

# 4) Constructing and standardising inputs
x_raw = np.array([[bw, delay, loss, rtt_norm, tp_norm]], dtype=np.float32)
x = (x_raw - mean) / std

# 5) Load the model and predict
model = load_model('predict_model.h5',compile=False)
pred  = model.predict(x, verbose=0)[0,0]

# 6) Output the nearest integer IW
iw_rec = int(round(pred))
print("Recommend IW = ",iw_rec)
