
# Mininet_data_2.py
import os
import re
import csv
import time
import json
from datetime import datetime

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSKernelSwitch
from mininet.topo import Topo

# auto initialize csv file 
CSV_FILE = 'results.csv'
FIELDNAMES = [
    'exp_id', 'timestamp', 'bw', 'delay', 'loss', 'iw',
    'rtt', 'throughput', 'reward'
]
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()

# default candidate IW values
default_iw_list = [4, 6, 8, 10]
#load next_iw.json mapping 
if os.path.exists('next_iw.json'):
    with open('next_iw.json') as f:
        next_iw_map = json.load(f)
    print("DEBUG: loaded next_iw_map =", next_iw_map, flush=True)
else:
    next_iw_map = {}
    print("DEBUG: no next_iw.json, use default_iw_list =", default_iw_list, flush=True)

# regular expression resolution function
PING_REGEX = re.compile(r"rtt.*= ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms")
def parse_ping_output(output: str) -> float:
    m = PING_REGEX.search(output)
    return float(m.group(2)) if m else None

IPERF_REGEX = re.compile(r"([\d\.]+) (?:M|K)bits/sec")
def parse_iperf_output(output: str) -> float:
    for line in output.splitlines()[::-1]:
        m = IPERF_REGEX.search(line)
        if m:
            return float(m.group(1))
    return None

# retry measurement function
def measure(host, cmd: str, parser, retries: int = 3, wait: float = 0.5):
    
    #run cmd on host,parse output(parser),
    #retry(retries)times,wait(wait)s afterfailed 。
    #return parse value or none 
    for _ in range(retries):
        out = host.cmd(cmd)
        val = parser(out)
        if val is not None:
            return val
        time.sleep(wait)
    return None

#topology definition 
class SingleLinkTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        self.addLink(h1, h2, cls=TCLink)

# experiment function part
def run_experiments(bw_list, delay_list, loss_list,
                    next_iw_map, default_iw_list,
                    alpha=0.8, output_csv=CSV_FILE):
    exp_id = 1
    with open(output_csv, 'a', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        for bw in bw_list:
            for delay in delay_list:
                for loss in loss_list:
                    # Select the IW list based on the current network parameters
                    key = f"({bw}, {delay}, {loss})"
                    iw_list = next_iw_map.get(key) or default_iw_list
                    print(f"[Exp {exp_id}] params={key}, use iw_list={iw_list}", flush=True)
                    print(f"[Exp {exp_id}] START bw={bw}, delay={delay}, loss={loss}", flush=True)

                    # start Mininet
                    topo = SingleLinkTopo()
                    net = Mininet(topo=topo,
                                  link=TCLink,
                                  switch=OVSKernelSwitch,
                                  controller=None )
                    h1, h2 = net.get('h1', 'h2')
                    for sw in net.switches:
                        sw.cmd(f'ovs-vsctl set-fail-mode {sw.name} standalone')
                    # Configuring Link Parameters
                    net.configLinkStatus('h1', 'h2', 'up')
                    h1.cmd(f'tc qdisc add dev h1-eth0 root handle 1: tbf rate {bw}mbit burst 100kb latency 50ms')
                    h1.cmd(f'tc qdisc change dev h1-eth0 root netem delay {delay}ms loss {loss}%')
                    net.start()

                    # start iperf server
                    h2.cmd('iperf -s -p 5001 &')
                    raw_results = []

                    # individually measure each IW 
                    for iw in iw_list:
                        # set initial cwnd 
                        h1.cmd(f'sysctl -w net.ipv4.tcp_initcwnd={iw}')
                        # RTT retry measuremnet
                        rtt_iw = measure(
                            host=h1,
                            cmd=f'ping -c 5 {h2.IP()}',
                            parser=parse_ping_output
                        )
                        if rtt_iw is None:
                            print(f"[Exp {exp_id}] \n{h1.cmd(f'ping -c 5 {h2.IP()}')}")
                        # throughput retry measurement 
                        tp_iw = measure(
                            host=h1,
                            cmd=f'iperf -c {h2.IP()} -p 5001 -n {iw*1460} -w {iw*1460}',
                            parser=parse_iperf_output
                        )
                        if tp_iw is None:
                            print(f"[Exp {exp_id}] org iperf output:\n{h1.cmd(f'iperf -c {h2.IP()} -p 5001 -n {iw*1460} -w {iw*1460}')}")
                        #if any measurement fails, skip
                        if rtt_iw is None or tp_iw is None:
                            print(f"[Exp {exp_id}] IW={iw} Measurement failed,skip ", flush=True)
                            continue
                        raw_results.append((iw, rtt_iw, tp_iw))

                    # if there are no valid results, skip this experiment
                    if not raw_results:
                        print(f"[Exp {exp_id}] no valid datas, skip ", flush=True)
                        h2.cmd('pkill iperf')
                        net.stop()
                        time.sleep(1)
                        exp_id += 1
                        continue

                    # Normalise and write to CSV
                    tp_max = max(tp for _, _, tp in raw_results)
                    rtt_min = min(rtt for _, rtt, _ in raw_results)
                    for iw, rtt_iw, tp_iw in raw_results:
                        reward = alpha * (tp_iw / tp_max) + (1 - alpha) * (rtt_min / rtt_iw)
                        print(f"--> exp_id={exp_id} IW={iw} rtt={rtt_iw:.2f} tp={tp_iw:.2f} reward={reward:.3f}", flush=True)
                        writer.writerow({
                            'exp_id': exp_id,
                            'timestamp': datetime.now().isoformat(),
                            'bw': bw,
                            'delay': delay,
                            'loss': loss,
                            'iw': iw,
                            'rtt': rtt_iw,
                            'throughput': tp_iw,
                            'reward': reward
                        })
                        exp_id += 1

                    # cleanup
                    h2.cmd('pkill iperf')
                    net.stop()
                    time.sleep(1)

# script entry point,network parameters and next_iw_map are defined here
if __name__ == '__main__':
    run_experiments(
        bw_list=[3,6,9],
        delay_list=[10,30,100],
        loss_list=[0,1,5],
        next_iw_map=next_iw_map,
        default_iw_list=default_iw_list,
        alpha=0.8,
        output_csv=CSV_FILE
    )
