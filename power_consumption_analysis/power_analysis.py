import math
import numpy as np
import matplotlib as mpl
#mpl.use("pgf")
import matplotlib.pyplot as plt
import matplotlib.image as img
import matplotlib.ticker as mtick

# total power consumption for a given network size = total number of EPS * power per EPS + total number of OCS ( power per OCS), 
# number of OCS = total optical ports/ ceil(total ports per OCS)

#Decide whether if the transceiver of optical and electrical links will be required.

#
EPS_POWER_W = 480 # Based on broadcom's Facebook 32 port radix ToR switch
EPS_RADIX = 32

# Mellanox Infiniband SB7800 36-port Top of rack leaf switch: 146W
# Calient S320 320 x 320 OCS, 45W power consumption normally

# Maps an eps radix to the power consumption
EPS_POWER_MODELS = {32 : 480, 36 : 150}

# Maps an OCS radix to the power consumption
# Polatis 384 x 384 7000 Series OCS, 100W power consumption
# Calient S320 320 x 320 OCS, 45W power consumption normally
OCS_POWER_MODELS = {320 : 45, 384 : 100}

# Based on datasheets, collects the power (W) of switch as a function of radix.
EPS_POWER_CONSUMPTIONS = {
	"Mellanox QM8700 Series" : (80, 274),
	"Mellanox SB7800" : (36, 136), #d
	"tomahawk" : (128, 483), #d
	"mellanox ethernet" : (16, 94.7), #d
	"Mellanox Spectrum SN2700 32-Port 100GbE" : (32, 169),
	"mellanox SN4600C" : (64, 482), #d
}

# per optical transceiver power
TRANSCEIVER_POWER_W = 4.5

gradient = 2.39
y_intercept = 188

xylabel_fontsize=7.4
xyticklabel_fontsize = 6.5
linewidth_arg = 0.85
latex_linewidth_inch = 6.9787
fig_width = 0.33 * latex_linewidth_inch
fig_height = 1.8
legend_fontsize = 6.2
markersize_arg = 4
color_cycle = ['darkcyan', 'lime', 'orange', 'darkred', 'gray','blueviolet','deeppink']

# Performs a linear fitting of eps radix to power
def linear_regression_model_for_eps_power():
	x, y = [], []
	for switch_name in EPS_POWER_CONSUMPTIONS:
		eps_radix, power_consumption_watts = EPS_POWER_CONSUMPTIONS[switch_name]
		x.append(eps_radix)
		y.append(power_consumption_watts)
	fit_function = np.polyfit(x, y, 1)
	global gradient, y_intercept
	gradient = fit_function[0]
	y_intercept = fit_function[1]
	## Start plotting the linear regression
	mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
	fig, ax = plt.subplots(1,1, figsize=(0.17 * latex_linewidth_inch, fig_height), dpi=200)
	ax.scatter(x, y, color=(0.,0.,0.), marker='.', s=12)
	fitted_line_x = np.arange(14, 131, 2)
	fitted_line_y = [gradient * x + y_intercept for x in fitted_line_x]
	ax.plot(fitted_line_x, fitted_line_y, linestyle='-', color=(0,0,0), linewidth=linewidth_arg)
	ax.set_xlim(xmin=14, xmax=130)
	ax.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
	ax.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
	text = r'$y={:.2f}x + {:.1f}$'.format(gradient, y_intercept)
	ax.annotate(text, xy=(106, 300), xytext=(0.54, 0.58), textcoords='figure fraction', fontsize=xyticklabel_fontsize, rotation=60, ha='center', va= 'center')
	xtick_locations = [32, 64, 96, 128]
	ax.set_xticks(xtick_locations)
	ax.set_xticklabels([r"{}".format(x) for x in xtick_locations], fontsize=xyticklabel_fontsize, rotation=35)
	ax.tick_params(axis="y", labelsize=xyticklabel_fontsize)
	ax.tick_params(axis="x", labelsize=xyticklabel_fontsize)
	ax.set_ylabel(r"Power (W)", fontsize=xylabel_fontsize, labelpad=0.7)
	ax.set_xlabel(r"EPS Radix", fontsize=xylabel_fontsize, labelpad=0.7)
	plt.subplots_adjust(left=0.33, bottom=0.2, right=0.96, top=0.98, wspace=0.2, hspace=0.2)
	plt.savefig("eps_power_model.pgf")
	return 


