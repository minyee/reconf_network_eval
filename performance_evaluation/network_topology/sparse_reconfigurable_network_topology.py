import numpy as np
import networkx as nx
from network_topology import *

# In this model, the reconfigurable network is ToR-reconfigurable. Each pod is built with just a single
# ToR switch with radix of eps_radix 
# The actual number of aggregation switches is actually identical to the number of ToRs inside a 
# pod, but we logically collapse all aggregation switches to 1. In other words, each pod must only have 
# one aggregation switch.
class SparseReconfigurableNetworkTopology(NetworkTopology):
	def __init__(self, eps_radix, num_tors, num_servers_per_tor=-1):
		NetworkTopology.__init__(self, eps_radix)
		self.num_pods = num_tors
		self.num_servers_per_tor = num_servers_per_tor
		assert((self.eps_radix / 2) < num_tors - 1)
	
	# Wires up the network in its entirety, and sets up the various topological properties.
	def wire_network(self):
		# Step 1: Intialize the servers and the switches first if all pods, while also wiring things together
		for pod_id in range(self.num_pods):
			# Step 1.1 : Initialize the ToR switch, which serves as the aggregation switch in the sparse model. Still just 1 aggregation/ToR per pod.
			tor_id = pod_id
			self.device_id_to_pod_id_map[tor_id] = pod_id
			self.adjacency_list[tor_id] = {}

			# Step 1.2 : Initialize the servers
			server_id = self.num_pods + pod_id
			self.device_id_to_pod_id_map[server_id] = pod_id
			self.adjacency_list[server_id] = {}

			# Step 1.3 : Connect the servers to the ToRs
			self.adjacency_list[server_id][tor_id] = self.eps_radix / 2
			self.adjacency_list[tor_id][server_id] = self.eps_radix / 2

		# Step 2: Wire up the initial inter-pod logical topology between aggregation switches, with rotation matching like Rotornet
		# Step 2.1: Derive the logical interpod adjacency matrix, for setup just form a uniform mesh
		offset_switch = 1
		per_tor_uplink = self.eps_radix / 2
		for i in range(self.num_pods):
			for j in range(self.num_pods):
				if i != j:
					self.adjacency_list[i][j] = 1
		#for _ in range(per_tor_uplink):
		#	for tor in range(self.num_pods):
		#		target_tor = (offset_switch + tor) % self.num_pods
		#		assert(tor != target_tor and target_tor not in self.adjacency_list[tor])
		#		self.adjacency_list[tor][target_tor] = 1
		#	offset_switch = max((offset_switch + 1) % self.num_pods, 1)
		return

	# Generates the traffic probability in the form of strings.
	def generate_traffic_events_string(self, traffic_probability):
		str_builder = ""
		virtual_servers_offset = self.num_pods # Server indices are in the range [num_pods, 2 * num_pods - 1]
		num_physical_servers_per_tor = -1
		if self.num_servers_per_tor < 0:
			num_physical_servers_per_tor = self.eps_radix / 2
		else:
			num_physical_servers_per_tor = self.num_servers_per_tor / 2
		index = 0
		prob_sum = 0
		for src, dst in traffic_probability:
			src_virtual = virtual_servers_offset + src / num_physical_servers_per_tor
			dst_virtual = virtual_servers_offset + dst / num_physical_servers_per_tor
			if src_virtual != dst_virtual:
				prob_sum += traffic_probability[(src, dst)]
		for src, dst in traffic_probability:
			src_virtual = virtual_servers_offset + src / num_physical_servers_per_tor
			dst_virtual = virtual_servers_offset + dst / num_physical_servers_per_tor
			if src_virtual != dst_virtual:
				str_builder += "{},{},{},{:.4e}\n".format(index, src_virtual, dst_virtual, traffic_probability[(src, dst)] / prob_sum)
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

	# Generates the topology string used for netbench
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
		prefix += "ToRs=incl_range({},{})\n".format(0, self.num_pods - 1)
		prefix += "Servers=incl_range({},{})\n".format(self.num_pods, 2 * self.num_pods - 1)
		prefix += "Switches=set()\n\n"
		return prefix + topol_str

	# Retrieves the name of this topology, summarizing some of the essential parameters. Used to create topology directory and filename.
	def get_name(self):
		network_name_prefix = "tor_eps{}_".format(self.eps_radix)
		num_tors_str = "np{}".format(self.num_pods)
		return network_name_prefix + num_tors_str
	
	def get_num_reconfigurable_uplinks_per_pod(self):
		return self.eps_radix / 2
