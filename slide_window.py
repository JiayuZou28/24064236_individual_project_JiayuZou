
import json
import os

# Parameter: Step size Δ
DELTA = 2

# Default IW window 
default_arms = [2,4,6,8]

# filename
BEST_IW_FILE = 'best_iw.json'
CUR_IW_FILE  = 'current_iw.json'
NEXT_IW_FILE = 'next_iw.json'

# 1) read best_iw.json
with open(BEST_IW_FILE, 'r') as f:
    best_map = json.load(f)   # { "(bw, delay, loss)": {"best_iw":..., "ucb":{...}}, ... }

# 2) Read or initialisecurrent_iw.json
if os.path.exists(CUR_IW_FILE):
    with open(CUR_IW_FILE, 'r') as f:
        current_map = json.load(f)  # { "(bw, delay, loss)": [iw1, iw2, ...], ... }
else:
    # If it doesn't exist, initialise it with a default arm list
    current_map = { cond: default_arms[:] for cond in best_map.keys() }

# 3) sliding window
next_map = {}
for cond, info in best_map.items():
    best_iw = info['best_iw']
    arms    = current_map.get(cond, default_arms[:])
    min_iw, max_iw = min(arms), max(arms)

    if best_iw >= max_iw:
        # right shift
        updated = [iw + DELTA for iw in arms]
    elif best_iw <= min_iw:
        # left shift
        updated = [iw - DELTA for iw in arms]
    else:
        # remain unchanged
        updated = arms

    # Restrictions on lower/upper boundaries
    updated = [max(2, iw) for iw in updated]      # IW min 2
    updated = [min(50, iw) for iw in updated]    # IW max 50

    next_map[cond] = updated
    print(f"{cond}: {arms} -> {updated}  (best={best_iw})")

# 4) write in next_iw.json
with open(NEXT_IW_FILE, 'w') as f:
    json.dump(next_map, f, indent=2, ensure_ascii=False)

print(f"\nThe next round of IW listings have been written {NEXT_IW_FILE}")
