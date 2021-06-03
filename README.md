# Evaluating Reconfigurable Network Tradeoffs

This repository contains the source codes needed to reproduce our evaluation of reconfigurable and static network topologies. 

## Getting Started
### Software Dependencies
Our repository has the following dependencies that must be installed:

#### 1. Gurobi (https://www.gurobi.com/)
Installing Gurobi is necessary prior to running the evaluations in this repository. This is because several points in our analyses point to the Gurobi library when running traffic demand-based topology optimizations. 

#### 2. Netbench (https://github.com/minyee/netbench)
The original Netbench packet-level simulator can be found in (https://github.com/ndal-eth/netbench). Our version of Netbench is built on top of the original Netbench simulator, but it also contains more developed modules to support the functionalities required for simulating reconfigurable networks. Please follow the steps in building Netbench. Note that the Gurobi Java module must be linked to the build file.

#### 3. Python 2.7
Python dependencies are: networkx, numpy, gurobipy, math, matplotlib.

## Description of subdirectories.
This is our artifact repository for evaluating both reconfigurable and static network topologies along three main metrics:

#### 1. Scalability
#### 2. Power Consumption
#### 3. Network Throughput Performance

We have similarly created 3 sub-directories: `performance_evaluation`, `power_consumption_analysis`, and `topology_analysis`, each of which are self-contained subdirectories to recreate the analyses on scalability, power consumption, and network throughput performance, respectively, in our paper. Each sub-directory contains its own README, which details how the analyses in the paper can be recreated.

### NOTE
When running each analyses, please run from the root directory corresponding to each analysis, as we utilize relative path imports, and thus running the python scripts from different directories could cause unexpected errors. 