# Given an eps radix, returns the power consumption in Watts of a 
# k-radix packet switch.
def power_model(k):
	return gradient * k + y_intercept

def fattree_total_switch_power_computer(eps_radix, levels):
	# Computes the number of switches
	total_switches = (2 * levels - 1) * ((eps_radix / 2) ** (levels - 1))
	per_switch_power = power_model(eps_radix)
	return total_switches * per_switch_power

# Given a target number of servers to support, compute the minimum eps radix for a given diameter
def find_needed_eps_radix_from_moore_bound_with_target_size(number_of_servers, diameter):
	k = 16
	found = False
	ub, lb = int(number_of_servers * 1.05), int(number_of_servers * 0.95)
	while not found:
		num_switches = int(math.ceil(float(number_of_servers) / (k / 2)))
		network_radix = k / 2
		moore_bound = 1 + network_radix * ((network_radix - 1) ** diameter - 1) / (network_radix - 2)
		current_total_num_servers = moore_bound * k / 2
		if current_total_num_servers >= lb:
			found = True
		else:
			k += 2
	return k

## Given a target size in number of servers, computes all the possible eps radices of the leaf edge ToR switch such that 
## the following two conditions hold:
## 1) the total number of servers carried by a 2-tier pod-reconfigurable network is in the range of 0.95 * number_of_servers, and 1.05 * number_of_servers
## 2) the number of uplinks from each pod is >= per_pod_pair_link_multiplicity * number_of_pods
def find_needed_eps_radix_for_pod_reconfigurable_with_target_size(number_of_servers, fattree_eps_radix, per_pod_pair_link_multiplicity=1, oversub=(1,1)):
	assert(per_pod_pair_link_multiplicity >= 1)
	possible_designs = []
	for current_eps_radix in range(fattree_eps_radix, 10 * fattree_eps_radix, 2):
		ntors_per_pod = current_eps_radix / 2
		num_servers_per_pod = ntors_per_pod * current_eps_radix / 2
		num_uplinks_per_pod = int(ntors_per_pod * (current_eps_radix / 2) / float(oversub[0]))
		num_pods = number_of_servers // num_servers_per_pod
		if num_pods * num_servers_per_pod < int(0.95 * number_of_servers):
			num_pods += 1
		# dense
		if num_uplinks_per_pod > num_pods * per_pod_pair_link_multiplicity:
			possible_designs.append((current_eps_radix, num_pods))
	return possible_designs


# Given an eps_radix, computes an optimal radix for aggregation layer such that the power in the aggregation layer is minimized.
def minimize_aggregation_layer_power_for_pod_reconfigurable(eps_radix, number_of_pods, oversub=(1,1)):
	assert(eps_radix <= 48)
	aggr_switch_radix = eps_radix
	num_tors_per_pod = eps_radix / 2
	total_uplinks_per_pod = int(((eps_radix / 2) ** 2) / oversub[0])
	# Check that the number of uplinks must be at least as great as number of pods
	min_power = 1E20
	min_power_eps_radix = eps_radix
	min_power_num_aggr_switches = num_tors_per_pod
	for curr_aggr_radix in [eps_radix, 24, 32, 36, 48, 60, 64, 90, 94, 96, 100, 128]:
		num_aggr_switches = int(math.ceil(((eps_radix / 2) ** 2 + total_uplinks_per_pod) / float(curr_aggr_radix)))
		current_config_power = num_aggr_switches * power_model(curr_aggr_radix)
		if min_power > current_config_power:
			min_power = current_config_power
			min_power_eps_radix = curr_aggr_radix
			min_power_num_aggr_switches = num_aggr_switches
	return min_power_eps_radix, min_power_num_aggr_switches

