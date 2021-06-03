import numpy as np
import networkx as nx
from network_topology import *

# In this model, the reconfigurable network is pod-reconfigurable. Each pod is built as a
# full-bisection-bandwidth two layer fabric, with an aggregation layer and a ToR layer. 
# The actual number of aggregation switches is actually identical to the number of ToRs inside a 
# pod, but we logically collapse all aggregation switches to 1. In other words, each pod must only have 
# one aggregation switch.
class DenseReconfigurableNetworkTopology(NetworkTopology):
	def __init__(self, eps_radix, num_pods, num_tors_per_pod, oversubscription_ratio=(1,1)):
		NetworkTopology.__init__(self, eps_radix)
		self.num_pods = num_pods
		self.num_tors_per_pod = num_tors_per_pod
		self.oversubscription_ratio = (float(oversubscription_ratio[0]), float(oversubscription_ratio[1]))
		self.num_reconfigurable_uplink_per_pod = int(self.num_tors_per_pod * (self.eps_radix / 2) * (float(self.oversubscription_ratio[1]) / float(self.oversubscription_ratio[0])))
		assert(self.num_reconfigurable_uplink_per_pod > self.num_pods - 1)
	
	# Wires up the network in its entirety, and sets up the various topological properties.
	def wire_network(self):
		# Step 1: Intialize the servers and the switches first if all pods, while also wiring things together
		for pod_id in range(self.num_pods):
			# Step 1.1 : Initialize the pod aggregation switch, and there should only be 1 aggregation switch per pod.
			aggregation_device_id = pod_id	# Id of the aggregation switch
			self.device_id_to_pod_id_map[aggregation_device_id] = pod_id
			self.adjacency_list[aggregation_device_id] = {}
			# Step 1.2 : Initialize the ToR switches. Note that the i-th ToR of a pod j has device id: num_pods + j * tors_per_pod  + i
			for tor in range(self.num_tors_per_pod):
				tor_device_id = self.num_pods + (pod_id * self.num_tors_per_pod) + tor
				# Initialize the ToR's device entry in the adjacency list
				self.adjacency_list[tor_device_id] = {}
				# Next, connect the ToR with the aggregation switch
				self.adjacency_list[tor_device_id][aggregation_device_id] = self.eps_radix / 2
				self.adjacency_list[aggregation_device_id][tor_device_id] = self.eps_radix / 2
				# Step 1.3 : Initialize the servers and connect them with the ToRs. Note that each ToR in the topology file connects to only 1 server, though
				# 			 each server is a logical representation for eps_radix / 2 actual servers. We do this to save space and runtime later in netbench.
				server_device_id = self.num_pods * (1 + self.num_tors_per_pod) + (pod_id * self.num_tors_per_pod) + tor
				self.adjacency_list[server_device_id] = {}
				self.adjacency_list[server_device_id][tor_device_id] = self.eps_radix / 2
				self.adjacency_list[tor_device_id][server_device_id] = self.eps_radix / 2
				# Then add the tor server and aggregation switches into the device id to pod id map
				self.device_id_to_pod_id_map[server_device_id] = pod_id
				self.device_id_to_pod_id_map[tor_device_id] = pod_id
		# Step 2: Wire up the initial inter-pod logical topology between aggregation switches, assuming uniform connectivity
		# Step 2.1: Derive the logical interpod adjacency matrix
		uniform_interpod_logical_topology = self.__compute_uniform_interpod_connectivity()
		# Step 2.2: Modify the adjacency list to realize uniform interpod logical topology
		for src_pod in range(self.num_pods):
			for dst_pod in range(self.num_pods):
				link_count = uniform_interpod_logical_topology[src_pod][dst_pod]
				self.adjacency_list[src_pod][dst_pod] = link_count
		return

	# Generates the traffic events in the form of strings.
	def generate_traffic_events_string(self, traffic_probability):
		str_builder = ""
		virtual_servers_offset = self.num_pods * (1 + self.num_tors_per_pod)
		num_servers_per_tor = self.eps_radix / 2
		index = 0
		prob_sum = 0
		for src, dst in traffic_probability:
			src_virtual = virtual_servers_offset + src / num_servers_per_tor
			dst_virtual = virtual_servers_offset + dst / num_servers_per_tor
			assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list)
			if src_virtual != dst_virtual:
				prob_sum += traffic_probability[(src, dst)]
		for src, dst in traffic_probability:
			src_virtual = virtual_servers_offset + src / num_servers_per_tor
			dst_virtual = virtual_servers_offset + dst / num_servers_per_tor
			assert(src_virtual in self.adjacency_list and dst_virtual in self.adjacency_list)
			if src_virtual != dst_virtual:
				str_builder += "{},{},{},{}\n".format(index, src_virtual, dst_virtual, traffic_probability[(src, dst)] / prob_sum)
				index += 1
		return str_builder

	# Generates the initial WCMP configuration for a uniform pod-to-pod logical topology.
	def generate_initial_interpod_routing_weights_string(self):
		str_builder = ""
		per_path_ratio = float(1) / (self.num_pods - 1)
		for src_pod in range(self.num_pods):
			for dst_pod in range(self.num_pods):
				if src_pod != dst_pod:
					str_builder += "{},{},{},{}\n".format(2, per_path_ratio, src_pod, dst_pod)
					for intermediate_pod in range(self.num_pods):
						if intermediate_pod != src_pod and intermediate_pod != dst_pod:
							str_builder += "{},{},{},{},{}\n".format(3, per_path_ratio, src_pod, intermediate_pod, dst_pod)
		return str_builder

	# Generates the topology string used for netbench.
	def generate_topology_file_string(self):
		prefix = ""
		topol_str = ""
		num_edges = 0
		for switch_id in self.adjacency_list:
			for target_switch_id in self.adjacency_list[switch_id]:
				link_count = self.adjacency_list[switch_id][target_switch_id]
				num_edges += link_count
				for _ in range(link_count):
					topol_str += "{} {}\n".format(switch_id, target_switch_id)
		num_switches = len(self.adjacency_list)
		prefix += ("|V|={}".format(num_switches) + "\n")
		prefix += ("|E|={}".format(num_edges) + "\n")
		prefix += "ToRs=incl_range({},{})\n".format(self.num_pods, self.num_pods * (1 + self.num_tors_per_pod) - 1)
		prefix += "Servers=incl_range({},{})\n".format(self.num_pods * (1 + self.num_tors_per_pod), self.num_pods * (1 + (2 * self.num_tors_per_pod)) - 1)
		prefix += "Switches=incl_range({},{})\n\n".format(0, self.num_pods - 1) # For the aggregation switches only
		return prefix + topol_str

	# Retrieves the name of this topology, summarizing some of the essential parameters. Used to create topology directory and filename.
	def get_name(self):
		network_name_prefix = "pod_eps{}_".format(self.eps_radix)
		oversubscription_ratio_str = "{}to{}".format(int(self.oversubscription_ratio[0]), int(self.oversubscription_ratio[1]))
		num_pods_str = "np{}".format(self.num_pods)
		num_tors_per_pod_str = "ntpp{}".format(self.num_tors_per_pod)
		network_name = "{}_{}_{}".format(num_pods_str, num_tors_per_pod_str, oversubscription_ratio_str)
		return network_name_prefix + network_name

	def get_num_reconfigurable_uplinks_per_pod(self):
		return self.num_reconfigurable_uplink_per_pod

	'''
	###########################################################################################################################
	###########################################################################################################################
	Internal Methods used by the class.
	###########################################################################################################################
	###########################################################################################################################
	'''
	## Internal function used to compute the uniform interpod logical topology.
	def __compute_uniform_interpod_connectivity(self):
		uniform_interpod_logical_topology = np.zeros((self.num_pods, self.num_pods), dtype=int)
		per_pod_pair_num_links = self.num_reconfigurable_uplink_per_pod / (self.num_pods - 1)
		for i in range(self.num_pods):
			for j in range(self.num_pods):
				if i != j:
					uniform_interpod_logical_topology[i][j] = per_pod_pair_num_links
		leftover_links = self.num_reconfigurable_uplink_per_pod - (per_pod_pair_num_links * (self.num_pods - 1))
		assert(leftover_links >= 0 and leftover_links < self.num_pods - 1)
		if leftover_links > 0:
			# Run the random bipartite matching to fill in the remaining links
			dummy_src = 0
			dummy_sink = 2 * self.num_pods + 1
			G = nx.DiGraph()
			edges = []
			# Add edges from src to first layer nodes and from second layer nodes to the dst
			for i in range(self.num_pods):
				edges.append((dummy_src, i + 1, {'capacity': leftover_links, 'weight': 0}))
				edges.append((self.num_pods + i + 1, dummy_sink, {'capacity': leftover_links, 'weight': 0}))
			# Next, add edges between first layer nodes and second layer nodes
			for i in range(self.num_pods):
				for j in range(self.num_pods):
					if i != j:						
						edges.append((i + 1, self.num_pods + j + 1, {'capacity': 1, 'weight': 1}))
			# Add the edges set into the graph.
			G.add_edges_from(edges)
			# Trigger the min cost flow algorithm.
			min_cost_flow = nx.max_flow_min_cost(G, dummy_src, dummy_sink)
			for i in range(self.num_pods):
				for j in range(self.num_pods):
					if i != j:
						#if min_cost_flow[i + 1][self.num_pods + j + 1] > 0:
						uniform_interpod_logical_topology[i][j] += 1
		return uniform_interpod_logical_topology
