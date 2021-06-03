# Evaluating Reconfigurable Network Tradeoffs

This repository contains the evaluation of different reconfigurable networks. 

## Getting Started
#### Software Dependencies
Simulation has the following dependencies that should be installed:
1) Gurobi (https://www.gurobi.com/)
Gurobi is needed to optimize the network topology based on predicted traffic matrix. 

2) Netbench (https://github.com/minyee/netbench)
The original Netbench packet-level simulator can be found in (https://github.com/ndal-eth/netbench). TAGO/Netbench is built on top of the Netbench simulator, and it contains more developed modules to support the functionalities required by TAGO. Please follow the steps of setting up TAGO/Netbench, which will be required before proceeding to the next set of instructions. Note that the Gurobi Java module must be linked to the build file.

3) Python 2.7
Python dependencies are: networkx, numpy, gurobipy, math, matplotlib

#### Preliminary
1) Install Gurobi
2) Build Maven, which is needed to build Netbench.
3) Build Netbench.

#### Run
1) Please ensure that TAGO/Netbench is built succesfully before attempting to run the simulations here. 
2) Before running the example simulation, set the environment variable `$NETBENCH_TAGO_DIRECTORY`.
3) Next, we will run an example simulation based on Facebook's published Hadoop cluster traces from [1].
4) Run `python routing_simulator.py`

### NOTE
Please run the simulator from the root directory of this project. The imports are based on relative paths and running the simulator from other directories may fail.


## Description
This is our artifact repository for evaluating both reconfigurable and static network topologies along three main dimensions:
1) Scalability
2) Power Consumption
3) Network Performance

