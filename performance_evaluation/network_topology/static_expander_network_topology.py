import numpy as np
import networkx as nx
from network_topology import *
from numpy import linalg as LA
import math

# In this model, the network is a static expander that directly connects ToRs.
class StaticExpanderNetworkTopology:
	def __init__(self, eps_radix, target_num_tors, num_servers_per_tor=-1):
		self.eps_radix = eps_radix
		self.adjacency_list = {}
		self.num_pods = target_num_tors
		self.num_servers_per_tor = num_servers_per_tor
		assert((self.eps_radix / 2) < self.num_pods - 1)
	
	def get_lambda2(self, mat):
		eig,vecs = LA.eig(mat)	
		eig = np.abs(eig)
		eig.sort()
		return eig[-2]

	def get_spectral_gap(self, d):
		return 2 * np.sqrt(d-1)

	def is_ramanujan(self, mat, d):
		return self.get_lambda2(mat) < self.get_spectral_gap(d)

	# d= the degree of the graph
	# k= number of lifts to perform
	# e.g.,: random_k_lift(4,6) will create a 4 regualr graph with 30 nodes
	def random_k_lift(self, d, k):
		num_nodes = (d+1) * k
		mat = np.zeros( (num_nodes, num_nodes), dtype=int)
		# go over all meta nodes
		for meta1 in range(d + 1):
			# connect to any other meta node
			for meta2 in range(meta1 + 1, d + 1):

				# connect the ToRs between the meta-nodes randomally
				perm = np.random.permutation(k)
				for src_ind in range(k):
					src = meta1 * k + src_ind
					dst = meta2 * k + perm[src_ind]

					# connect the link
					mat[src,dst] = 1
					mat[dst,src] = 1

		if not self.is_ramanujan(mat,d):
			# try again if we got a bad Xpander
			return self.random_k_lift(d, k)
		return mat

	# Wires up the network in its entirety, and sets up the various topological properties.
	def wire_network(self):
		# Step 0: Run the k-lifting algorithm to generate the ToR level connectivity

		tor_level_topology_adj_matrix = self.random_k_lift(self.eps_radix / 2, int(math.ceil(float(self.num_pods) / ((self.eps_radix / 2) + 1))))
		self.num_pods = len(tor_level_topology_adj_matrix)
		# Check for k-lifting symmetry
		for i in range(len(tor_level_topology_adj_matrix)):
			for j in range(i+1, len(tor_level_topology_adj_matrix), 1):
				assert(tor_level_topology_adj_matrix[i][j] == tor_level_topology_adj_matrix[j][i])
		# Step 1: Intialize the servers and the switches first if all pods, while also wiring things together
		for tor_id in range(self.num_pods):
			# Step 1.1 : Initialize the ToR switch, which serves as the aggregation switch in the sparse model. Still just 1 aggregation/ToR per pod.
			self.adjacency_list[tor_id] = {}

			# Step 1.2 : Initialize the servers
			server_id = self.num_pods + tor_id
			self.adjacency_list[server_id] = {}

			# Step 1.3 : Connect the servers to the ToRs
			self.adjacency_list[server_id][tor_id] = self.eps_radix / 2
			self.adjacency_list[tor_id][server_id] = self.eps_radix / 2

		# Step 2: Wire up the initial inter-pod logical topology between aggregation switches, with rotation matching like Rotornet
		# Step 2.1: Derive the logical interpod adjacency matrix, for setup just form a uniform mesh
		for i in range(self.num_pods):
			for j in range(self.num_pods):
				if i != j and tor_level_topology_adj_matrix[i][j] > 0:
					self.adjacency_list[i][j] = tor_level_topology_adj_matrix[i][j]
		return

	# Generates the traffic events in the form of strings.
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

	# Generates the initial WCMP configuration for a uniform pod-to-pod logical topology.
	def generate_initial_interpod_routing_weights_string(self):
		return ""

	# Generates the strings used to write to the filename, which states 
	# the pod id each of the switch/server belongs to.
	def generate_pod_id_file_string(self):
		return ""

	def get_num_reconfigurable_uplinks_per_pod(self):
		return 0

