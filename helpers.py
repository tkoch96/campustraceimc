import numpy as np, csv, socket, struct, os, re, geopy.distance, json, pickle, time, matplotlib, matplotlib.pyplot as plt
from subprocess import call, check_output
import geoip2.database
from bisect import bisect_left
from constants import *


### This file contains helper functions. I use these helper functions in all my projects
### so some of them might be irrelevant.

def get_figure(l=7,h=3):
	plt.clf()
	plt.close()

	font = {'size'   : 14}
	matplotlib.rc('font', **font)
	f,ax = plt.subplots(1)
	f.set_size_inches(l,h)
	return f,ax

def save_figure(fn):
	plt.savefig(os.path.join('figures', fn), bbox_inches='tight')
	plt.clf()
	plt.close()


def find_mp(arr, v):
	## find insert point of v into arr in log time
	if v < arr[0]:
		return 0
	if v > arr[-1]:
		return len(arr)
	curr_k = len(arr)//2
	if v < arr[curr_k]:
		return find_mp(arr[0:curr_k], v)
	elif v > arr[curr_k]:
		return curr_k + find_mp(arr[curr_k:], v)
	else:
		return curr_k

def domain_to_domainstr(s):
	if s.startswith("https://"):
		s = s[len("https://"):]
	s = s.split("/")[0]
	domain_els = s.split(".")
	if len(domain_els) > 3:
		significant_domain_els = domain_els[-3:]
		domain_str = ".".join(significant_domain_els)
	else:
		domain_str = s
	domain_str = domain_str.replace(",","")
	return domain_str

def fe_to_pop_converter(fe_to_loc, threshold = 150):
	clusters = {}

	def add_to_cluster(fe_loc, cluster):
		clusters[cluster]['fes'].append(fe)
		clusters[cluster]['loc'] = np.mean(np.array([fe_to_loc[fe] for fe in clusters[cluster]['fes']]),axis=0)

	def new_cluster(fe,loc):
		clusters[fe] = {'loc': loc, 'fes': [fe]}

	def check_in_cluster(loc):
		for fe, v in clusters.items():
			if geopy.distance.geodesic(loc, v['loc']).km <= threshold:
				return fe
		return False

	for fe, loc in fe_to_loc.items():
		in_cluster = check_in_cluster(loc)
		if in_cluster:
			add_to_cluster(fe, in_cluster)
		else:
			new_cluster(fe,loc)

	fe_to_pop = {
		'lon': 'london',
		'amb': 'amsterdam',
		'hkg': 'hong kong',
		'sin': 'singapore',
		'sao': 'sao paulo',
		'dba': 'dublin',
		'nyc': 'newyorkcity',
		'tyo': 'tokyo',
		'gva': 'geneva',
		'chg': 'chicago',
		'sel': 'seoul',
		'co': 'washington',
		'wst': 'seattle',
		'sjc': 'sanjose',
		'ash': 'baltimore',
		'par': 'paris',
		'den': 'denver',
		'dal': 'dallas',
		'bom': 'pune',
		'dxb': 'abudhabi',
		'ata': 'atlanta',
	}

	ret = {}
	for v in clusters.values():
		fes = v['fes']
		if len(fes) > 1:
			try:
				pop = [fe_to_pop[_fe] for _fe in fes if _fe in fe_to_pop][0]
			except IndexError:
				print(v)
				continue
		else:
			pop = fes[0]
		for fe in fes:
			ret[fe] = pop

	return ret

