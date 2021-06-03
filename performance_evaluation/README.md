## Performance Evaluation
This directory is dedicated to recreating the network throughput performance analyses in Section 5 of our paper.
We primarily compare the network performances of PRN, TRN, static expander and fat tree. The performance evaluation is self-contained; all the source and data files required to generate the Netbench simulation files are contained here.

#### Description of files and directories.
1) `network_topology/` - Contains the different network topology Python classes.

2) `traffic_probabilities/` - Contains the summarized PDF of the traffic communication pattern between server ids for different applications.

3) `generate_netbench_configs.py` - Python script used for generating the Netbench simulation configuration files.

4) `utilities.py` - Contains auxilary functions used in generating the Netbench simulation files.

## To run the Netbench simulations from scratch.

1) Set the environment variable `NETBENCH_HOME` to point to the directory where Netbench is located, using `export NETBENCH_HOME={netbench_dir}`.

2) Generate netbench simulation files by running `python generate_netbench_configs.py` from this directory.

3) Add execution permision to the generated shell script by running: `chmod +x automated_execution.sh`.

4) Run `./automated_execution.sh`, which will initialize all the simulations automatically.