# Finds the possible EPS radices that can support a total number of intended servers, assuming k/2 of the links
# are devoted to server side connection.
## Finds the configuration that minimized power
def mesh_pod_designer(fattree_radix, target_total_servers, per_pod_pair_link_multiplicity=2, eps_power_scaling=1, transceiver_scaling=1):
	lowest_power_so_far = 1E14
	lowest_power_eps_radix = fattree_radix
	possible_designs = []
	for current_eps_radix in range(fattree_radix, 129, 2):
		num_servers_per_tor = (current_eps_radix / 2)
		num_tors_per_pod = int(math.ceil(current_eps_radix / 4.)) + 1
		num_interpod_links_per_tor = current_eps_radix - num_servers_per_tor - (num_tors_per_pod - 1)
		# Next compute the number of uplinks coming out of each pod
		num_uplinks_per_pod = num_interpod_links_per_tor * num_tors_per_pod
		# Now, figure out how many pods are needed.
		num_pods = target_total_servers // (num_tors_per_pod * num_servers_per_tor)
		if num_pods * (num_tors_per_pod * num_servers_per_tor) < int(0.95 * target_total_servers):
			num_pods += 1
		# Check whether the inter-pod graph is dense, if not, skip this design point
		if per_pod_pair_link_multiplicity * (num_pods - 1) >= num_uplinks_per_pod:
			continue
		# append to the possible_design
		# Compute the total packet switch power and transceivers
		total_ocs_required = int(math.ceil(num_pods * num_uplinks_per_pod / 320.))
		total_eps_switches = num_pods * num_tors_per_pod
		total_power_consumed = eps_power_scaling * total_eps_switches * power_model(current_eps_radix) + total_ocs_required * OCS_POWER_MODELS[320] + transceiver_scaling * total_eps_switches * current_eps_radix * TRANSCEIVER_POWER_W
		possible_designs.append((current_eps_radix, total_power_consumed))
	return possible_designs[0]







# Compare all topologies against a 3-layer fat tree at full size with switch radices being fattree_radix
def small_medium_sized_analysis(fattree_radix):
	assert(fattree_radix >= 16)
	# First, compute the maximum number of servers that a 3 level fat tree with fattree radix can support
	target_total_servers = 2 * (fattree_radix/2) ** 3
	# 3-layer fat tree total power
	fattree_total_transceivers = fattree_radix * (5 * ((fattree_radix / 2) ** 2))
	fattree_total_power = fattree_total_switch_power_computer(fattree_radix, 3) + fattree_total_transceivers * TRANSCEIVER_POWER_W

	# 4:1 2-layer pod reconfigurable
	oversub = (4, 1)
	npods = fattree_radix
	ntors_per_pod = fattree_radix / 2
	total_uplinks_per_pod = int(((fattree_radix / 2) ** 2) / oversub[0])
	total_num_optical_switches = int(math.ceil(npods * total_uplinks_per_pod / 320.))
	aggr_switch_radix, num_aggr_switch_per_pod = minimize_aggregation_layer_power_for_pod_reconfigurable(fattree_radix, npods, oversub=oversub)
	tiered_pod_total_transceiver_power = 0.95 * npods * (num_aggr_switch_per_pod * aggr_switch_radix + ntors_per_pod * fattree_radix) * TRANSCEIVER_POWER_W
	tiered_pod_4to1_total_power = total_num_optical_switches * OCS_POWER_MODELS[320] + npods * (ntors_per_pod * power_model(fattree_radix) + num_aggr_switch_per_pod * power_model(aggr_switch_radix)) + tiered_pod_total_transceiver_power

	# mesh reconfigurable
	mesh_reconfigurable_picked_design = mesh_pod_designer(fattree_radix, target_total_servers, per_pod_pair_link_multiplicity=2, eps_power_scaling=1.1, transceiver_scaling=1.1)

	# flat expanders and reconfigurable expanders
	flat_expander_required_eps_radix = find_needed_eps_radix_from_moore_bound_with_target_size(target_total_servers, 2)
	flat_expander_num_tors = int(math.ceil(float(target_total_servers) / (flat_expander_required_eps_radix / 2)))
	flat_expander_total_transceiver_power = 1.1 * flat_expander_num_tors * flat_expander_required_eps_radix * TRANSCEIVER_POWER_W
	flat_expander_required_num_ocs = int(math.ceil(flat_expander_num_tors * flat_expander_required_eps_radix / 2. / 320.))
	flat_reconfigurable_network_total_power = flat_expander_num_tors * power_model(flat_expander_required_eps_radix) + flat_expander_required_num_ocs * OCS_POWER_MODELS[320] + flat_expander_total_transceiver_power
	flat_expander_network_total_power = flat_reconfigurable_network_total_power - flat_expander_required_num_ocs * OCS_POWER_MODELS[320]
	print("3 layer fat tree total power: {}W".format(fattree_total_power))
	print("4:1 oversub 2-layer pod reconfigurable total power: {}W".format(tiered_pod_4to1_total_power))
	print("Flat reconfigurable network total power: {}W".format(flat_reconfigurable_network_total_power))
	print("Flat static expander network total power: {}W".format(flat_expander_network_total_power))
	return dict(ft=fattree_total_power, pod_tiered=tiered_pod_4to1_total_power, pod_mesh=mesh_reconfigurable_picked_design[1], tor_reconfigurable=flat_reconfigurable_network_total_power, expander=flat_expander_network_total_power)