def check_ping_responsive(ips, use_file=False, ret_ping=False,tmpoutfn='tmp.warts'):
	ret = []
	out_fn = tmpoutfn
	if use_file:
		# ips is the file name
		scamp_cmd = 'sudo scamper -O warts -c "ping -c 1" -p 10000 -M tak2154atcolumbiadotedu'\
			' -l peering_interfaces -o {} -f {}'.format(out_fn, ips)
		try:
			check_output(scamp_cmd, shell=True)
			cmd = "sc_warts2json {}".format(out_fn)
			out = check_output(cmd, shell=True).decode()
			for meas_str in out.split('\n'):
				if meas_str == "": continue
				measurement_obj = json.loads(meas_str)
				meas_type = measurement_obj['type']
				if meas_type == 'ping':
					dst = measurement_obj['dst']
					if measurement_obj['responses'] != []:
						if ret_ping:
							ret.append(measurement_obj)
						else:
							ret.append(dst)
		except:
			# likely bad input
			import traceback
			traceback.print_exc()
			pass
	else:
		n_chunks = len(ips) // 1000 + 1
		ip_chunks = split_seq(ips,n_chunks)
		for ip_chunk in ip_chunks:
			addresses_str = " ".join(ip_chunk)
			if addresses_str != "":
				scamp_cmd = 'sudo scamper -O warts -c "ping -c 1" -p 8000 -M tak2154atcolumbiadotedu'\
					' -l peering_interfaces -o {} -i {}'.format(out_fn, addresses_str)
				try:
					check_output(scamp_cmd, shell=True)
					cmd = "sc_warts2json {}".format(out_fn)
					out = check_output(cmd, shell=True).decode()
					for meas_str in out.split('\n'):
						if meas_str == "": continue
						measurement_obj = json.loads(meas_str)
						meas_type = measurement_obj['type']
						if meas_type == 'ping':
							dst = measurement_obj['dst']
							if measurement_obj['responses'] != []:
								if ret_ping:
									ret.append(measurement_obj)
								else:
									ret.append(dst)
				except:
					# likely bad input
					import traceback
					traceback.print_exc()
					pass
	return ret

def load_bgp_paths_ping_campaign(fn,load_workers=True, **kwargs):
	ret = {}
	for row in open(fn,'r'):
		try:
			asn,fe,peer_str = row.strip().split('\t')
		except ValueError:
			asn,fe = row.strip().split('\t')
			peer_str = ""
		if asn == "None" or asn == "NA": continue
		if int(asn) >= 1e6: asn = int(asn)
		peers = []
		if peer_str != "":
			for peer in peer_str.split('-'):
				if int(peer) >= 1e6:
					peers.append(int(peer))
				else:
					peers.append(peer)
		try:
			ret[asn,fe] += peers
		except KeyError:
			ret[asn,fe] = peers
		ret[asn,fe] = list(set(ret[asn,fe]))
	if load_workers:
		from subprocess import call
		import glob
		for wfn in glob.glob(fn + "*tmp"):
			this_ret = load_bgp_paths_ping_campaign(wfn,load_workers=False)
			for (asn,fe), peers in this_ret.items():
				try:
					ret[asn,fe] += peers
				except KeyError:
					ret[asn,fe] = peers
				ret[asn,fe] = list(set(ret[asn,fe]))
			call("rm {}".format(wfn),shell=True)
		with open(fn, 'w') as f:
			for (asn,fe), peers in ret.items():
				peers = [str(el) for el in peers]
				peer_str = "-".join(peers)
				f.write("{}\t{}\t{}\n".format(str(asn), fe, peer_str))
	return ret

def save_vf_bgp_peers_paths(obj, fn, save_paths, **kwargs):
	# Saves valid BGP peers/paths to file
	# columns are either asn,fe,peers,paths or asn,peers,paths
	write_mode = kwargs.get('write_mode', 'a')
	with open(fn,write_mode) as f:
		for k in obj:
			peers = []
			for peer in obj[k]['peers']:
				if type(peer) == tuple:
					peers.append(str(peer[0]) + "," + str(peer[1]))
				else:
					peers.append(str(peer))
			peers = list(set(peers))
			peers_str = "-".join(peers)
			if save_paths:
				paths = obj[k]['paths']
				paths_str = ""
				for path in paths:
					paths_str += (";" + "-".join([str(el) for el in path]))
			else:
				paths_str = ""
			if type(k) == tuple:
				f.write("{}\t{}\t{}\t{}\n".format(k[0],k[1],peers_str,paths_str))
			else:
				f.write("{}\t{}\t{}\n".format(k,peers_str,paths_str))

