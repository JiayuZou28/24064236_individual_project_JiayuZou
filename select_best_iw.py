
import pandas as pd
import math
import json

# Hyperparameter
GAMMA = 0.9    # discounted factor γ
E    = 0.1    # UCB explortation factor ξ
C     = 0.9    # reward upper bound，for padding 

def discount_ucb(rewards, arms, gamma=GAMMA, E=E, C=C):
    
    #rewards: list of tuples (iw, reward) chronological order
    #arms:    list of all possible IW
    #return each arm 的 UCB account dict{arm: score}
    
    # Initialising discount accumulation and counting
    X = {a: 0.0 for a in arms}  # Discount Rewards Accumulation
    D = {a: 0.0 for a in arms}  # Discount Selection Count

    # Update discounts and counts online
    for arm, r in rewards:
        # Discount all arm 
        for a in arms:
            X[a] *= gamma
            D[a] *= gamma
        # Then accumulate the current arm
        X[arm] += r
        D[arm] += 1

    # Calculate the total number of discount "samples"
    total_D = sum(D.values()) or 1.0

    # Calculate the UCB for each arm
    ucb = {}
    for a in arms:
        if D[a] > 0:
            mean = X[a] / D[a]
            padding = 2 * C * math.sqrt(E * math.log(total_D) / D[a])
            ucb[a] = mean + padding
        else:
            # If the arm has never been tried, make it infinite to ensure that priority is given to exploration
            ucb[a] = float('inf')
    return ucb

def main():
    # 1) Read data
    df = pd.read_csv('results.csv', parse_dates=['timestamp'])

    # 2) cluster by network condition
    groups = df.groupby(['bw', 'delay', 'loss'])

    output = {}
    for params, group in groups:
        # Sort by time to ensure correct chronology
        group = group.sort_values('timestamp')
        arms = sorted(group['iw'].unique())
        rewards = list(zip(group['iw'], group['reward']))

        # 3) Calculate the UCB score for each arm
        ucb_scores = discount_ucb(rewards, arms)

        # 4) Select the arm with the highest score
        best_iw = max(ucb_scores, key=ucb_scores.get)

        output[str(params)] = {
            'best_iw': int(best_iw),
            'ucb': {str(k): float(v) for k,v in ucb_scores.items()}
        }

        print(f"params={params} → best_iw={best_iw}")

    # 5) Write JSON to be loaded by subsequent scripts
    with open('best_iw.json', 'w') as fp:
        json.dump(output, fp, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
