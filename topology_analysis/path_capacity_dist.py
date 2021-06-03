import numpy as np
import scipy.misc
import matplotlib as mpl
import matplotlib.pyplot as plt

def compute_tor_level_connectivity_based_on_pod_level_connectivity(pod_level_graph, num_tors_per_pod):
	num_pods = len(pod_level_graph)
	# First, figure out the interpod capacity with two hop forwarding
	interpod_path_capacity_graph = np.zeros((num_pods, num_pods), dtype=int)
	for i in range(num_pods):
		for j in range(num_pods):
			if i != j:
				# Figure out how many paths exists between pods i to j within 2 hop counts
				num_paths = 0
				# count direct path
				if pod_level_graph[i][j] > 0:
					num_paths += pod_level_graph[i][j]
				# now count the indirect paths
				for k in range(num_pods):
					if k != i and k != j:
						num_paths += min(pod_level_graph[i][k], pod_level_graph[k][j])
				interpod_path_capacity_graph[i][j] += num_paths 
	return 

# Computes ocs_schedule progression type 1.
def compute_ocs_schedule(num_tors, num_uplinks_per_tor, current_node_offset):
	assert(num_tors > num_uplinks_per_tor - 1 and current_node_offset > 0 and current_node_offset < num_tors)
	# figure out the sequence of connections
	current_schedule = np.zeros((num_tors, num_tors), dtype=int)
	for ocs_id in range(num_uplinks_per_tor):
		for tor_id in range(num_tors):	
			target_tor_id = (tor_id + current_node_offset) % num_tors
			current_schedule[tor_id][target_tor_id] = 1
		current_node_offset = max((current_node_offset + 1) % num_tors, 1)
	return current_schedule

def total_pathways_between_source_and_dest(topology, src, dst):
	assert(src != dst)
	n = len(topology)
	num_paths = 0
	# First check the direct paths
	if topology[src][dst] > 0:
		num_paths = topology[src][dst]
	for k in range(n):
		if k != src and k != dst:
			path_capacity = min(topology[src][k], topology[k][dst])
			if path_capacity > 0:
				num_paths += path_capacity
	return num_paths

def find_permutation_recur(current_index, placements_so_far, num_points, all_placements):
	# base case
	if current_index >= num_points:
		# figure out the remaining placements
		all_placements.append(placements_so_far)
	else:
		for i in range(num_points):
			if i not in placements_so_far:
				placement = list(placements_so_far)
				placement.append(i)
				find_permutation_recur(current_index + 1, placement, num_points, all_placements)
	return

def find_all_permutation_matrices(num_points):
	# finds all the permutation matrices
	all_permutation_placements = []
	find_permutation_recur(0, [], num_points, all_permutation_placements)
	print("Number of permutation matrices for num node: {} is: {}".format(num_points, len(all_permutation_placements)))
	all_permutation_matrices = []
	for permutation_placement in all_permutation_placements:
		permutation_matrix = np.zeros((num_points, num_points), dtype=int)
		for i, j in zip(range(num_points), permutation_placement):
			permutation_matrix[i][j] = 1
		all_permutation_matrices.append(permutation_matrix)
	return all_permutation_matrices


# Given the number of points, and the number of edges per point, this function computes all
# the points along the convex hull of the matrix.
def compute_interpod_connectivity_pdf(num_points, num_edges_per_point):
	all_permutation_matrices = find_all_permutation_matrices(num_points)
	# try to decompose a sum of num_edges_per_point across the number of permutations (num_points!)
	# do this recursively 
	# Go through each of the permutation matrices and find out for each permutation mask, what is the interpod capacity
	pathway_capacity_timeseries = []
	for permutation_matrix in all_permutation_matrices:
		path_capacity = np.zeros((num_points, num_points), dtype=int)
		for i in range(num_points):
			for j in range(num_points):
				if i != j:
					num_pathways = total_pathways_between_source_and_dest(permutation_matrix, i, j)
					path_capacity[i][j] = num_pathways
		pathway_capacity_timeseries.append(path_capacity)

	pair = (0, 3)
	num_zeros = 0
	# Compute the number of masks such that the path way capacity are zero
	max_path_capacity = 0
	for path_capacity_mask in pathway_capacity_timeseries:
		max_path_capacity = max(max_path_capacity, path_capacity_mask[pair[0]][pair[1]])
		if path_capacity_mask[pair[0]][pair[1]] == 0:
			num_zeros += 1
	zero_pathway_prob = (float(num_zeros) / len(all_permutation_matrices))
	print("Max path capacity: {}".format(max_path_capacity))
	print("num zeros: {}".format(num_zeros))
	pdf = []
	for i in range(num_edges_per_point + 1):
		prob = scipy.misc.comb(num_edges_per_point, i) * (1 - zero_pathway_prob) ** i * (zero_pathway_prob) ** (num_edges_per_point - i)
		pdf.append(prob)
	print("length of pdf: {}".format(len(pdf)))
	return np.arange(num_edges_per_point + 1), pdf