def calc_vf(args):
	"""Calculates valley free paths to Microsoft. Meant to be used in a worker thread."""
	msft_org, as_rel, all_asns, settings, worker_n = args
	cache_fn = settings.get('cache_fn')
	save_paths = settings.get('save_paths', False) # could bloat memory
	if os.path.exists(cache_fn): # cache VF paths since the calcs are expensive
		ret = load_bgp_paths_ping_campaign(cache_fn, load_workers=False)
		ret = {k:{'peers': v, 'paths': None} for k,v in ret.items()}
	else:
		ret = {}
	# Calculate valley free paths
	from mybgpsim import MyBGPSim
	s = MyBGPSim(msft_org)
	s.load_graph(as_rel)
	t_s_calc = time.time()

	for i,asn in enumerate(all_asns):
		if asn in ret: continue
		if type(asn) == tuple:
			if len(asn) == 3:
				asn,pop,_ = asn
			else:
				asn,pop = asn
		else:
			pop = None
		if len([el for el in as_rel if el[0] == asn or el[1] == asn]) > 0:
			if i % 10 == 0 and i > 0:
				t_per_iter = (time.time() - t_s_calc) / i
				t_left = (len(all_asns) - i) * t_per_iter / 3600.0
				print("{} percent done, {} hours remaining in worker {}".format(i*100.0/len(all_asns), round(t_left,2), worker_n))					
			paths, peers = [], []
			# even if we're targeting a FE, just calculate for all FE (since its not much harder)
			# and then prune later
			for path in s.get_vf_paths([asn]): 
				peer = path[-2]
				peers.append(peer)
				paths.append(path)
		else:
			peers = []
			paths = []	
		if pop is not None:
			asn = (asn,pop)

		ret[asn] = {
			"peers": peers,
		}
		if save_paths:
			# Can bloat memory
			ret[asn]['paths'] = paths

		if np.random.random() > .9:
			# save periodically just in case
			out_fn = cache_fn + str(worker_n) + "-tmp"
			save_vf_bgp_peers_paths(ret, out_fn, save_paths)
			ret = {}
			
	print("Done in worker {}".format(worker_n))

	return ret

def haversine(loc1,loc2):
	"""
	Calculate the great circle distance between two points 
	on the earth (specified in decimal degrees)
	"""
	lat1,lon1 = loc1
	lat2,lon2 = loc2
	# convert decimal degrees to radians 
	lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
	# haversine formula 
	dlon = lon2 - lon1 
	dlat = lat2 - lat1 
	a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
	c = 2 * np.arcsin(np.sqrt(a)) 
	# Radius of earth in kilometers is 6371
	km = 6371* c
	return km

def edit_distance(path1, path2, v=False):
	"""Excluding destinations, how many add-remove ops to go from one IP path to the other?"""
	# remove destinations
	path1 = path1[0:-1]
	path2 = path2[0:-1]
	if v:
		print(path1)
		print(path2)
	
	# vote on most common hop
	paths = [path1,path2]
	for i, p in enumerate(paths):
		new_path = []
		for hops in p:
			hops = [h for h in hops if h != "*"]
			if hops == []: continue
			if len(set(hops)) > 1:
				# vote on most common one
				uniques, counts = np.unique(hops,return_counts=True)
				max_c = max(counts)
				new_path.append(uniques[np.where(counts==max_c)[0][0]])
			else:
				new_path.append(hops[0])
		if i == 0: path1 = new_path
		if i == 1: path2 = new_path
	if v:
		print(path1)
		print(path2)
	# now its just an intersection argument
	ed = len(get_difference(path1, path2)) + len(get_difference(path2,path1))
	if v:
		print(ed)
	return ed

def hausdorff(path1, path2):
	"""Returns max-min distance between points on paths 1 and 2. Points are in lat-lon space."""
	# get distances between all points
	# do it once for path 1, once for path 2
	min_distances = []
	try:
		for i in range(len(path1)):
			this_pt = path1[i]
			if this_pt == "?": continue
			try:
				all_distances = []
				for hop2 in path2:
					if hop2 == "?": continue
					all_distances.append(geopy.distance.geodesic(this_pt, hop2).km)
			except:
				print(path1)
				print(path2)
				exit(0)
			min_distance = min(all_distances)
			min_distances.append(min_distance)
		for i in range(len(path2)):
			this_pt = path2[i]
			if this_pt == "?": continue
			try:
				all_distances = []
				for hop1 in path1:
					if hop1 == "?": continue
					all_distances.append(geopy.distance.geodesic(this_pt, hop1).km)
			except:
				print(path1)
				print(path2)
				exit(0)
			min_distance = min(all_distances)
			min_distances.append(min_distance)
	except:
		import traceback
		traceback.print_exc()
		exit(0)
	return max(min_distances)

