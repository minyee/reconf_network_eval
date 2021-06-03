'''
Topological analysis for maximum network size.
'''
import numpy as np
from gurobipy import *
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.image as img
from matplotlib import cm

#mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
xylabel_fontsize=7.4
xyticklabel_fontsize = 6.5
linewidth_arg = 0.9
latex_linewidth_inch = 6.9787
fig_width = 0.45 * latex_linewidth_inch
fig_height = 1.65
legend_fontsize = 6.2
markersize_arg = 4

color_cycle = ['black','red','lime','blue','darkcyan','blueviolet','deeppink']

# Computes the maximum number of nodes we can support given a node degree and a diameter
def compute_moore_bound(node_degree, diameter):
	moore_bound = -1
	if node_degree == 2:
		moore_bound = 2 * diameter + 1
	elif node_degree > 2:
		moore_bound = 1 + node_degree * ((node_degree - 1) ** diameter - 1) / (node_degree - 2)
	return int(moore_bound)


# Given a per ToR node degree, computes the relative subscription factor delta that maximizes pod level diameter.
def maximize_mesh_pod_degree(per_node_degree):
	model = Model("Maximize pod degree given node degree: {}".format(per_node_degree))
	model.setParam( 'OutputFlag', False)
	# Let delta be the fraction of links used for INTER-pod wiring
	delta = model.addVar(lb=0., ub=1, obj=1, vtype=GRB.CONTINUOUS, name="delta")
	objective_function = QuadExpr()
	objective_function.add(delta, mult=per_node_degree ** 2 + per_node_degree)
	objective_function.add(delta * delta, mult=-per_node_degree ** 2)
	model.setObjective(objective_function, GRB.MAXIMIZE) 
	model.optimize()
	delta_val = delta.x
	n1 = int(math.floor(per_node_degree * delta_val))
	n2 = int(math.ceil(per_node_degree * delta_val))
	pod_uplinks_1 = ((per_node_degree - n1) + 1) * n1
	pod_uplinks_2 = ((per_node_degree - n2) + 1) * n2
	if pod_uplinks_1 >= pod_uplinks_2:
		return n1, pod_uplinks_1

	return n2, pod_uplinks_2

def tor_reconfigurable_network_designer(tor_num_uplinks, tor_level_diameter, num_dimensions=1):
	if tor_num_uplinks == 0:
		return 0, 0
	num_dimensions = min(tor_num_uplinks, num_dimensions)
	per_dimension_num_uplinks = tor_num_uplinks / num_dimensions
	leftover = tor_num_uplinks % num_dimensions
	num_uplinks_in_dim = [per_dimension_num_uplinks] * num_dimensions
	for i in range(leftover):
		num_uplinks_in_dim[i] += 1
	# Now, iterate through each dimension
	num_tors = 1
	max_ocs_radix = 0
	total_tors = 1
	for d in num_uplinks_in_dim:
		num_tors_in_dim = compute_moore_bound(d, tor_level_diameter)
		total_tors *= num_tors_in_dim
		max_ocs_radix = max(max_ocs_radix, num_tors_in_dim)
		num_tors *= num_tors_in_dim
	return num_tors * tor_num_uplinks, max_ocs_radix, total_tors * (2 * tor_num_uplinks), total_tors * tor_num_uplinks

# Returns the largest possible system size supported and the OCS radix requirement.
def twotiered_pod_reconfigurable_network_designer(tor_num_uplinks, pod_level_diameter, oversubscription_ratio=(1,1)):
	if tor_num_uplinks == 0:
		return 0, 0
	num_tors_per_pod = tor_num_uplinks
	fraction_of_northbound_links_per_pod = float(oversubscription_ratio[1]) * 2. / (oversubscription_ratio[0] + oversubscription_ratio[1])
	assert(fraction_of_northbound_links_per_pod <= 1 and fraction_of_northbound_links_per_pod > 0)
	num_uplinks_per_pod = int(fraction_of_northbound_links_per_pod * (tor_num_uplinks * num_tors_per_pod))
	# Finally, since each pod has the number of uplinks computed, we want to find the maximum number of pods using moore 
	# bound given per-pod uplinks and inter-pod diameter.
	max_pods = int(compute_moore_bound(num_uplinks_per_pod, pod_level_diameter))
	min_ocs_radix = max_pods
	max_num_servers = tor_num_uplinks * (max_pods * num_tors_per_pod)
	num_electrical_ports = max_pods * (num_tors_per_pod * 2 * (2 * tor_num_uplinks))
	num_optical_ports = max_pods * num_uplinks_per_pod
	return max_num_servers, min_ocs_radix, num_electrical_ports, num_optical_ports

