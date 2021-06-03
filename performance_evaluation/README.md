## Performance Evaluation

The performance evaluation is self-contained.
The evaluation compares the maximize attainable network size, measured in terms of total number of server end points, different network topologies can support. 
We primarily compare the scalability between PRN, TRN, static expander and fat tree. 

## To run the Netbench simulations from scratch

1) Set the environment variable `NETBENCH_HOME` to point to the directory where Netbench is located, using `export NETBENCH_HOME={netbench_dir}`.

2) Generate netbench simulation files by running `python generate_netbench_configs.py` from this directory.

3) Add execution permision to the generated shell script by running: `chmod +x automated_execution.sh`.

4) Run `./automated_execution.sh`, which will initialize all the simulations automatically.