def get_maxmind_reader():
	fn = os.path.join(DATA_DIR, "GeoLite2-City.mmdb")
	reader = geoip2.database.Reader(fn)
	return reader

def get_ip_loc(ip_addr, ip_to_loc, reader, tolerance=500):
	"""Gets locations of IP address. We could add more methods in here, with different priorities. If 
		the location of ip is already in ip_to_loc, doesn't do anything. Else, tries to find it."""
	try:
		# either we already looked it up, or its in RIPE OpenIP Map project
		ip_to_loc[ip_addr] 
		return ip_to_loc
	except KeyError:
		pass
	
	# As a last resort, try MaxMind
	try:
		response = reader.city(ip_addr)
		# ip_to_loc[ip_addr] = (response.city.name, response.country.name)
		if response.location.accuracy_radius is None:
			ip_to_loc[ip_addr] = "?"
		else:
			if float(response.location.accuracy_radius) <= tolerance: # make sure its accurate enough
				ip_to_loc[ip_addr] = (response.location.latitude, response.location.longitude)
			else:
				ip_to_loc[ip_addr] = "?"
	except geoip2.errors.AddressNotFoundError:
		ip_to_loc[ip_addr] = "?"

	return ip_to_loc

def get_kusto_client(cluster, database, table):
	AAD_TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
	KUSTO_CLUSTER = "https://{}.kusto.windows.net/".format(cluster)
	KUSTO_DATABASE = database
	KCSB = KustoConnectionStringBuilder.with_aad_device_authentication(
		KUSTO_CLUSTER)
	KCSB.authority_id = AAD_TENANT_ID
	KUSTO_CLIENT = KustoClient(KCSB)

	return KUSTO_CLIENT

def temporal_split_kusto_query(cluster, database, table, query, total_time_hours, 
		start_ago=24, out_dir=None, pre_defs=None, time_keyword="['time']", delta=1, save_to_file=True, build_auth=True,
		kusto_client=None, verb=True):
	base_results_dir = KUSTO_RESULTS_DIR
	if build_auth:
		kusto_client = get_kusto_client(cluster, database, table)
	else:
		assert kusto_client is not None
	time_blocks = np.linspace(start_ago, start_ago + total_time_hours, int(total_time_hours/delta)+1)

	# Create dir in which to store all the results
	from subprocess import call
	from datetime import datetime
	if out_dir is not None:
		results_dir = os.path.join(base_results_dir, out_dir)
	else:
		results_dir = os.path.join(base_results_dir, "query_{}".format(datetime.now().strftime("%m%d%Y")))
	if not os.path.exists(results_dir): call("mkdir {}".format(results_dir),shell=True)
	for tbi in range(len(time_blocks) - 1):
		results_fn = os.path.join(results_dir, "{}.csv".format(tbi))
		if os.path.exists(results_fn): continue

		s,e = round(time_blocks[tbi],3), round(time_blocks[tbi+1],3)
		this_timestep_query = "{} | where {} <= ago({}h) and {} > ago({}h) {}".format(
			table, time_keyword, s, time_keyword, e, query)
		if pre_defs is not None:
			this_timestep_query = pre_defs + "\n" + this_timestep_query
		if verb:
			print("\n\n\n{}\n\n\n\n".format(this_timestep_query))
		kusto_response = kusto_client.execute(database, this_timestep_query)
		df = dataframe_from_result_table(kusto_response.primary_results[0])
		if save_to_file:
			df.to_csv(open(results_fn,'w'))
		else:
			yield df

def get_fe_from_device(device_name):
	# Gets the three letter front-end code, which is encoded in device names
	# they should really get a system of global UIDs for all of this...
	try:
		if "ier" in device_name:
			return re.search("ier\d+\.(\D+)\d?", device_name).group(1).replace("-","")
		elif "ter" in device_name:
			return re.search("ter\d+\.(\D+)\d?", device_name).group(1).replace("-","")
		return re.search("^(\D{2,3}).?", device_name).group(1).replace("-","")
	except AttributeError:
		print("Error in get_fe_from_device")
		print(device_name); exit(0)

