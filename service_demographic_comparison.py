from constants import *
from helpers import *
import os, numpy as np,tqdm, random
from domain_metrics import *
from service_mapping import Service_Mapper

DEMO_TO_PLOT_LABEL = {
	'grad': "Graduate",
	'undergrad': "Undergraduates",
	'all traffic': "All Traffic",
	'mixed_demo': "Mixed Residents",
	'pdocsfacstaff': "Post-Docs &\nFaculty",
	'gradfacstaff': "Graduate &\nFaculty",
	'facstaff': "Faculty",
}
serv_to_lab = {
	'youtube': "Youtube",
	'icloud': 'iCloud',
	'primevideo': "Prime\nVideo",
	'netflix': 'Netflix',
	'instagram': 'Instagram',
	'applestore': 'Apple Store',
	'steam': 'Steam',
	'tiktok': 'TikTok',
	'hulu': '\n  Hulu'
}

class Service_Demographic_Comparison():
	def __init__(self):
		self.all_building_subnets = [
			"160.39.40.128", "160.39.41.128", "160.39.61.128", "160.39.61.0", # grad students
			"160.39.62.192", "160.39.62.128", "160.39.62.0", "160.39.63.128", "160.39.63.64", "160.39.63.0", # grad students
		    "160.39.2.0", # undergraduate students in the School of General Studies
		    "160.39.41.0", "160.39.56.128", "160.39.59.0", # students, faculty and staff
		    "128.59.122.128", "160.39.21.128", "160.39.22.0", "160.39.38.128", # postdocs, faculty and staff
		    "160.39.22.128", "160.39.23.0", "160.39.31.128","160.39.32.0", "160.39.33.128", # faculty and staff
		    "160.39.33.192", "160.39.33.64", "160.39.34.192", "160.39.35.0","160.39.35.64", "160.39.36.64", # faculty and staff
		]
		self.subnet_to_nunits = {
			'160.39.40.128': 36,
			'160.39.41.128': 24,
			'160.39.61.128': 24,
			'160.39.61.0': 53,
			'160.39.62.192': 29,
			'160.39.62.128': 24,
			'160.39.62.0': 37,
			"160.39.63.128": 23,
			"160.39.63.64": 24,
			"160.39.63.0": 23,
			'160.39.2.0': 107,
			"160.39.41.0": 34,
			"160.39.56.128": 24,
			"160.39.59.0": 55,
			"128.59.122.128": 31,
			"160.39.21.128": 23,
			"160.39.22.0": 46,
			"160.39.38.128": 65,
			"160.39.22.128": 31,
			"160.39.23.0": 25,
		    "160.39.31.128": 27,
		    "160.39.32.0": 25,
		    "160.39.33.128": 25,
		    "160.39.33.192": 25,
		    "160.39.33.64": 45,
		    "160.39.34.192": 23,
		    "160.39.35.0": 45,
		    "160.39.35.64": 23,
		    "160.39.36.64": 9,
		}

	def temporal_representativity(self):
		np.random.seed(31415)
		plt_cache_fn = os.path.join(CACHE_DIR, 'temporal_representativity_plot_cache.pkl')
		if not os.path.exists(plt_cache_fn):
			self.setup_service_by_hour_data()
			self.service_bytes_by_divider = self.service_bytes_by_hour
			# self.get_dist_mat('hour', euclidean )
			self.get_domains_arr('hour')

			nunits = len(self.service_bytes_by_divider)
			ndays = nunits
			print("{} dividers total".format(nunits))
			units = list(self.service_bytes_by_divider)

			### Q: let x = global service average
			## how does err(mean[included_set] - x) vary as we include more in the set?
			if False:
				nsim_atmost = 15
				errs_over_n_sim = np.zeros((nsim_atmost, nunits-1))
				for i in range(nsim_atmost):
					ordering = np.arange(nunits)
					np.random.shuffle(ordering)
					current_average = self.domains_arr[ordering[0],:]
					current_sum = self.domains_arr[ordering[0],:]
					next_sum = current_sum.copy()
					next_average = current_average.copy()
					for j in range(nunits-1):
						next_unit = ordering[j+1]

						next_sum += self.domains_arr[next_unit,:]
						next_average = next_sum / np.sum(next_sum)
						errs_over_n_sim[i,j] = 1-pdf_distance(current_average, next_average)

						current_sum = next_sum.copy()
						current_average = next_average.copy()
						# print(current_average[0:10])
			else:
				ndays = 30
				nsim_atmost = np.maximum(nunits - ndays,1)
				errs_over_n_sim = np.zeros((nsim_atmost, ndays))
				for i in range(nsim_atmost):
					ordering = np.arange(i,i+ndays)
					current_average = self.domains_arr[ordering[0],:]
					current_sum = self.domains_arr[ordering[0],:]
					next_sum = current_sum.copy()
					next_average = current_average.copy()
					for j in range(ndays-1):
						next_unit = ordering[j+1]
						next_sum += self.domains_arr[next_unit,:]
						next_average = next_sum / np.sum(next_sum)
						errs_over_n_sim[i,j] = 1-pdf_distance(current_average, next_average)

						current_sum = next_sum.copy()
						current_average = next_average.copy()

			pickle.dump({
				'errs_over_n_sim': errs_over_n_sim,
				'nunits':nunits,
				}, open(plt_cache_fn,'wb'))
		else:
			d = pickle.load(open(plt_cache_fn,'rb'))
			errs_over_n_sim = d['errs_over_n_sim']
			nunits = d['nunits']

		plt_arr = {k: errs_over_n_sim.shape[1] for k in ['min','med','max', 'std']}
		plt_arr['min'] = np.min(errs_over_n_sim, axis=0).flatten()
		plt_arr['med'] = np.median(errs_over_n_sim,axis=0).flatten()
		plt_arr['max'] = np.max(errs_over_n_sim,axis=0).flatten()
		plt_arr['std'] = np.std(errs_over_n_sim,axis=0).flatten()

		overall_max = np.max(plt_arr['max'])

		import matplotlib
		matplotlib.rcParams.update({'font.size': 18})
		import matplotlib.pyplot as plt
		f,ax = plt.subplots(1,1)
		f.set_size_inches(12,4)
		ax.plot(np.arange(1,len(plt_arr['med'])+1), plt_arr['med']/overall_max)
		ax.fill_between(np.arange(1,len(plt_arr['med'])+1), (plt_arr['med'] - plt_arr['std'])/overall_max,
			(plt_arr['med'] + plt_arr['std']) / overall_max, alpha=.3, color='red')
		ax.grid(True)
		ax.set_xlabel("Days for Comparison",fontsize=20)
		# ax.set_ylabel("Normalized Median\nBhattacharyyar Distance",fontsize=20)
		ax.set_ylabel("Marginal Impact",fontsize=20)
		ax.set_ylim([0,1.0])
		plt.savefig("figures/day_representativeness.pdf", bbox_inches='tight')

	def unit_representativity(self, **kwargs):
		np.random.seed(31415)

		ordering_type = ['ordered','mixed']
		nsims_atmost = {'mixed': 200, 'ordered': 10}

		for ot in ordering_type:
			plt_cache_fn = os.path.join(CACHE_DIR, 'unit_representativity_plot_cache_{}.pkl'.format(ot))
			if not os.path.exists(plt_cache_fn):
				# self.setup_service_by_unit_data()
				self.setup_service_data(**kwargs)
				self.service_bytes_by_divider = self.service_bytes_by_building
				self.get_dist_mat('building', euclidean )

				nunits = len(self.service_bytes_by_divider)
				units = list(self.service_bytes_by_divider)

				demo_u, tmp = [], {}
				for c in self.cats_buildings:
					try:
						tmp[c] += 1
					except KeyError:
						demo_u.append(c)
						tmp[c] = 1
				demo_c = [tmp[du] for du in demo_u]

				### Q: let x = global service average
				## how does err(mean[included_set] - x) vary as we include more in the set?

				nsim_atmost = nsims_atmost[ot]
				errs_over_n_sim = np.zeros((nsim_atmost,nunits-1))
				nunits_over_sim = np.zeros((nsim_atmost,nunits-1))
				for i in range(nsim_atmost):
					ordering = np.arange(nunits)
					if ot == 'mixed':
						np.random.shuffle(ordering)
					else:
						ordering = []
						cs = 0 # cumsum
						for _u,_c in zip(demo_u,demo_c):
							o = np.arange(cs,cs+_c)
							np.random.shuffle(o)
							ordering = ordering + list(o)
							cs += _c

					current_average = self.domains_arr[ordering[0],:]
					current_sum = self.domains_arr[ordering[0],:]
					next_sum = current_sum.copy()
					next_average = current_average.copy()
					for j in range(nunits-1):
						next_unit = ordering[j+1]

						next_sum += self.domains_arr[next_unit,:]
						next_average = next_sum / np.sum(next_sum)
						errs_over_n_sim[i,j] = 1-pdf_distance(current_average, next_average)
						nunits_over_sim[i,j] = self.subnet_to_nunits[self.in_order_dividers['building'][next_unit]]

						current_sum = next_sum.copy()
						current_average = next_average.copy()
						# print(current_average[0:10])

				d = {
					'errs_over_n_sim': errs_over_n_sim,
					'nunits_over_sim': nunits_over_sim,
					'nunits':nunits,
					'demo_u': demo_u,
					'demo_c': demo_c,
					}
				pickle.dump(d, open(plt_cache_fn,'wb'))
			else:
				d = pickle.load(open(plt_cache_fn,'rb'))
				errs_over_n_sim = d['errs_over_n_sim']
				nunits_over_sim = d['nunits_over_sim']
				nunits = d['nunits']

			plt_arr = {k: np.zeros(nunits-1) for k in ['min','med','max', 'std']}
			plt_arr['min'] = np.min(errs_over_n_sim, axis=0)
			plt_arr['med'] = np.median(errs_over_n_sim,axis=0)
			plt_arr['max'] = np.max(errs_over_n_sim,axis=0)
			plt_arr['std'] = np.std(errs_over_n_sim,axis=0)

			overall_max = np.max(plt_arr['max'])

			nunits_x = np.median(np.cumsum(nunits_over_sim,axis=1), axis=0)

			import matplotlib
			matplotlib.rcParams.update({'font.size': 18})
			import matplotlib.pyplot as plt
			f,ax = plt.subplots(1,1)
			f.set_size_inches(12,4)
			ax.plot(nunits_x, plt_arr['med']/overall_max)
			ax.fill_between(nunits_x, (plt_arr['med'] - plt_arr['std'])/overall_max,
				(plt_arr['med'] + plt_arr['std']) / overall_max, alpha=.3, color='red')

			if ot == 'ordered':
				demo_u = d['demo_u']
				demo_c = d['demo_c']
				i=0
				cs = 1
				for u,c in zip(demo_u,demo_c):
					print("{} {} {}".format(u,c,cs))
					if cs >= len(nunits_x):
						cs = -1
					ax.axvline(nunits_x[cs-1],0,1)
					ax.text(nunits_x[cs-1],.8-i*.1,DEMO_TO_PLOT_LABEL[u])

					cs+=c
					i+=1

			ax.grid(True)
			ax.set_xlabel("Units Averaged Over",fontsize=20)
			# ax.set_ylabel("Normalized Median\nBhattacharyyar Distance",fontsize=20)
			ax.set_ylabel("Marginal Impact",fontsize=20)
			ax.set_ylim([0,1.0])
			plt.savefig("figures/building_representativeness-{}.pdf".format(ot),bbox_inches='tight')

	def setup_activity_comparison_data(self, **kwargs):
		### Want to build separator by activity measure
		### i.e., DNS -> dns requests corresponding to service for each service
		self.sm = Service_Mapper()
		self.activity_by_service = self.sm.get_service_activity_measure_dists(**kwargs)

		self.all_services = list(set(service for unit,services in self.activity_by_service.items()
			 for service in services))

		self.units = sorted(list(self.activity_by_service))
		print(self.units)

		self.in_order_dividers = {
			'activity_measure': self.units,
		}

	def compare_activity_measures(self, metric, **kwargs):
		self.setup_activity_comparison_data(**kwargs)
		divider_type = 'activity_measure'
		print("\n\n-----DIVIDING BY TYPE {}------".format(divider_type))

		service_bytes_by_divider = self.activity_by_service
		self.service_bytes_by_divider = service_bytes_by_divider
		dist_mat = self.get_dist_mat(divider_type, metric, **kwargs)
		dmat_sum = np.sum(dist_mat, axis=0)
		
		cats = ['Traffic', "DNS\nResponses", 'Flows', "Flow\nDuration"]
		

		import matplotlib
		matplotlib.rcParams.update({'font.size': 18})
		import matplotlib.pyplot as plt
		service_or_type = kwargs.get('service_or_type', 'service')
		xticklocs, xticks = [1], ['1']
		if service_or_type == 'service':
			n_to_plot = 100
			for ploti in range(len(cats) + 2):
				f,ax = plt.subplots(1,1)
				f.set_size_inches(12,4)
				linestyles=['-', '-.', ':','--']

				if ploti == len(cats) + 1:
					ordering = ['Flows','Flow\nDuration','DNS\nResponses','Traffic']
				else:
					ordering = ['Traffic', "DNS\nResponses", "Flow\nDuration", "Flows"]
				for i,lab in enumerate(ordering):
					if i >= ploti: break
					divideri = np.where(np.array(cats)==lab)[0][0]
					ax.semilogx(np.arange(1,n_to_plot+1), self.domains_arr[divideri,0:n_to_plot]*100.0,
						label=cats[divideri],linestyle=linestyles[divideri],marker='o')
					if cats[i] == 'Traffic':
						for i in range(8):
							yloc = ((-1)**i - 1) * 1 + self.domains_arr[divideri,i]*100
							yloc=0
							if i == 0:
								xloc = 1
							elif i <= 4:
								xloc = i+1
							else:
								xloc = i+2
							print("{} {} {}".format(xloc,yloc,serv_to_lab.get(self.all_services[i])))
							# ax.text(xloc,yloc,serv_to_lab.get(self.all_services[i]),fontsize=16, rotation=40)
							xticklocs.append(xloc+.002)
							xticks.append(serv_to_lab.get(self.all_services[i]))
				xticklocs.append(11)
				xticklocs.append(100)
				xticks.append('10')
				xticks.append('100')
				ax.set_xlabel("Overall Service Traffic Volume Contribution Rank")
				ax.set_ylabel("Percent of Total Activity (%)")
				ax.set_xticks(xticklocs)
				ax.set_xticklabels(xticks,rotation=40,fontsize=14)
				ax.set_ylim([0,15])
				ax.set_xlim([1,n_to_plot])

				if ploti == len(cats) + 1:
					ax.legend()
					plt.savefig('figures/activity_measures_topn-{}.pdf'.format(service_or_type), bbox_inches='tight')
				else:
					plt.savefig('figures/activity_measures_topn_{}-{}.png'.format(ploti, service_or_type))

				plt.clf(); plt.close()



		n_dividers = len(self.service_bytes_by_divider)
		fig, axs = plt.subplots(n_dividers, n_dividers, figsize=(11 , 10))
		sorted_rows = list(reversed(np.argsort(dmat_sum)))
		for divideri in range(n_dividers):
			for dividerj in range(n_dividers):

				axs[divideri, dividerj].imshow(np.array([[dist_mat[sorted_rows[divideri],
					sorted_rows[dividerj]]]]), 
					cmap='coolwarm', vmin=0, vmax=1)
				# axs[divideri, dividerj].axis('off')
				axs[divideri, dividerj].set_xticks([])
				axs[divideri, dividerj].set_yticks([])
				axs[divideri, dividerj].set_aspect('equal')

		def divideri_to_lab(divideri):
			return cats[divideri]

		for i,divideri in enumerate(sorted_rows):
			axs[0,i].set_xlabel(divideri_to_lab(divideri), rotation=45, fontsize=18)
			axs[0,i].xaxis.set_label_position('top')
			axs[0,i].xaxis.set_label_coords(.5, 1)
		for i,divideri in enumerate(sorted_rows):
			axs[i,0].set_ylabel(divideri_to_lab(divideri), rotation=45, fontsize=18)
			axs[i,0].yaxis.set_label_coords(-.25, .2)

		# print(dist_mat.round(2))
		# Add colorbar
		norm = plt.Normalize(0, 1)
		cmap = plt.get_cmap('coolwarm')
		cax = fig.add_axes([0.91, 0.1, 0.02, 0.8])
		cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
		cb.ax.set_ylabel(kwargs.get('axis_lab'), fontsize=20)
		fig.subplots_adjust(right=.90)
		
		# Adjust spacing and show plot
		plt.subplots_adjust(wspace=-.5, hspace=-.05)
		# plt.show()
		plt.savefig('figures/similarities_across_{}-{}-{}.pdf'.format(
			divider_type, kwargs.get('plt_lab',''), service_or_type))
		plt.clf(); plt.close()

	def setup_service_by_hour_data(self, **kwargs):
		print("Setting up service by hour data...")
		try:
			self.all_services
			return
		except AttributeError:
			pass
		sm = Service_Mapper()
		self.service_bytes_by_hour = sm.get_service_bytes_by_separator(by='hour', **kwargs)

		self.all_services = list(set(service for hour,services in self.service_bytes_by_hour.items()
			 for service in services))


		self.hours = sorted(list(self.service_bytes_by_hour))

		self.in_order_dividers = {
			'hour': sorted(self.hours),
		}

	def get_domains_arr(self, divider_type):
		self.bytes_by_service = {}
		for div in self.service_bytes_by_divider:
			for s,nb in self.service_bytes_by_divider[div].items():
				try:
					self.bytes_by_service[s] += nb
				except KeyError:
					self.bytes_by_service[s] = nb
		self.all_services = sorted(self.all_services, key = lambda s : -1*self.bytes_by_service[s])
		service_to_i = {service:i for i,service in enumerate(self.all_services)}
		n_dividers = len(self.service_bytes_by_divider)
		divider_to_i = {divider:i for i,divider in enumerate(self.in_order_dividers[divider_type])}
		self.domains_arr = np.zeros((n_dividers, len(self.all_services)))
		print(self.domains_arr.shape)
		for divider,services in self.service_bytes_by_divider.items():
			for service,nb in services.items():
				self.domains_arr[divider_to_i[divider],service_to_i[service]] = nb

		nb_by_divider = np.sum(self.domains_arr,axis=1)
		self.domains_arr = self.domains_arr / nb_by_divider.reshape((-1,1))

	def get_dist_mat(self, divider_type, metric, **kwargs):
		print("Computing distance matrix...")
		n_dividers = len(self.service_bytes_by_divider)
		print("{} dividers, {} services".format(n_dividers, len(self.all_services)))

		for divider in list(self.service_bytes_by_divider):
			services = list(self.service_bytes_by_divider[divider])
			for not_inc_service in get_difference(self.all_services,services):
				self.service_bytes_by_divider[divider][not_inc_service] = 0
		self.get_domains_arr(divider_type)
		

		if divider_type == 'building':
			interesting_prints = []
		elif divider_type in ['category','activity_measure']:
			interesting_prints = list(range(n_dividers))
		else:
			interesting_prints = []

		if len(interesting_prints) > 0:
			n_to_print = 100
			divider_type_service_rank = {}
			with open(os.path.join(CACHE_DIR, 'exports', 'popularities-{}-{}.csv'.format(
				divider_type, kwargs.get('service_or_type', 'service'))), 'w') as f:
				f.write(",".join(self.in_order_dividers[divider_type]) + "\n")
				write_arr = {}
				
				for divideri in interesting_prints:
					max_n = np.sum(self.domains_arr[divideri,:])
					print("Divider {}".format(self.in_order_dividers[divider_type][divideri]))
					divider_type_service_rank[self.in_order_dividers[divider_type][divideri]] = {}
					for j,i in enumerate(np.argsort(self.domains_arr[divideri,:])[::-1][0:n_to_print]):
						divider_type_service_rank[self.in_order_dividers[divider_type][divideri]][self.all_services[i]] = j
						print("{} -- {} {}".format(i,self.all_services[i],round(self.domains_arr[divideri,i]*100.0/max_n,4)))
						if type(self.all_services[i]) == tuple:
							s = "--".join([str(el) for el in self.all_services[i]])
						else:
							s = self.all_services[i]
						write_arr[j,divideri] = s + " ({} pct.)".format(round(self.domains_arr[divideri,i]*100.0/max_n,4))
				for i in range(n_to_print):
					try:
						f.write(",".join([str(write_arr[i,j]) for j in range(len(self.in_order_dividers[divider_type]))]) + "\n")
					except KeyError:
						break

			## Comment on what swings the most
			print(divider_type_service_rank)
			diffs = list([((div1,subd1),(div2,subd2),divider_type_service_rank[div1][subd1] - \
				divider_type_service_rank[div2][subd2]) for div1 in divider_type_service_rank
				for div2 in divider_type_service_rank for subd1 in divider_type_service_rank[div1]
				for subd2 in divider_type_service_rank[div2] if subd1==subd2])
			sdiffs = sorted(diffs, key = lambda el : -1 * np.abs(el[2]))
			print("BIGGEST SWINGS")
			print(sdiffs[0:10:2])

		dist_mat = np.zeros((n_dividers,n_dividers))
		from sympy.combinatorics.permutations import Permutation
		for divideri in tqdm.tqdm(range(n_dividers),desc="Calculating distances..."):
			for dividerj in range(n_dividers):
				if dividerj>divideri: break
				
				d = metric(self.domains_arr[divideri,:], self.domains_arr[dividerj,:], **kwargs)

				dist_mat[divideri,dividerj] = d
				dist_mat[dividerj,divideri] = d


		dist_mat = dist_mat - np.min(dist_mat.flatten())
		dist_mat = dist_mat / np.max(dist_mat.flatten())

		return dist_mat

	def setup_service_data(self, **kwargs):
		try:
			self.all_services
			return
		except AttributeError:
			pass
		sm = Service_Mapper()
		self.service_bytes_by_building = sm.get_service_bytes_by_separator(**kwargs)

		self.all_services = list(set(service for building,services in self.service_bytes_by_building.items()
			 for service in services))

		### TODO -- make this more dynamic
		# ncats,cats = [10,1,3,4,11],['grad','undergrad','gradfacstaff','pdocsfacstaff','facstaff']
		# ncats,cats = [11,3,4,11],['grad','gradfacstaff','pdocsfacstaff','facstaff']
		ncats,cats = [11,7,11], ['grad','mixed_demo','facstaff']
		cats = [c for i,c in enumerate(cats) for n in range(ncats[i]) ]
		building_subnets = [b for b in self.all_building_subnets if b in self.service_bytes_by_building]
		self.cats_buildings = [c for c,b in zip(cats, self.all_building_subnets) if b in self.service_bytes_by_building]

		self.in_order_dividers = {
			'building': building_subnets,
			#'category': ['all traffic','grad','facstaff'], ### SHUYUE PRESENTATION
			# 'category': ['grad','undergrad', 'gradfacstaff','pdocsfacstaff','facstaff','all traffic'], # without GS in grad
			# 'category': ['grad', 'gradfacstaff','pdocsfacstaff','facstaff','all traffic'], # moved GS into grad
			'category': ['grad', 'mixed_demo','facstaff','all traffic'], # combined some cats
		}

		## aggregate to pseudo buildings, with each category being a building
		self.service_bytes_by_category = {'all traffic': {}}
		for bsnet,cat in zip(building_subnets,self.cats_buildings):
			try:
				self.service_bytes_by_category[cat]
			except KeyError:
				self.service_bytes_by_category[cat] = {}

			for service,nb in self.service_bytes_by_building[bsnet].items():
				try:
					self.service_bytes_by_category[cat][service] += nb
				except KeyError:
					self.service_bytes_by_category[cat][service] = nb
		for cat in self.service_bytes_by_category:
			total_n_b = sum(list(self.service_bytes_by_category[cat].values()))
			for s in self.service_bytes_by_category[cat]:
				self.service_bytes_by_category[cat][s] = self.service_bytes_by_category[cat][s] / total_n_b
		for cat in self.service_bytes_by_category:
			for service,nb in self.service_bytes_by_category[cat].items():
				try:
					self.service_bytes_by_category['all traffic'][service] += nb
				except KeyError:
					self.service_bytes_by_category['all traffic'][service] = nb

	def compare_building_domains(self, metric, **kwargs):
		self.setup_service_data(**kwargs)		

		for service_bytes_by_divider,divider_type in zip([self.service_bytes_by_building,self.service_bytes_by_category], 
				['building','category']):
			print("\n\n-----DIVIDING BY TYPE {}------".format(divider_type))
			if divider_type == 'building': continue

			self.service_bytes_by_divider = service_bytes_by_divider
			# ### FOR SHUYUE PRESENTATION
			# self.service_bytes_by_divider = {k:self.service_bytes_by_divider[k] for k in ['all traffic', 'grad', 'facstaff']}
			# ### 
			dist_mat = self.get_dist_mat(divider_type, metric, **kwargs)
			dmat_sum = np.sum(dist_mat, axis=0)

			def divideri_to_lab(divideri):
				if divider_type == 'building':
					return self.cats_buildings[divideri]
				else:
					category = self.in_order_dividers['category'][divideri]
					category_to_plot_label = DEMO_TO_PLOT_LABEL
					return category_to_plot_label[category]

			import matplotlib
			matplotlib.rcParams.update({'font.size': 18})
			import matplotlib.pyplot as plt
			service_or_type = kwargs.get('service_or_type', 'service')
			if service_or_type == 'service':
				n_to_plot = 100
				f,ax = plt.subplots(1,1)
				f.set_size_inches(12,4)
				linestyles=['-', '-.','--',':']

				# ordering = ['Flows','Flow\nDuration','DNS\nResponses','Bytes']
				# for i,lab in enumerate(ordering):
					# divideri = np.where(np.array(cats)==lab)[0][0]

				xticklocs, xticks = [1], ['1']
				for divideri in range(self.domains_arr.shape[0]):
					if divideri_to_lab(divideri) == 'Mixed Residents':
						continue
					ax.semilogx(np.arange(1,n_to_plot+1), self.domains_arr[divideri,0:n_to_plot]*100.0,
						label=divideri_to_lab(divideri),linestyle=linestyles[divideri], marker='o')
					if divideri_to_lab(divideri) == 'All Traffic':
						for i in range(8):
							yloc = ((-1)**i - 1) * 1 + self.domains_arr[divideri,i]*100
							yloc=0
							if i == 0:
								xloc = 1
							elif i <= 4:
								xloc = i+1
							else:
								xloc = i+2
							print("{} {} {}".format(xloc,yloc,serv_to_lab.get(self.all_services[i])))
							# ax.text(xloc,yloc,serv_to_lab.get(self.all_services[i]),fontsize=16, rotation=40)
							xticklocs.append(xloc+.002)
							xticks.append(serv_to_lab.get(self.all_services[i]))
				xticklocs.append(11)
				xticklocs.append(100)
				xticks.append('10')
				xticks.append('100')
				ax.set_xlabel("Overall Service Traffic Volume Contribution Rank")
				ax.set_ylabel("Percent of Total Traffic Volume (%)")
				ax.set_xticks(xticklocs)
				ax.set_xticklabels(xticks, rotation=40, fontsize=13)
				ax.set_ylim([0,15])
				ax.set_xlim([.9,n_to_plot])

				ax.legend()
				plt.savefig('figures/similarities_across_{}_{}_topn-{}.pdf'.format(
					divider_type, kwargs.get('plt_lab',''), service_or_type),
					bbox_inches='tight')

				plt.clf(); plt.close()
			else:
				self.compare_us_sandvine(metric)

			n_dividers = len(self.service_bytes_by_divider)
			fig, axs = plt.subplots(n_dividers, n_dividers, figsize=(11, 10))
			sorted_rows = list(reversed(np.argsort(dmat_sum)))
			for divideri in range(n_dividers):
				for dividerj in range(n_dividers):

					axs[divideri, dividerj].imshow(np.array([[dist_mat[sorted_rows[divideri],
						sorted_rows[dividerj]]]]), 
						cmap='coolwarm', vmin=0, vmax=1)
					# axs[divideri, dividerj].axis('off')
					axs[divideri, dividerj].set_xticks([])
					axs[divideri, dividerj].set_yticks([])
					axs[divideri, dividerj].set_aspect('equal')

			

			for i,divideri in enumerate(sorted_rows):
				axs[0,i].set_xlabel(divideri_to_lab(divideri), rotation=45, fontsize=18)
				axs[0,i].xaxis.set_label_position('top')
				axs[0,i].xaxis.set_label_coords(.5, .9)
			for i,divideri in enumerate(sorted_rows):
				axs[i,0].set_ylabel(divideri_to_lab(divideri), rotation=45, fontsize=18)
				axs[i,0].yaxis.set_label_coords(-.25, .2)

			# print(dist_mat.round(2))
			# Add colorbar
			norm = plt.Normalize(0, 1)
			cmap = plt.get_cmap('coolwarm')
			cax = fig.add_axes([0.91, 0.1, 0.02, 0.8])
			cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
			cb.ax.set_ylabel(kwargs.get('axis_lab'), fontsize=20)
			fig.subplots_adjust(right=.85)
			
			# Adjust spacing and show plot
			plt.subplots_adjust(wspace=0, hspace=-.2)
			# plt.show()
			plt.savefig('figures/similarities_across_{}-{}-{}.pdf'.format(
				divider_type, kwargs.get('plt_lab',''), service_or_type))
			plt.clf(); plt.close()

	def compare_us_sandvine(self, metric):
		## Sandvine types
		cat_order = ['video', 'gaming', 'marketplace', 'socialmedia', 'cloud', 'misc', 'communication',
			'filesharing', 'music', 'vpn']
		america_type = {k:v for k,v in zip(cat_order, np.array([73.74,5.77,4.19,3.77,3.52,3.34,2.48,1.43,.92,.83])/100)}
		apac_type = {k:v for k,v in zip(cat_order, np.array([66.11,7.33,7.19,3.30,5.11,2.9,2.25,3.37,.8,1.62])/100) }
		emea_type = {k:v for k,v in zip(cat_order, np.array([62.46,3.01,4.2,14.22,2.58,4.38,4.94,2.59,.3,1.33])/100)}

		us_faculty = {}
		print(self.in_order_dividers['category'])
		cat_to_i = {cat:i for i,cat in enumerate(self.in_order_dividers['category'])}
		print(self.all_services)
		servtype_to_i = {c:[i for i in range(len(self.all_services)) if self.all_services[i] == c][0] for c in cat_order}
		print(servtype_to_i)

		fac_type = {cat: self.domains_arr[cat_to_i['facstaff'], servtype_to_i[cat]] for cat in cat_order}
		grad_type = {cat: self.domains_arr[cat_to_i['grad'], servtype_to_i[cat]] for cat in cat_order}
		print(fac_type)
		print(grad_type)

		arrs = [america_type,apac_type,emea_type,fac_type,grad_type]
		labs = ['america','apac','emea','fac','grad']
		i=0
		for arri,li in zip(arrs,labs):
			j=0
			for arrj,lj in zip(arrs,labs):
				d = metric(np.array([arri[k] for k in cat_order]), np.array([arrj[k] for k in cat_order]))
				print("{} vs {} -- {}".format(li,lj,round(d,3)))
				j+= 1
				if j > i: break
			i+= 1

	def crosswise_comparisons(self, **kwargs):
		metrics = [pdf_distance,weighted_jaccard, euclidean,rbo_wrap,spearman, cosine_similarity, jaccard]
		labs = ['bc','wjac', 'euclidean','rbo','spearman', 'cos_sim', 'jac']
		# ax_labs = ['Bhattacharyya Distance', 'Weighted Jaccard Index', 'Euclidean Distance','Rank-Biased Overlap', 'Spearman Correlation', 'Cosine Similarity',
		# 	 'Jaccard Index']
		ax_labs = ['Similarity', 'Weighted Jaccard Index', 'Euclidean Distance','Rank-Biased Overlap', 'Spearman Correlation', 'Cosine Similarity',
			 'Jaccard Index']
		for metric,lab,axis_lab in zip(metrics,labs,ax_labs):
			print("\n\n\nCOMPUTING METRIC {}\n\n\n".format(lab))
			self.compare_building_domains(metric, n_doms=1000, plt_lab=lab, axis_lab=axis_lab, **kwargs)
			self.compare_activity_measures(metric, plt_lab=lab, axis_lab=axis_lab, **kwargs)
			break


	def get_rtts_distances_by_service(self, **kwargs):
		plot_cache_fn = os.path.join(CACHE_DIR, 'rtts-and-distances-plot-cache.pkl')
		if not os.path.exists(plot_cache_fn):
			self.setup_activity_comparison_data(**kwargs)
			self.sm.compute_domains_to_services()
			n_services = 100

			most_popular_services = sorted(list(self.activity_by_service['bytes']), key = lambda el : -1 * self.activity_by_service['bytes'][el])[0:n_services]
			# print("MPS: {}".format(most_popular_services))

			service_to_dst_ip = {mps:{} for mps in most_popular_services}
			for dst_ip,uids in self.sm.dstip_to_domain_sni.items():
				for uid,nb in uids.items():
					try:
						service = self.sm.domain_sni_to_service[uid]
					except KeyError:
						continue
					try:
						service_to_dst_ip[service]
					except KeyError:
						continue
					try:
						service_to_dst_ip[service][dst_ip] += nb
					except KeyError:
						service_to_dst_ip[service][dst_ip] = nb
			service_to_distances = {mps: {} for mps in most_popular_services}
			service_to_rtts = {mps: {} for mps in most_popular_services}
			all_nb, mapped_rtt_nb, mapped_distance_nb = 0,0,0
			rtts = pickle.load(open(os.path.join(CACHE_DIR, 'rtts.pkl'),'rb'))
			distances = pickle.load(open(os.path.join(CACHE_DIR,'distances.pkl'),'rb'))
			dst_ip_locs = pickle.load(open(os.path.join(CACHE_DIR, 'dst_ip_locs.pkl'),'rb'))
			for service in service_to_dst_ip:
				for dst_ip,nb in service_to_dst_ip[service].items():
					all_nb += nb
					try:
						distance = distances[dst_ip]
						try:
							service_to_distances[service][distance] += nb
						except KeyError:
							service_to_distances[service][distance] = nb
						mapped_distance_nb += nb
					except KeyError:
						pass	
					try:
						rtt = rtts[dst_ip]['min']
						try:
							service_to_rtts[service][rtt] += nb
						except KeyError:
							service_to_rtts[service][rtt] = nb
						mapped_rtt_nb += nb
					except KeyError:
						pass
			print("{} pct mapped for RTTs".format(round(100*mapped_rtt_nb/all_nb,2)))
			print("{} pct mapped for Distances".format(round(100*mapped_distance_nb/all_nb,2)))

			rdns_names = {}
			ip_to_rdns = {}
			rdns_to_ip = {}
			for row in open(os.path.join('tmp','addr_to_rdns.txt'), 'r'):
				ip,rdns = row.strip().split('\t')
				rdns = rdns.strip()
				ip = ip.strip()
				if rdns[-1] == ".":
					rdns = rdns[0:-1]
				ip_to_rdns[ip] = rdns.lower()
				rdns_to_ip[rdns.lower()] = ip

			delta_distances_arr, delta_rtts_arr = [], []
			for service in most_popular_services:
				if len(service_to_distances[service]) > 0:
					_distances = list(service_to_distances[service])
					nbs = list([service_to_distances[service][distance] for distance in _distances])
					delta_distances_arr.append(np.average(_distances,weights=nbs) - np.min(_distances))
					if delta_distances_arr[-1] > 0:
						print('\n')
						print("Service {} going on average {} ms away from minimum (distance-wise)".format(service,delta_distances_arr[-1]))
						total_nb = sum(list(service_to_dst_ip[service].values()))
						for dst_ip,nb in sorted(service_to_dst_ip[service].items(), key = lambda el : -1 * el[1]):
							if nb/total_nb > .01:
								try:
									distances[dst_ip]
									dst_ip_locs[dst_ip]
									if distances[dst_ip] > 10:
										print("{} pct of bytes going {} km away to {} ({}) {}".format(
											round(nb * 100.0/total_nb,2), distances[dst_ip], dst_ip_locs[dst_ip],ip_to_rdns.get(dst_ip,'nordns'),dst_ip))
								except KeyError:
									pass
				else:
					print("Note -- absolutely no distance information for service {}".format(service))
				if len(service_to_rtts[service]) > 0:
					_rtts = list(service_to_rtts[service])
					nbs = list([service_to_rtts[service][rtt] for rtt in _rtts])
					delta_rtts_arr.append(np.average(_rtts,weights=nbs) - np.min(_rtts))
				else:
					print("Note -- absolutely no rtt information for service {}".format(service))

			pickle.dump([delta_rtts_arr,delta_distances_arr], open(plot_cache_fn,'wb'))

		else:
			delta_rtts_arr,delta_distances_arr = pickle.load(open(plot_cache_fn,'rb'))


		import matplotlib
		matplotlib.rcParams.update({'font.size': 22})
		import matplotlib.pyplot as plt
		f,ax = plt.subplots(1,1)
		f.set_size_inches(12,3)

		
		x,cdf_x = get_cdf_xy(delta_rtts_arr,logx=True,n_points=80)
		cdf_x = np.array(cdf_x)
		cdf_x = 1 - cdf_x
		ax.semilogx(x,cdf_x,label="RTT",marker='.',markersize=10)
		nm = 'lat'
		for _x in [10,30]:
			print("{} -- {} ms --- {} pct".format(nm,_x,cdf_x[np.argmin(np.abs(x-_x))]))

		delta_distances_arr = np.array(delta_distances_arr) * .01 # convert to ms
		x,cdf_x = get_cdf_xy(delta_distances_arr,logx=True,n_points=80)
		cdf_x = np.array(cdf_x)
		cdf_x = 1 - cdf_x
		ax.semilogx(x,cdf_x,label="Great-Circle Distance",marker='p',markersize=10)
		nm = 'dist'
		for _x in [10,30]:
			print("{} -- {} ms --- {} pct".format(nm,_x,cdf_x[np.argmin(np.abs(x-_x))]))


		ax.legend(fontsize=24)
		ax.set_xlabel("Avg. - Min. Great-Circle Distance / Latency to Service (ms)")
		ax.set_ylabel("CCDF of \nTop-100 Services")
		ax.set_xlim([1,100])
		ax.set_xticks([1,10,100])
		ax.set_yticks([0,.25,.5,.75,1.0])
		ax.set_xticklabels(['1','10','100'])
		ax.grid(True)
		plt.savefig('figures/rtts-and-distances-avg-min-diff.pdf', bbox_inches='tight')

		## Question -- what are these missing services, need to do more traceroutes, make sure calc is how shuyue did hers


if __name__ == "__main__":
	### service -> facetime, hulu, etc
	### type -> video, messaging, etc

	# sdc = Service_Demographic_Comparison()
	# sdc.unit_representativity()
	# sdc = Service_Demographic_Comparison()
	# sdc.temporal_representativity()
	sdc = Service_Demographic_Comparison()
	# sdc.crosswise_comparisons(service_or_type='service')
	# sdc = Service_Demographic_Comparison()
	# sdc.crosswise_comparisons(service_or_type='type')

	sdc = Service_Demographic_Comparison()
	sdc.get_rtts_distances_by_service(service_or_type='service')

