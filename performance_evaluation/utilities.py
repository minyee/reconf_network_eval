import sys, os

## Given a long representing the nanoseconds, returns a string of the time.
def extract_timing_string(nanoseconds):
	if nanoseconds < 1000:
		# nanoseconds regime
		entry = nanoseconds
		return "{}ns".format(entry)
	elif nanoseconds >= 1000 and nanoseconds < 1000000:
		# microseconds regime
		entry = nanoseconds / 1000
		return "{}us".format(entry)
	elif nanoseconds >= 1000000 and nanoseconds < 1000000000:
		# milliseconds regime
		entry = nanoseconds / 1000000
		return "{}ms".format(entry)
	else:
		# seconds regime
		entry = nanoseconds / 1000000000
		return "{}s".format(entry)

# Reads in a traffic probability file.
def read_traffic_probability_file(prob_filename):
	traffic_probabilities = {}
	max_index = -1
	with open(prob_filename, "r") as f:
		for line in f:
			if line[0] == "#":
				continue
			else:
				str_list = line.split(',')
				src, dst, prob = int(str_list[1]), int(str_list[2]), float(str_list[3])
				max_index = max(max_index, max(src, dst))
				traffic_probabilities[(src, dst)] = prob
	return traffic_probabilities, max_index + 1

def write_simulation_configuration_file(output_base_dir,
										output_subdir,
										initial_topology_filename, 
										traffic_probability_filename, 
										initial_routing_weights_filename,  
										pod_ids_filename,
										flow_arrival_per_sec,
										network_property_dictionary):
	# Topology file
	str_builder = "# Topology\n"
	str_builder += "scenario_topology_file={}\n".format(initial_topology_filename)
	str_builder += "\n"
	# Run info 
	str_builder += "# Run Info\n"
	str_builder += "run_folder_name={}\n".format(output_subdir)
	str_builder += "run_folder_base_dir={}\n".format(output_base_dir)
	str_builder += "run_time_s=2\n"
	str_builder += "enable_smooth_rtt=false\n"
	str_builder += "seed=8278897294\n"
	str_builder += "check_link_bidirectionality=false\n"
	str_builder += "\n"

	# Enable bandwidth steering during simulation
	str_builder += "# Reconfig steering\n"
	if network_property_dictionary["reconfiguration_type"] in ("on_demand", "rotation"):
		str_builder += "reconfiguration_type={}\n".format(network_property_dictionary["reconfiguration_type"])
		str_builder += "reconfiguration_period_ns={}\n".format(network_property_dictionary["reconfiguration_period_ns"])
	str_builder += "link_reconfig_latency_ns=0\n"
	str_builder += "num_reconfigurable_uplinks={}\n\n".format(network_property_dictionary["num_reconfigurable_uplinks_per_pod"])
	# Network device
	str_builder += "# Network Device\n"
	str_builder += "transport_layer=infiniband\n"
	if network_property_dictionary["reconfiguration_granularity"] == "tor" and network_property_dictionary["reconfiguration_type"] == "static":
		str_builder += "network_device=valiant_ecmp_hybrid_infiniband_switch\n"
		str_builder += "network_device_routing=simple_infiniband_ecmp\n"
		str_builder += "ecmp_fraction={}\n".format(network_property_dictionary["ecmp_fraction"])
	else:
		str_builder += "network_device=reconfigurable_infiniband_switch\n"
		str_builder += "network_device_routing=reconfigurable_infiniband_switch_routing\n"
	str_builder += "infiniband_input_queue_size_bytes={}\n".format(network_property_dictionary["input_queue_size_bytes"])
	str_builder += "num_vcs={}\n".format(network_property_dictionary["num_vcs"]).lower()

	str_builder += "stateful_load_balancing=false\n"
	str_builder += "enable_packet_spraying=true\n"
	str_builder += "wcmp_path_weights_filename={}\n".format(initial_routing_weights_filename)
	str_builder += "pod_id_filename={}\n".format(pod_ids_filename)
	str_builder += "network_device_intermediary=identity\n"
	str_builder += "\n"

	#injection_queue_multiplier = max(1, round(float(injection_link_capacity_gbps)/float(network_link_capacity_gbps)))
	#injection_queue_multiplier = int(injection_queue_multiplier)
	# Link & output port
	str_builder += "# Output port\n"
	if network_property_dictionary["reconfiguration_granularity"] == "tor" and network_property_dictionary["reconfiguration_type"] == "static":
		str_builder += "output_port=simple_infiniband_output_port\n"
	else:
		str_builder += "output_port=reconfigurable_infiniband_output_port\n"
	str_builder += "output_port_max_queue_size_bytes={}\n".format(network_property_dictionary["output_port_queue_size_bytes"])

	str_builder += "# Link\n"
	str_builder += "link=reconfigurable_link\n"
	str_builder += "link_delay_ns={}\n".format(network_property_dictionary["network_link_delay_ns"]) # per link delay
	str_builder += "server_link_delay_ns={}\n".format(network_property_dictionary["server_link_delay_ns"]) # per link delay
	str_builder += "link_bandwidth_bit_per_ns={}\n".format(network_property_dictionary["network_link_bw_gbps"])
	str_builder += "\n"

	#Traffic
	str_builder += "# Traffic\n"
	## Traffic probability
	str_builder += "traffic=poisson_arrival\n"	
	str_builder += "traffic_lambda_flow_starts_per_s={}\n".format(flow_arrival_per_sec)
	str_builder += "traffic_flow_size_dist=pfabric_web_search_upper_bound\n"
	str_builder += "traffic_probabilities_file={}\n\n".format(traffic_probability_filename)
	return str_builder 