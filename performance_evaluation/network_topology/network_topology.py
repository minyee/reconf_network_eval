import sys

class NetworkTopology(object):

	# The model assumes that all Electrical Packet Switches (EPS) are built with
	# identical radix devices.
	def __init__(self, eps_radix):
		# The topology only needs: eps_radix, num_pods, device id to pod id map, and adjacency list
		self.eps_radix = eps_radix
		self.device_id_to_pod_id_map = {}
		self.adjacency_list = {}
		return

	# Retrieves the device id map to pod id
	def get_device_id_to_pod_id_mapping(self):
		return self.device_id_to_pod_id

	# An abstract function called by external user to wire the network together.
	# This is the responsibility of each sparse and dense reconfigurable models to implement themselves.
	def wire_network(self):
		raise Exception("Wiring method is not implemented.")
		return

	## Basic query functions for basic information of this topology.
	# Retrieves the EPS radix.
	def get_eps_radix(self):
		return self.eps_radix

	# Retrieves the number of servers that this topology instance supports.
	def get_num_servers(self):
		# Each ToR carries eps_radix / 2 servers, 
		return 

	# Retrives the number of electrical packet switches in the network.
	def get_num_eps(self):
		return

	## Returns the network logical topology
	def get_adjacency_list(self):
		return self.adjacency_list

	# Generates the strings used to write to the filename, which states 
	# the pod id each of the switch/server belongs to.
	def generate_pod_id_file_string(self):
		str_builder = ""
		for device_id in sorted(self.device_id_to_pod_id_map.keys()):
			pod_id = self.device_id_to_pod_id_map[device_id]
			str_builder += "{},{}\n".format(device_id, pod_id)
		return str_builder

	def get_name(self):
		raise Exception("Child classes must override this method.")
		return ""

	def get_num_reconfigurable_uplinks_per_pod(self):
		return 0