def get_peer_rel_from_ifalias(ifalias):
	# make sure supersets come before subsets (maps-voice then maps)
	relationships = {
		"onnet": "provider",
		"onnnet": "provider",
		"free": "peer",
		"offnet": "provider", 
		"maps-voice": "provider",
		"maps": "provider",
		"exch": "peer",
		"edgezone":"peer", 
		"sip":"provider",
	}
	if "msit" in ifalias.lower(): return None
	asn_re = re.search("AS(\d{1,6})",ifalias)
	try:
		peer_asn = asn_re.group(1)
	except AttributeError:
		return None
	
	found_rel = False
	for rel in relationships:
		if "peer-" + rel in ifalias.lower():
			found_rel = True
			relationship = relationships[rel]
	if not found_rel:
		relationship = 'peer'

	return peer_asn, relationship

def multi_max(arr):
	"""Arr is a dict k->N, where N is the number of k. Returns key(s) with max number."""
	ks = list(arr.keys())
	all_N = [arr[k] for k in arr]
	most_popular_i = np.argmax(all_N)
	return [k for k,v in arr.items() if v == all_N[most_popular_i]]

def is_bad_ip(ip_address):
	"""Returns true if the ip address is in the private IP space."""
	for net in private_ips:
		try:
			# private IP addresses are bad
			if address_in_network(dotted_quad_to_num(ip_address),dotted_quad_to_num(net[0]),make_mask(net[1])):
				return True
		except:
			# malformed IP addresses are bad
			return True
	return False

def remove_digits(_str):
	# removes digits from a string
	return ''.join([i for i in _str if not i.isdigit()])

def split_seq(seq, n_pieces):
	# splits seq into n_pieces chunks of approximately equal size
	# useful for splitting things to divide among processors
	newseq = []
	splitsize = 1.0/n_pieces*len(seq)
	for i in range(n_pieces):
		newseq.append(seq[int(round(i*splitsize)):int(round((i+1)*splitsize))])
	return newseq

def make_mask(n):
	"""return a mask of n bits as a long integer"""
	return (2<<n-1) - 1

def dotted_quad_to_num(ip):
	"""convert decimal dotted quad string to long integer"""
	return struct.unpack('<L',socket.inet_aton(ip))[0]

def network_mask(ip,bits):
	"""Convert a network address to a long integer"""
	return dotted_quad_to_num(ip) & make_mask(bits)

def address_in_network(ip, net, netmask):
	"""Is an address in a network"""
	return ip & netmask == net

def ip32_to_24(ip):
	return ".".join(ip.split(".")[0:3]) + ".0"

def get_subnet_str(ip_int):
	"""Assuming ip_int is an integer representation of a /24, get the corresponding dotted quad .0/24."""
	msb = int(np.floor(ip_int/(2**16)))
	ip_int -= (msb*2**16)
	mid_sb = int(np.floor(ip_int/2**8))
	ip_int -= (mid_sb*2**8)
	lsb = int(ip_int)
	return str(".".join([str(msb),str(mid_sb),str(lsb), "0"]))

def find_closest_city_from_loc(loc, cities_data):
	# Input is (lat,lon) and cities data from load_cities_data
	# Output is human readable (city, country)
	all_ks = [(c,cn) for c in cities_data for cn in cities_data[c]]
	all_locs = np.array([cities_data[c][cn] for c,cn in all_ks])[:,0:10]
	dists = np.linalg.norm(all_locs - np.array(loc),axis=1)
	closest_k = all_ks[np.argmin(dists)]

	return closest_k