## Given the number of uplinks for each ToR, and the permitted pod_level_diameter, returns
def mesh_pod_reconfigurable_network_designer(tor_num_uplinks, pod_level_diameter):
	if tor_num_uplinks == 0:
		return 0, 0
	# First compute the maximum allocation of tor uplinks such that total servers are maximized.
	per_tor_inter_pod_links, pod_num_uplink = maximize_mesh_pod_degree(tor_num_uplinks)
	per_tor_intra_pod_links = tor_num_uplinks - per_tor_inter_pod_links
	assert(per_tor_intra_pod_links > 0)
	num_pods = int(compute_moore_bound(pod_num_uplink, pod_level_diameter))
	max_num_servers = num_pods * (per_tor_intra_pod_links + 1) * tor_num_uplinks
	num_electrical_ports = (per_tor_intra_pod_links + tor_num_uplinks) * num_pods 
	num_ocs_ports = num_pods * (per_tor_intra_pod_links + 1) * per_tor_inter_pod_links 
	return max_num_servers, num_pods, num_electrical_ports, num_ocs_ports

def dragonfly_network_designer(switch_num_uplinks, pod_level_diameter):
	group_size = switch_num_uplinks
	num_groups = group_size + 1
	max_num_servers = num_groups * group_size * switch_num_uplinks
	num_electrical_ports = num_groups * group_size * (2 * switch_num_uplinks)
	return max_num_servers, num_groups, num_electrical_ports, 0

# Returns the maximum system size and requirement on OCS radix
def fully_subscribed_clos_designer(tor_num_uplinks, levels):
	if tor_num_uplinks == 0:
		return 0, 0
	max_num_servers = 2 * (tor_num_uplinks ** levels)
	total_switches = (2 * levels - 1) * tor_num_uplinks ** (levels - 1)
	return max_num_servers, 0, total_switches * tor_num_uplinks * 2, 0