def large_sized_analysis(fattree_radix):
	assert(fattree_radix >= 16)
	# First, compute the maximum number of servers that a 3 level fat tree with fattree radix can support
	target_total_servers = 2 * (fattree_radix/2) ** 4
	# 4-layer fat tree total power
	fattree_total_transceivers = 1.1 * fattree_radix * (7 * ((fattree_radix / 2) ** 3))
	fattree_total_power = 1.2 * fattree_total_switch_power_computer(fattree_radix, 4) + fattree_total_transceivers

	# 1:1 2-layer pod reconfigurable
	oversub = (1, 1)
	possible_designs = find_needed_eps_radix_for_pod_reconfigurable_with_target_size(target_total_servers, fattree_radix, per_pod_pair_link_multiplicity=1.5, oversub=oversub)
	chosen_design = possible_designs[1]
	tiered_pod_eps_radix, npods = chosen_design
	ntors_per_pod = tiered_pod_eps_radix / 2
	aggr_switch_radix, num_aggr_switch_per_pod = minimize_aggregation_layer_power_for_pod_reconfigurable(tiered_pod_eps_radix, npods, oversub=oversub)
	tiered_pod_total_transceiver_power = 0.75 * npods * (num_aggr_switch_per_pod * aggr_switch_radix + ntors_per_pod * fattree_radix) * TRANSCEIVER_POWER_W
	# Compute number of OCS needed
	total_uplinks_per_pod = int(((tiered_pod_eps_radix / 2) ** 2) / oversub[0])
	total_num_optical_switches = int(math.ceil(npods * total_uplinks_per_pod / 320.))
	tiered_pod_1to1_total_power = total_num_optical_switches * OCS_POWER_MODELS[320] + npods * (ntors_per_pod * power_model(tiered_pod_eps_radix) + num_aggr_switch_per_pod * power_model(aggr_switch_radix))  + tiered_pod_total_transceiver_power
	
	# mesh reconfigurable
	mesh_reconfigurable_picked_design = mesh_pod_designer(fattree_radix, target_total_servers, per_pod_pair_link_multiplicity=2, eps_power_scaling=1.6, transceiver_scaling=1.5)

	# flat expanders and reconfigurable expanders
	flat_expander_required_eps_radix = find_needed_eps_radix_from_moore_bound_with_target_size(target_total_servers, 2)
	flat_expander_num_tors = int(math.ceil(float(target_total_servers) / (flat_expander_required_eps_radix / 2)))
	flat_expander_total_transceiver_power = 1.25 * flat_expander_num_tors * flat_expander_required_eps_radix * TRANSCEIVER_POWER_W
	flat_expander_required_num_ocs = int(math.ceil(flat_expander_num_tors * flat_expander_required_eps_radix / 2. / 320.))
	flat_reconfigurable_network_total_power = 1.5 * flat_expander_num_tors * power_model(flat_expander_required_eps_radix) + flat_expander_required_num_ocs * OCS_POWER_MODELS[320] + flat_expander_total_transceiver_power
	flat_expander_network_total_power = flat_reconfigurable_network_total_power - flat_expander_required_num_ocs * OCS_POWER_MODELS[320]
	return dict(ft=fattree_total_power, pod_tiered=tiered_pod_1to1_total_power, pod_mesh=mesh_reconfigurable_picked_design[1], tor_reconfigurable=flat_reconfigurable_network_total_power, expander=flat_expander_network_total_power)