def load_cities_data(prepath="./",us_states=False):
	"""Useful cities data to use in whatever project you need some locations for. The data isn't perfect or complete."""
	cities_data = {} # city -> country -> lat, lon or city -> state is us_stats is True
	with open(os.path.join(prepath,"data", "world_cities.csv"), 'r',encoding='latin1') as f:
		for i, row in enumerate(f):
			fields = row.replace("\"", "").split(',')
			if i == 0: # header
				continue

			city = fields[1].lower().strip()
			country = fields[4].lower().strip()

			if us_states and country == "united states":
				state = fields[7].lower()
				try:
					cities_data[city]
				except KeyError:
					cities_data[city] = {}
				try:
					cities_data[city][state]
					raise ValueError("Multiple values for US City State pair: {} {}".format(city, state))
				except KeyError:
					cities_data[city][state] = (float(fields[2]), float(fields[3]))
				continue

			try:
				cities_data[city]
				try:
					cities_data[city][country]
					#case by case
					state = fields[7].lower()

					if city == "miami" and state != "florida":
						continue
					elif city == "dallas" and state != "texas":
						continue
					elif city == "atlanta" and state != "georgia":
						continue
					elif city == "philadelphia" and state != "pennsylvania":
						continue
					elif city == "washington" and state != "district of columbia":
						continue
					elif city == "jacksonville" and state != "florida":
						continue
					elif city == "montgomery" and state != "alabama":
						continue
					elif city == "newark" and state != "new jersey":
						continue
					elif city == "richmond" and state != "virginia":
						continue
					elif city == "santa fe" and state != "new mexico":
						continue
					elif city == "columbus" and state != "ohio":
						continue
					elif city == "las vegas" and state != "new mexico":
						continue
					elif city == "cleveland" and state != "ohio":
						continue
					elif city == "trenton" and state != "new jersey":
						continue
					#print("Duplicate city, country: %s, %s"%(city, country))
					cities_data[city][country] = (float(fields[2]), float(fields[3]))
				except KeyError:
					cities_data[city][country] = (float(fields[2]), float(fields[3]))

			except KeyError:
				cities_data[city] = {}
				cities_data[city][country] = (float(fields[2]), float(fields[3]))
	return cities_data

class discrete_cdf:
	# Adapted from https://tinyurl.com/y6dlvbsb
	def __init__(self, data,weighted=False):
		self.weighted=weighted
		if weighted:
			# assume data is tuple (value, count of value)
			self._data = [el[0] for el in data]
			self._counts = [el[1] for el in data]
			self._data_len = float(np.sum(self._counts)) # "length" is number of everything
		else:
			self._data = data
			self._data_len = float(len(data))

	def __call__(self, point):
		if self.weighted:
			return np.sum(self._counts[:bisect_left(self._data, point)]) / self._data_len
		else:
			return (len(self._data[:bisect_left(self._data, point)]) /
				self._data_len)

def save_to_csv(data, data_type, fname):
	if data_type == "aggregate":
		# key -> numerical value
		# create list of lists
		csv_out_structure = [[k,v] for k,v in data.items()]
	elif data_type == "distribution":
		# key -> array of values
		tmp = [[k] for k in data.keys()]
		for i in range(len(tmp)):
			[tmp[i].append(el) for el in data[tmp[i][0]]]
		csv_out_structure = tmp
	elif data_type == "msft_data":
		csv_out_structure = [[k, v["client"], v["volume"]] for k,v in data.items()]
	elif data_type == "generic":
		# already in the correct format
		csv_out_structure = data
	else:
		raise ValueError("Data type: %s not recognized."%(data_type))
	with open(fname, 'w') as csv_file:
		writer = csv.writer(csv_file)
		writer.writerows(csv_out_structure)

def load_from_csv(data_type, fname):
	data = {}
	with open(fname, 'r') as f:
		if data_type == "aggregate":
			for row in f:
				fields = row.split(",")
				try:
					data[int(fields[0])] = float(fields[1])
				except ValueError: # v6, or not aggregating
					data[fields[0]] = float(fields[1])
		elif data_type == "distribution":
			for row in f:
				fields = row.split(",")
				try:
					data[int(fields[0])] = np.array([float(el) for el in fields[1:]])
				except ValueError: # v6, or not aggregating
					data[fields[0]] = np.array([float(el) for el in fields[1:]])
		elif data_type == "msft_data":
			for row in f:
				fields = row.split(",")
				data[fields[0]] = {"client": float(fields[1]), "volume": float(fields[2])}
		elif data_type == "generic":
			data = []
			for row in f:
				data.append(row.strip())
		else:
			raise ValueError("Data type: %s not recognized."%(data_type))
	return data