def ocs_scalability_analysis():
	ocs_radices = np.arange(4, 320, 4)
	eps_radix = 32
	servers_per_tor = eps_radix // 2
	num_uplinks_per_tor = eps_radix - servers_per_tor
	# ToR 1D 2 hop
	maximum_tors = compute_moore_bound(num_uplinks_per_tor, 2)
	tors_1D_num_servers = []
	for ocs_radix in ocs_radices:
		if ocs_radix >= maximum_tors:
			tors_1D_num_servers.append(maximum_tors * servers_per_tor)
		else:
			tors_1D_num_servers.append(ocs_radix * servers_per_tor)
	# ToR 2D 2 hop
	tors_2D_num_servers = []
	maximum_tors_per_dim = compute_moore_bound(num_uplinks_per_tor // 2, 1)
	print("maximum nD : {} maximum flat: {}".format(maximum_tors_per_dim ** 2, maximum_tors))
	for ocs_radix in ocs_radices: 
		if ocs_radix >= maximum_tors_per_dim:
			total_tors = maximum_tors_per_dim ** 2
			tors_2D_num_servers.append(total_tors * servers_per_tor)
		else:
			tors_per_dim = ocs_radix
			total_tors = tors_per_dim ** 2
			tors_2D_num_servers.append(total_tors * servers_per_tor)
	# Mesh pod
	pod_mesh_num_servers = []
	for ocs_radix in ocs_radices:
		number_of_groups = ocs_radix
		# For each total number of pods, we need to make sure that a * h >= number_of_groups - 1, such that a - 1 + h = r/2
		max_num_servers = 0
		for h in range(1, num_uplinks_per_tor, 1):
			a = num_uplinks_per_tor + 1 - h
			if a * h >= number_of_groups - 1:
				max_num_servers = max(max_num_servers, number_of_groups * a * servers_per_tor)
		prev_entry_size = 0
		if len(pod_mesh_num_servers) > 0:
			prev_entry_size = pod_mesh_num_servers[-1]
		new_entry = max(max_num_servers, prev_entry_size)
		if new_entry == 0:
			new_entry = 0.1
		pod_mesh_num_servers.append(new_entry)
	# 2-layered pod, no oversub
	pod_2tiered_num_servers = []
	for ocs_radix in ocs_radices:
		num_tors_per_pod = (eps_radix / 2)
		num_uplinks_per_pod = (eps_radix / 2) * num_tors_per_pod
		num_pods = min(ocs_radix, num_uplinks_per_pod + 1)
		total_servers = num_tors_per_pod * servers_per_tor * num_pods
		pod_2tiered_num_servers.append(total_servers)
	# 2-layered pod, 4:1 oversub
	pod_2tiered_4to1_num_servers = []
	for ocs_radix in ocs_radices:
		num_tors_per_pod = (eps_radix / 2)
		num_uplinks_per_pod = (eps_radix / 2) * num_tors_per_pod / 4
		num_pods = min(ocs_radix, num_uplinks_per_pod + 1)
		total_servers = num_tors_per_pod * servers_per_tor * num_pods
		pod_2tiered_4to1_num_servers.append(total_servers)
	mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
	fig, ax = plt.subplots(1,1, figsize=(fig_width, fig_height), dpi=200)
	ax.plot(ocs_radices, tors_1D_num_servers, linestyle='-', linewidth=linewidth_arg, color='darkcyan', marker='+', markerfacecolor='none', markersize=markersize_arg, markevery=12)
	ax.plot(ocs_radices, tors_2D_num_servers, linestyle='-', linewidth=linewidth_arg, color='darkblue', marker='^', markerfacecolor='none', markersize=markersize_arg, markevery=12)
	ax.plot(ocs_radices, pod_mesh_num_servers, color='lime',  marker='s', markevery=12, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax.plot(ocs_radices, pod_2tiered_num_servers, color='red', marker='x', markevery=12, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax.plot(ocs_radices, pod_2tiered_4to1_num_servers, color='darkred', marker='d', markevery=12, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax.legend(['TRN-Flat', 'TRN-2D', 'PRN-Mesh', 'PRN-2L (1:1)', 'PRN-2L (4:1)'], fontsize=legend_fontsize, ncol=3, loc='lower right',bbox_to_anchor=(1.01,0.0), labelspacing=0.3, columnspacing=0.5)
	ax.set_xlim(xmin=min(ocs_radices), xmax=max(ocs_radices))
	ax.set_yscale('log', basey=10, nonposy='clip')
	#ax.set_xscale('log', basex=2, nonposx='clip')
	ax.set_ylim(ymin=1)
	ax.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
	ax.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
	ax.tick_params(axis="y", labelsize=xyticklabel_fontsize)
	ax.tick_params(axis="x", labelsize=xyticklabel_fontsize)
	ax.set_ylabel(r"Network size", fontsize=xylabel_fontsize, labelpad=0.7)
	ax.set_xlabel(r"OCS radix", fontsize=xylabel_fontsize, labelpad=0.7)
	plt.subplots_adjust(left=0.14, bottom=0.19, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
	
def scalability_analysis():
	num_uplinks = np.arange(4, 65, 2)
	# Mesh pod-reconfigurable
	mesh_pod = [mesh_pod_reconfigurable_network_designer(x, 1) for x in num_uplinks]
	# 2-tiered clos pod-reconfigurable
	tiered_1to1_pod = [twotiered_pod_reconfigurable_network_designer(x, 1, oversubscription_ratio=(1,1)) for x in num_uplinks]
	tiered_4to1_pod = [twotiered_pod_reconfigurable_network_designer(x, 1, oversubscription_ratio=(4,1)) for x in num_uplinks]
	# ToR-reconfigurables
	tor_dimension1_diameter1 = [tor_reconfigurable_network_designer(x, 1, num_dimensions=1) for x in num_uplinks]
	tor_dimension1_diameter2 = [tor_reconfigurable_network_designer(x, 2, num_dimensions=1) for x in num_uplinks]
	tor_dimension1_diameter3 = [tor_reconfigurable_network_designer(x, 3, num_dimensions=1) for x in num_uplinks]
	tor_dimension2_diameter1 = [tor_reconfigurable_network_designer(x, 1, num_dimensions=2) for x in num_uplinks]
	tor_dimension3_diameter1 = [tor_reconfigurable_network_designer(x, 1, num_dimensions=3) for x in num_uplinks]
	# Clos
	clos_layer3 = [fully_subscribed_clos_designer(x, 3) for x in num_uplinks]
	clos_layer4 = [fully_subscribed_clos_designer(x, 4) for x in num_uplinks]

	# Dragonfly (Canonical)
	dfly_canonical = [dragonfly_network_designer(x, 1) for x in num_uplinks]

	# Plotting
	mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
	fig, ax1 = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=200)
	eps_radices = [2 * x for x in num_uplinks]
	ax1.plot(eps_radices, [x[0] for x in tor_dimension1_diameter2], linestyle='--', linewidth=linewidth_arg, color='darkcyan', marker='+', markerfacecolor='none', markersize=markersize_arg, markevery=4)
	ax1.plot(eps_radices, [x[0] for x in tor_dimension2_diameter1], linestyle='-.', linewidth=linewidth_arg, color='darkblue', marker='^', markerfacecolor='none', markersize=markersize_arg, markevery=4)
	ax1.plot(eps_radices, [x[0] for x in mesh_pod], color='lime',  marker='s', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax1.plot(eps_radices, [x[0] for x in tiered_1to1_pod], color='red', marker='x', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax1.plot(eps_radices, [x[0] for x in tiered_4to1_pod], color='darkred', marker='d', markevery=4, linewidth=linewidth_arg, markerfacecolor='none', markersize=markersize_arg)
	ax1.plot(eps_radices, [x[0] for x in dfly_canonical], linestyle=(0, (1, 1)), linewidth=linewidth_arg, color='orange', marker='h', markerfacecolor='none', markersize=markersize_arg, markevery=6)
	ax1.plot(eps_radices, [x[0] for x in clos_layer3], linewidth=linewidth_arg, color='black', linestyle='--')
	ax1.plot(eps_radices, [x[0] for x in clos_layer4], linewidth=linewidth_arg, color='black')
	
	#ax1.plot(eps_radices, [x[0] for x in tor_dimension1_diameter3], linestyle='--', linewidth=linewidth_arg, color='gray')
	#ax1.plot([x[0] for x in clos_layer4], num_uplinks, linewidth=linewidth_arg)
	ax1.set_ylabel(r"Network size", fontsize=xylabel_fontsize, labelpad=0.7)
	ax1.set_xlabel(r"Packet switch degree ($k$)", fontsize=xylabel_fontsize, labelpad=0.7)
	ax1.set_xlim(xmin=min(eps_radices), xmax=max(eps_radices))
	#ax1.set_xscale('log',basex=2,nonposx='clip')
	ax1.set_yscale('log',basey=10, nonposy='clip')
	#ax1.set_xlim(xmax=1e7, xmin=1e3)
	ax1.legend(['TRN-Flat', 'TRN-2D', 'PRN-Mesh', 'PRN-2L (1:1)', 'PRN-2L (4:1)', 'DF', 'FT3', 'FT4'], fontsize=legend_fontsize, ncol=3, loc='lower right', bbox_to_anchor=(1.01,-0.01), labelspacing=0.3, columnspacing=0.5)
	ax1.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
	ax1.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
	ax1.tick_params(axis="y", labelsize=xyticklabel_fontsize)
	ax1.tick_params(axis="x", labelsize=xyticklabel_fontsize)
	plt.subplots_adjust(left=0.14, bottom=0.21, right=0.98, top=0.98, wspace=0.2, hspace=0.2)

if __name__ == "__main__":
	scalability_analysis()
	ocs_scalability_analysis()
	plt.show()