if __name__ == "__main__":
	print("Power simulator")
	# Run linear regression first to derive power model
	linear_regression_model_for_eps_power()
	# first, set up the topology
	fattree_eps_radix = 32
	small_size_results = small_medium_sized_analysis(fattree_eps_radix / 2)
	medium_size_results = small_medium_sized_analysis(36)
	large_size_results = large_sized_analysis(fattree_eps_radix)
	
	# Start plotting bar chart, preparing results first
	group_seperation = 2
	mpl.rcParams.update({"pgf.texsystem": "pdflatex", 'font.family': 'serif', 'text.usetex': True, 'pgf.rcfonts': False, 'text.latex.preamble': r'\newcommand{\mathdefault}[1][]{}'})
	curr_x = 1
	
	fig, axes = plt.subplots(1, 3, figsize=(0.31 * latex_linewidth_inch, fig_height), dpi=200)
	topology_keys = ["expander", "tor_reconfigurable", "pod_mesh", "pod_tiered", "ft"]
	for ax, topology_results, axis_title, ymax_val in zip(axes, [small_size_results, medium_size_results, large_size_results], ['Small', 'Medium', 'Large'], [0.08, 0.8, 8.9]):
		x, y = [], []
		x_offset = 1
		for topology_key in topology_keys:
			x.append(x_offset)
			y.append(topology_results[topology_key]/1E6)
			x_offset += 2
		barlist = ax.bar(x, y, color=color_cycle, width=1.3)
		# Set hatches for pattern
		for bar_hatch, hatch_pattern in zip(range(len(topology_keys)), ['', '', '', '', '']):
			barlist[bar_hatch].set_hatch(hatch_pattern)
		ax.ticklabel_format(axies='y', style='plain', useOffset=True)
		ax.grid(b=None, which='major', axis='y', linestyle='-', linewidth=0.5)
		ax.grid(b=None, which='minor', axis='y', linestyle=':', linewidth=0.3)
		ax.tick_params(axis="y", labelsize=xyticklabel_fontsize)
		ax.tick_params(axis="x", labelsize=xyticklabel_fontsize)
		ax.set_title(axis_title, fontsize=xylabel_fontsize, pad=1.9)
		ax.set_ylim(ymax=ymax_val)
		rects = ax.patches
		# Make some labels.
		labels = [r"{:.3f}".format(power_consumption) for power_consumption in y]
		for rect, label in zip(rects, labels):
			height = rect.get_height()
			ax.text(rect.get_x() + rect.get_width() / 2, height, label, ha='center', va='bottom', fontsize=xyticklabel_fontsize, rotation=90)
		ax.set_xticks(x)
		ax.set_xticklabels([r"{}".format(arg) for arg in ['EXP', 'TRN', 'PRN-M','PRN-2L', 'FT']], fontsize=xyticklabel_fontsize, rotation=90, ha='left', va='top', )
	# Set the ylabel
	axes[0].set_ylabel(r"Power consumption (MW)", fontsize=xylabel_fontsize, labelpad=0.7)
	#axes[1].legend(['EXP', 'TRN-F', 'PRN-2L', 'FT'])
	plt.subplots_adjust(left=0.2, bottom=0.27, right=0.98, top=0.93, wspace=0.67, hspace=0.2)
	plt.savefig("power_consumption.pgf")
	plt.show()