def get_iou(set1, set2):
	"""Gets | intersection | / | union |."""
	return len(get_intersection(set1,set2)) / (len(get_union(set1,set2)) + .0005)


def get_union(set1, set2):
	"""Gets union of two sets."""
	return list(set(set(set1).union(set(set2))))

def get_intersection(set1, set2):
	"""Gets intersection of two sets."""
	return list(set(set(set1) & set(set2)))

def get_difference(set1, set2):
	"""Gets set1 - set2."""
	set1 = set(set1); set2 = set(set2)
	return list(set1.difference(set2))

def prune_v6(data, is_dict=True):
	"""Gets rid of v6 IP entries in either the list or dictionary."""
	def test_v6(ip):
		try:
			# v4
			[int(el) for el in ip.split(".")]
			return False
		except ValueError:
			# v6
			return True
		except AttributeError:
			# integer, so its pre-encoded v4
			return False
	if is_dict:
		return {ip: val for ip,val in data.items() if not test_v6(ip)}
	else:
		return [ip for ip in data if not test_v6(ip)]

def aggregate_list_by_subnet(ip_list, subnet=24, discard_v6=False):
	# Just returns a list of the subnets that encompass this list of ip's
	if subnet == 24:
		def get_subnet_int(ip):
			try:
				# v4
				sub_fields = [int(el) for el in ip.split(".")][0:3]
				# MSB -> LSB
				return sub_fields[0] * (2**16) + sub_fields[1] * (2**8) + sub_fields[2]
			except ValueError:
				# v6 or hashed IP -- dont do subnet stuff (we assume this is a small percentage)
				if discard_v6:
					return None
				else:
					return ip

	else:
		raise ValueError("Subnet of %d not yet supported."%subnet)

	output_with_potential_null_values = list(np.unique([get_subnet_int(ip) for ip in ip_list]))
	return [el for el in output_with_potential_null_values if el]

def aggregate_by_subnet(ip_dict, aggregator=None, subnet=24, discard_v6=False):
	"""It is reasonable to asssume that IP's within a subnet generally represent the same client,
		and for a number of reasons its useful to aggregate this information."""

	# ip_dict is a dictionary of IP -> value pairs where value is some number
	# wish to return subnet dict: subnet -> aggregate values

	if subnet == 24:
		def get_subnet_int(ip):
			try:
				# v4
				sub_fields = [int(el) for el in ip.split(".")][0:3]
				# MSB -> LSB
				return sub_fields[0] * (2**16) + sub_fields[1] * (2**8) + sub_fields[2]
			except ValueError:
				# v6 or hashed IP -- dont do subnet stuff (we assume this is a small percentage)
				if discard_v6: 
					return None
				else:
					return ip

	else:
		raise ValueError("Subnet of %d not yet supported."%subnet)

	aggregate_ip_dict = {}

	for ip, value in ip_dict.items():
		subnet = get_subnet_int(ip)
		if subnet is None:
			continue
		try:
			if aggregator is None:
				aggregate_ip_dict[subnet] += value
			else:
				# some other way of managing this information
				aggregate_ip_dict[subnet] = aggregator(aggregate_ip_dict[subnet], value)
		except KeyError:
			aggregate_ip_dict[subnet] = value

	return aggregate_ip_dict

