import os, sys
import traffic_events
from network_topology import *
import utilities

####################################################################################################
# Simulation parameters 
####################################################################################################
# BASE DIRECTORY FOR ALL SIMULATION AND RESULTS FILES
BASE_DIRECTORY = os.getenv('NETBENCH_HOME') + "/temp/multi_eval"
if not os.path.isdir(BASE_DIRECTORY):
	os.mkdir(BASE_DIRECTORY)

# Reconfiguration related
# RECONFIGURATION_TYPE options include preplanned, on_demand, rotation, static
# RECONFIGURATION_GRANULARITY options include pod, tor, fattree

# Topology-related
EPS_RADIX = 32 # options include 16, 24, 32, 48, 64
TOR_EPS_RADIX = 64
OVERSUBSCRIPTION_RATIO = (4, 1) # options include (2, 1), (3, 1), (4, 1), ..., etc.

# Network hardware related
INPUT_QUEUE_BUFFER_SIZE_BYTES = 20000 # ignored if protocol is TCP-based
OUTPUT_QUEUE_BUFFER_SIZE_BYTES = 20000 # always used
CONGESTION_THRESHOLD_BYTES = 5000 # ignored if protocol is Infiniband-based
NETWORK_LINK_LATENCY_NS = 30
SERVER_LINK_LATENCY_NS = 10
NETWORK_LINK_BANDWIDTH_GBPS = 100

GENERATED_CONFIGS = []

# Reconfiguration timing related
RECONFIGURATION_PERIODS_NS = [1000, 10000, 100000]

property_dictionary = {"num_vcs": 2,
						"input_queue_size_bytes": INPUT_QUEUE_BUFFER_SIZE_BYTES,
						"output_port_queue_size_bytes": OUTPUT_QUEUE_BUFFER_SIZE_BYTES,
						"network_link_delay_ns": NETWORK_LINK_LATENCY_NS,
						"network_link_bw_gbps": NETWORK_LINK_BANDWIDTH_GBPS,
						"server_link_delay_ns": SERVER_LINK_LATENCY_NS,
						"ecmp_fraction": 0.6,
						"reconfiguration_latency_ns": 0,
						}

## Generates a bash script that automates the running of all the simulations.
def generate_bash_script(netbench_config_files_list):
	# Construct the string builder
	str_builder = "cd $NETBENCH_HOME\n\n"
	netbench_execution_prefix = "java -jar -ea NetBench.jar "
	for config_filename in netbench_config_files_list:
		str_builder += (netbench_execution_prefix + config_filename + "\n")
	# Write the script to the .sh file
	with open("automated_execution.sh", "w+") as f:
		f.write(str_builder)
	return

def get_topology_params_based_on_app(app_name):
	topology_params = {}
	if app_name == "MiniDFT":
		topology_params["fattree"] = (23, 11)
		topology_params["prn"] = (23, 11)
		topology_params["trn"] = 122
		topology_params["exp"] = 122
	elif app_name in ("AMG", "AMR"):
		topology_params["fattree"] = (14, 8)
		topology_params["prn"] = (14, 8)
		topology_params["trn"] = 108
		topology_params["exp"] = 108
	return topology_params