def compute_tor_connectivity_pdf(num_tors, num_uplinks_per_tor):
	tor_connectivity_schedules = []
	for tor_schedule_offset in range(1, num_tors, 1):
		schedule = compute_ocs_schedule(num_tors, num_uplinks_per_tor, tor_schedule_offset)
		tor_connectivity_schedules.append(schedule)
	tor_pair = (0, 1)
	tor_pair_connectivity_timeseries = [total_pathways_between_source_and_dest(x, tor_pair[0], tor_pair[1]) for x in tor_connectivity_schedules]
	# Here compute the pdf
	max_entry = max(tor_pair_connectivity_timeseries)
	pdf = [0] * (max_entry + 1)
	for connectivity in tor_pair_connectivity_timeseries:
		pdf[connectivity] += 1./len(tor_connectivity_schedules)
	return np.arange(max_entry + 1), pdf

def shade_curve(x, y, ymin, axis_reference, c_arg=(1,0,0)):
	axis_reference.fill_between(x, y, ymin, alpha=0.09, color=c_arg)
	return

# Plot out the connectivity between endpoints over time
if __name__ == "__main__":
	tor_uplinks = 16
	num_tor_per_pod = 16
	num_pods = 8
	# Build up a ToR network
	# First generate a sequence of traffic patterns at random.
	
	
	x_pod, pdf_pod = compute_interpod_connectivity_pdf(num_pods, num_tor_per_pod)
	x_tor, pdf_tor = compute_tor_connectivity_pdf(num_tor_per_pod * num_pods, tor_uplinks)

	xylabel_fontsize=7.4
	xyticklabel_fontsize = 6.5
	linewidth_arg = 0.7
	latex_linewidth_inch = 4.8
	fig_width = 0.35 * latex_linewidth_inch
	fig_height = 1.3
	mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
	fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
	ax.bar(x_pod, pdf_pod, width=1, color=(0.3, 0.3, 0.3))
	ax.set_xlim(xmin=-0.5, xmax=x_pod[-1]+0.5)
	ax.set_ylim(ymin=0)
	ax.grid(b=None, which='major', axis='y', linestyle=':', linewidth=0.4) # Enable Grids
	ax.tick_params(axis="y", labelsize=xyticklabel_fontsize)
	ax.tick_params(axis="x", labelsize=xyticklabel_fontsize)
	ax.set_xlabel("Total path capacity", fontsize=xylabel_fontsize)
	ax.set_ylabel("Probability", fontsize=xylabel_fontsize)
	plt.subplots_adjust(left=0.28, bottom=0.26, right=0.98, top=0.98, wspace=0.2, hspace=0.2)

	# Plot the ToR
	fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
	ax.bar(x_tor, pdf_tor, width=1, color=(0.3, 0.3, 0.3))
	ax.set_xlim(xmin=-0.5, xmax=x_pod[-1]+0.5)
	ax.set_ylim(ymin=0)
	ax.grid(b=None, which='major', axis='y', linestyle=':', linewidth=0.4) # Enable Grids
	ax.tick_params(axis="y", labelsize=xyticklabel_fontsize)
	ax.tick_params(axis="x", labelsize=xyticklabel_fontsize)
	ax.annotate('{:.3f}'.format(pdf_tor[0]), xy=(0, pdf_tor[0]), xytext=(4, 0.2), arrowprops=dict(arrowstyle="->"), fontsize=xylabel_fontsize)
	ax.set_xlabel("Total path capacity", fontsize=xylabel_fontsize)
	ax.set_ylabel("Probability", fontsize=xylabel_fontsize)
	plt.subplots_adjust(left=0.25, bottom=0.26, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
	plt.show()