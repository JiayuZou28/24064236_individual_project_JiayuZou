
import subprocess
import os
import sys
import time


# Configuration item: stop after reaching the number of data
TARGET_LINES = 5500 # Accumulate up to N samples and stop

# Run a shell command and throw an exception if it fails.

def run(cmd, use_sudo=False):
    
    #cmd: list[str] ['python3','select_best_iw.py']
    #use_sudo: If True, prefix the command with ['sudo','-E'].
    
    full = (['sudo','-E'] if use_sudo else []) + cmd
    print(">> Running:", " ".join(full))
    subprocess.run(full, check=True)


# cycle through data collection iterations

def main():
    iteration = 1

   
    while True:
        print(f"\n=== Iteration {iteration} ===\n")

        # 1) Call Mininet_data_2.py to collect a batch of data and append it to results.csv.
        #    Requires root privileges to run mininet
        run(['python3', 'Mininet_data_2.py'], use_sudo=True)

        # 2) Select best_iw.json based on latest results.csv
        run(['python3', 'select_best_iw.py'])

        # 3) Update next_iw.json with sliding window algorithm
        run(['python3', 'slide_window.py'])

        # Rename next_iw.json to current_iw.json
        import shutil
        shutil.copyfile('next_iw.json', 'current_iw.json')

        # Check how many rows of data are already in results.csv (minus the header)
        if os.path.exists('results.csv'):
            with open('results.csv') as f:
                total = sum(1 for _ in f)
            data_rows = max(0, total - 1)
        else:
            data_rows = 0

        print(f">>> Collected {data_rows} data rows so far.\n")

        if data_rows >= TARGET_LINES:
            print(f"Reached target of {TARGET_LINES} samples, stopping.")
            break

        iteration += 1
        

    print("\n*** Data collection complete! ***")
    print(f"results.csv contains {data_rows} samples.")
    print("best_iw..json and next_iw.json have been updated.")
if __name__ == '__main__':
    main()