def get_cdf_xy(data, logx=False, logy=False, n_points = 500, weighted=False,
	cutoff=None, default_log_low = -1):
	"""Returns x, cdf for your data on either log-lin or lin-lin plot."""

	# sort it
	if weighted:
		data.sort(key = lambda val : val[0]) # sort by the value, not the weight of the value
	else:
		data.sort()
	if cutoff:
		# trim off some values
		if not weighted:
			weighted = True
			data = [(el,1) for el in data] # this just allows for more code reuse
		weights = [el[1] for el in data]
		cutoff_weight = sum(weights) * cutoff["p_ile"]
		if cutoff["sym"]:
			# find when the cum weight exceeds the cutoff
			c_s = 0
			for lower_ind, weight in enumerate(weights):
				c_s += weight
				if c_s > cutoff_weight:
					break
		else:
			lower_ind = 0
		c_s = 0
		for i, weight in enumerate(reversed(weights)):
			c_s += weight
			if c_s > cutoff_weight:
				break
		upper_ind = len(weights) - i - 1
		data = data[lower_ind:upper_ind]

	if logx:
		if weighted:
			if data[0][0] <= 0:
				log_low = default_log_low; 
			else:
				log_low = np.floor(np.log10(data[0][0]))
			log_high = np.ceil(np.log10(data[-1][0]))
		else:
			if data[0] <= 0: # check for bad things before you pass them to log
				log_low = default_log_low
			else:
				log_low = np.floor(np.log10(data[0]))
			log_high = np.ceil(np.log10(data[-1]))
		x = np.logspace(log_low,log_high,num=n_points)
	elif logy:
		# Do an inverted log scale on the y axis to get an effect like
		# .9, .99, .999, etc
		# not implemented
		log_low = -5
		log_high = 0
		x = np.linspace(data[0], data[-1], num=n_points)
	else:
		if weighted:
			x = np.linspace(data[0][0], data[-1][0], num=n_points)
		else:
			x = np.linspace(data[0], data[-1],num=n_points)

	# Generate the CDF
	cdf_data_obj = discrete_cdf(data, weighted=weighted)
	cdf_data = [cdf_data_obj(point) for point in x]

	return [x, cdf_data]

from cymruwhois import Client
def lookup_asn(ips):
	"""Looks up ASNs for IP addresses using the cymruwhois Python library."""
	print("----Looking up ASN for {} IP addresses----".format(len(ips)))
	ips = [ip for ip in ips if not is_bad_ip(ip)]
	ip_to_asn = {}
	def perform_lookup(ip_chunk):
		c = Client()
		this_r = c.lookupmany_dict(ip_chunk)
		return this_r
	n_chunks = len(ips) // 5000 + 1 # don't grab too many at once
	ip_chunks = split_seq(ips, n_chunks)
	r = {}
	for i, ip_chunk in enumerate(ip_chunks):
		if i > 0 and np.random.random() > .9:
			print("{} percent done looking up ASNs.".format(i*100.0/len(ip_chunks)))
		done = False
		max_n_retries, n_retries = 3, 0
		while not done and n_retries < max_n_retries:
			try:
				this_r = perform_lookup(ip_chunk)
				for ans in this_r:
					r[ans] = this_r[ans]
				done = True
			except:
				print("Failed to fetch, retrying.")
				print(ip_chunk)
				n_retries += 1
				continue
	for ip,v in r.items():
		ip_to_asn[ip] = v.asn
	return ip_to_asn

def get_as_path(raw_as_path, as_siblings, v=False):
	# The input is an AS path 
	# This function removes doubles, collapses siblings, and removes loops


	# Remove doubles and collapse siblings
	as_path = []
	prev_as = None
	for i, hop in enumerate(raw_as_path):
		try:
			# alias siblings together
			org_hop = as_siblings[hop]
		except KeyError:
			org_hop = hop
		if prev_as is None and org_hop not in ["None", "NA"]:
			as_path.append({
				"actual":hop,
				"org":org_hop,
			})
			prev_as = org_hop
			continue
		elif prev_as is None:
			continue
		if v:
			print("P AS: {} AS: {}".format(prev_as, hop))

		if org_hop == prev_as: continue
		as_path.append({
			"actual": hop,
			"org": org_hop,
			})
		if org_hop not in [None, "None", "NA"]:
			prev_as = org_hop

	as_path = [hop for hop in as_path if hop["org"] not in ["None", "NA"]]

	# Now remove loops
	# loops are likely due to siblings we don't have data for, or load balancing on paths
	max_i,i=5,0
	while len(set([hop['org'] for hop in as_path])) != len(as_path) and i<max_i:
		org_path = np.array([hop['org'] for hop in as_path])
		unique_hops,counts = np.unique(org_path, return_counts=True)
		for u,c in zip(unique_hops,counts):
			if c > 1:
				try:
					assert c == 2 # TODO -- implement
				except AssertionError:
					return as_path # just don't remove the loops
				# loop
				first_occurence = np.where(org_path == u)[0][0]
				second_occurence = np.where(org_path == u)[0][1]
				as_path = as_path[0:first_occurence] + as_path[second_occurence:]
				break
		i = i + 1
	return as_path