'''
Sets up the experiment based on parameters.
'''
if __name__ == "__main__":
	# Step 1: Read in the traffic probability file, using the maximum rank as the number of nodes required.
	app_traffic_probabilities = {}
	app_nnodes = {}
	for app in ["AMG", "AMR", "MiniDFT"]:
		traffic_probabilities, nnodes = utilities.read_traffic_probability_file("traffic_probabilities/{}.txt".format(app))
		app_traffic_probabilities[app] = traffic_probabilities
		app_nnodes[app] = nnodes
	# Step 2: Create the directories.
	for app in ["AMG", "AMR", "MiniDFT"]:
		if not os.path.isdir("{}/{}".format(BASE_DIRECTORY, app)):
			os.mkdir("{}/{}".format(BASE_DIRECTORY, app))
		for topology_name in ["fattree", "prn", "trn", "exp"]:
			if not os.path.isdir("{}/{}/{}".format(BASE_DIRECTORY, app, topology_name)):
				os.mkdir("{}/{}/{}".format(BASE_DIRECTORY, app, topology_name))
	# Step 3: Generate the .property files and other requisite files needed for simulations.
	for app in ["AMG", "AMR", "MiniDFT"]:
		# Compute the flow arrivals based on each app's number of nodes required.
		nnodes = app_nnodes[app]

		num_arrivals_per_sec_list = []
		for load in [10, 30, 50, 70, 90]:
			load_frac = float(load)/100
			num_flow_arrivals_per_sec = int((load_frac * nnodes * NETWORK_LINK_BANDWIDTH_GBPS * 1E9 / 8. / 2434900))
			num_arrivals_per_sec_list.append(num_flow_arrivals_per_sec)

		topology_params = get_topology_params_based_on_app(app)
		fattree_topology = fattree_network_topology.FatTreeNetworkTopology(EPS_RADIX, topology_params["fattree"][0], topology_params["fattree"][1])
		exp_topology = static_expander_network_topology.StaticExpanderNetworkTopology(TOR_EPS_RADIX, topology_params["exp"], num_servers_per_tor=EPS_RADIX)
		trn_topology = sparse_reconfigurable_network_topology.SparseReconfigurableNetworkTopology(TOR_EPS_RADIX, topology_params["trn"], num_servers_per_tor=EPS_RADIX)
		prn_topology = dense_reconfigurable_network_topology.DenseReconfigurableNetworkTopology(EPS_RADIX, topology_params["prn"][0], topology_params["prn"][0], oversubscription_ratio=OVERSUBSCRIPTION_RATIO)
		# Wire all topology instances.
		fattree_topology.wire_network()
		exp_topology.wire_network()
		trn_topology.wire_network()
		prn_topology.wire_network()
		for topology, topology_name in zip([prn_topology, trn_topology, fattree_topology, exp_topology], ["prn", "trn", "fattree", "exp"]):
			output_base_dir = "{}/{}/{}".format(BASE_DIRECTORY, app, topology_name)
			# Set the number of reconfigurable uplinks per pod
			property_dictionary["num_reconfigurable_uplinks_per_pod"] = topology.get_num_reconfigurable_uplinks_per_pod()
			# For each topology, get its own shifted traffic probability file, initial topology file, pod id file, wcmp routing weights name
			# Topology file
			topology_filename = "{}/{}/{}/initial_topology.topology".format(BASE_DIRECTORY, app, topology_name)
			topology_file_string = topology.generate_topology_file_string()
			with open(topology_filename, "w+") as f:
				f.write(topology_file_string)
			# Pod id map file
			pod_id_map_filename = "{}/{}/{}/pod_id_map.txt".format(BASE_DIRECTORY, app, topology_name)
			pod_id_map_string = topology.generate_pod_id_file_string()
			with open(pod_id_map_filename, "w+") as f:
				f.write(pod_id_map_string)
			# WCMP routing weights file
			routing_path_split_ratio_filename = "{}/{}/{}/initial_wcmp_weights.txt".format(BASE_DIRECTORY, app, topology_name)
			routing_path_split_ratio_string = topology.generate_initial_interpod_routing_weights_string()	
			with open(routing_path_split_ratio_filename, "w+") as f:
				f.write(routing_path_split_ratio_string)
			# Traffic probability file
			reshifted_traffic_prob_filename = "{}/{}/{}/flow_arrivals.txt".format(BASE_DIRECTORY, app, topology_name)
			reshifted_traffic_prob_str = topology.generate_traffic_events_string(app_traffic_probabilities[app])
			with open(reshifted_traffic_prob_filename, "w+") as f:
				f.write(reshifted_traffic_prob_str)
			# Iterate over all the loads
			for load_level, num_arrivals_per_sec in zip([10, 30, 50, 70, 90], num_arrivals_per_sec_list):
				load_name = "load{}perc".format(load_level)
				if topology_name == "prn":
					property_dictionary["reconfiguration_granularity"] = "pod"
					property_dictionary["reconfiguration_type"] = "on_demand"
					for reconfig_period_ns in RECONFIGURATION_PERIODS_NS:
						reconfig_period_str = utilities.extract_timing_string(reconfig_period_ns)
						property_dictionary["reconfiguration_period_ns"] = reconfig_period_ns
						# Write the .properties on demand
						config_file_strings = utilities.write_simulation_configuration_file(output_base_dir,
																				"rp" + reconfig_period_str,
																				topology_filename, 
																				reshifted_traffic_prob_filename, 
																				routing_path_split_ratio_filename,  
																				pod_id_map_filename, 
																				num_arrivals_per_sec,
																				property_dictionary)
						simulation_config_filename = "{}/{}/{}/{}_rp{}.properties".format(BASE_DIRECTORY, app, topology_name, load_name, reconfig_period_str)
						with open(simulation_config_filename, "w+") as f:
							f.write(config_file_strings)
						GENERATED_CONFIGS.append(simulation_config_filename)
				elif topology_name == "trn":
					property_dictionary["reconfiguration_granularity"] = "tor"
					for reconfig_period_ns in RECONFIGURATION_PERIODS_NS:
						reconfig_period_str = utilities.extract_timing_string(reconfig_period_ns)
						property_dictionary["reconfiguration_period_ns"] = reconfig_period_ns
						# Write the .properties for on_demand
						property_dictionary["reconfiguration_type"] = "on_demand"
						config_file_strings = utilities.write_simulation_configuration_file(output_base_dir,
																				"rp" + reconfig_period_str + "_demand",
																				topology_filename, 
																				reshifted_traffic_prob_filename, 
																				routing_path_split_ratio_filename,  
																				pod_id_map_filename, 
																				num_arrivals_per_sec,
																				property_dictionary)
						simulation_config_filename = "{}/{}/{}/{}_rp{}_demand.properties".format(BASE_DIRECTORY, app, topology_name, load_name, reconfig_period_str)
						with open(simulation_config_filename, "w+") as f:
							f.write(config_file_strings)
						GENERATED_CONFIGS.append(simulation_config_filename)
						# Write the .properties for rotation
						property_dictionary["reconfiguration_type"] = "rotation"
						config_file_strings = utilities.write_simulation_configuration_file(output_base_dir,
																				"rp" + reconfig_period_str + "_rotation",
																				topology_filename, 
																				reshifted_traffic_prob_filename, 
																				routing_path_split_ratio_filename,  
																				pod_id_map_filename, 
																				num_arrivals_per_sec,
																				property_dictionary)
						simulation_config_filename = "{}/{}/{}/{}_rp{}_rotate.properties".format(BASE_DIRECTORY, app, topology_name, load_name, reconfig_period_str)
						with open(simulation_config_filename, "w+") as f:
							f.write(config_file_strings)
						GENERATED_CONFIGS.append(simulation_config_filename)
				else:
					if topology_name == "exp":
						property_dictionary["reconfiguration_granularity"] = "tor"
					else:
						property_dictionary["reconfiguration_granularity"] = "fattree"
					property_dictionary["reconfiguration_type"] = "static"
					# Static topologies
					# Write the .properties
					config_file_strings = utilities.write_simulation_configuration_file(output_base_dir,
																			"results",
																			topology_filename, 
																			reshifted_traffic_prob_filename, 
																			routing_path_split_ratio_filename,  
																			pod_id_map_filename, 
																			num_arrivals_per_sec,
																			property_dictionary)
					simulation_config_filename = "{}/{}/{}/{}.properties".format(BASE_DIRECTORY, app, topology_name, load_name)
					with open(simulation_config_filename, "w+") as f:
						f.write(config_file_strings)
					GENERATED_CONFIGS.append(simulation_config_filename)
	generate_bash_script(GENERATED_CONFIGS)
	


