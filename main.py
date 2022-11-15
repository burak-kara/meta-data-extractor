import sys
import os
import threading

SS = "\\"
SLASH = "/"
NEW_LINE = "\n"
DASH = "-"
UNDERSCORE = "_"

# The name of the folder where the videos are stored
VIDEOS = "videos"
# The name of the folder where the server logs are stored
LOGS = "logs"
# The name of the first video
HARBOR = "harbor"
# The name of the second video
TIMELAPSE = "timelapse"
OUTPUT = "output"
MPD = 'mpd'

# Available tile grids
TILES = ["6x4", "8x6", "12x8"]
# Available stream profiles
PROFILES = ["case9-omafv1-live", "case9-omafv2-live", "case9-omafv2-livezipped"]

# ISOBMFF boxes
FTYP = 'ftyp'
STYP = 'styp'
MOOF = 'moof'
MOOV = 'moov'
MDAT = 'mdat'
IMDA = 'imda'
BOXES = [FTYP, STYP, MOOF, MOOV, MDAT, IMDA]

RESULTS = []


def get_video_details(video_folder):
	details = video_folder.split(UNDERSCORE)
	if len(details) == 3:
		return details[0], details[1], '20'
	else:
		return details[0], details[1], '50'


def log_results(video_path, run_binary, run_setup, sizes):
	_, video_folder, tile, profile = video_path.split(SS)
	segment, video, resolution = get_video_details(video_folder)
	tile = tile.split(DASH)[2]
	omaf_version = profile.split(DASH)[1][-2:]
	if profile.find('zipped') != -1:
		omaf_version += '*'
	log = ' '.join([video, segment, resolution, tile, omaf_version, run_binary, str(run_setup['run_count']),
	                ' '.join(map(str, sizes))])
	print(log)
	RESULTS.append(log)


def run_mp4viewer(file_path, output_file_path):
	os.system(
		"python27.exe .\mp4viewer\src\showboxes.py -o stdout -c off {} > {}"
		.format(file_path, output_file_path))


def append_results(original_index_box_sizes, sizes, compression_ratio):
	for key in original_index_box_sizes:
		original_index_box_sizes[key] *= compression_ratio
		sizes[key] += round(original_index_box_sizes[key], 2)


def find_compression_ratio(original_index_path, index_path):
	original_index_size = os.path.getsize(original_index_path)
	index_size = os.path.getsize(index_path)
	ratio = index_size / original_index_size
	if ratio > 0.95:
		ratio = 0.15
	return ratio


def parse_box_info_file(file_path, sizes):
	try:
		with open(file_path) as f:
			lines = f.readlines()
			for line_id in range(len(lines)):
				if any(box in lines[line_id] for box in BOXES) and lines[line_id].find('-') != -1:
					box_name = lines[line_id].split('-')[-1].strip()
					if box_name in [FTYP, STYP]:
						if file_path.find('v1') != -1:
							if box_name == STYP:
								sizes[STYP] += 40
							elif box_name == FTYP:
								sizes[FTYP] += 28
						elif file_path.find('v2') != - 1:
							if box_name == STYP:
								if file_path.find('index') != -1:
									sizes[STYP] += 20
								else:
									sizes[STYP] += 36
							elif box_name == FTYP:
								sizes[FTYP] += 36
					elif lines[line_id + 1].find('size') != -1:
						size = lines[line_id + 1].split(':')[1].strip()
						sizes[box_name] += int(size)
	except Exception as e:
		eprint("index file is not available!")


def handle_zipped_index_file(index_path, file_name, sizes):
	original_index_path = index_path.replace('zipped', '')
	original_index_output_path = original_index_path + SS + file_name[:-4] + "_info.txt"
	original_index_box_sizes = {
		FTYP: 0,
		STYP: 0,
		MOOF: 0,
		MOOV: 0,
		MDAT: 0,
		IMDA: 0
	}
	parse_box_info_file(original_index_output_path, original_index_box_sizes)

	compression_ratio = find_compression_ratio(original_index_path, index_path)
	append_results(original_index_box_sizes, sizes, compression_ratio)


def calculate_video_size(video_path, files):
	sizes = {
		FTYP: 0,
		STYP: 0,
		MOOF: 0,
		MOOV: 0,
		MDAT: 0,
		IMDA: 0
	}
	for file_name in files:
		file_path = video_path + SS + file_name
		output_file_path = video_path + SS + file_name[:-4] + "_info.txt"

		if file_name.find(MPD) != -1:
			continue

		if video_path.find('zipped') != -1 and file_name.find('index') != -1:
			handle_zipped_index_file(video_path, file_name, sizes)
			continue

		if not os.path.isfile(output_file_path):
			try:
				run_mp4viewer(file_path, output_file_path)
			except Exception as e:
				eprint(file_path, e)
				continue

		parse_box_info_file(output_file_path, sizes)
	return sizes


def start_thread(video_path, run_setup, run_binary):
	sizes = calculate_video_size(video_path, run_setup['files'])
	return log_results(video_path, run_binary, run_setup, sizes.values())


def iterate_video_files(video_files, video_paths, video_name):
	for run_binary in video_files:
		threads = []
		for video_path, run_setup in zip(video_paths, video_files[run_binary].values()):
			thread = threading.Thread(target=start_thread, args=(video_path, run_setup, run_binary))
			threads.append(thread)

		for tt in threads:
			tt.start()

		for tt in threads:
			tt.join()
		print('run_binary: {}, video_name: {} is done'.format(run_binary, video_name))


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)


def find_run_setup(line, run_setups):
	for run_setup in run_setups:
		if run_setup + SLASH in line:
			return run_setup
	return None


def init_results(run_setups, run_binaries):
	results = {}
	for run_binary in run_binaries:
		results[run_binary] = {}
		for run_setup in run_setups:
			results[run_binary][run_setup] = {"run_count": 0, "files": []}
	return results


def find_run_binaries(line):
	run_binaries = []
	binaries = line.split(DASH)
	for binary in binaries:
		if binary.find("player2") != -1:
			run_binaries.append("H2")
		elif binary.find("player") != -1:
			run_binaries.append("H1")
	return run_binaries


def parse_server_log(file_path, run_setups):
	with open(file_path) as f:
		lines = f.readlines()
		run_binaries = find_run_binaries(lines[0])
		results = init_results(run_setups, run_binaries)
		run_binary = -1
		for line in lines:
			run_setup = find_run_setup(line, run_setups)
			if run_setup is not None:
				try:
					parsed = line.split()
					if parsed[2].find(MPD) != -1:
						run_binary = (run_binary + 1) % len(run_binaries)
						results[run_binaries[run_binary]][run_setup]["run_count"] += 1
					file_name = parsed[2].split(SLASH)[3][:-6]
					results[run_binaries[run_binary]][run_setup]['files'].append(file_name)
				except Exception as e:
					eprint("segment_bytes caused exception", file_path, e)
					continue
	return results


def get_run_setup(tile, profile):
	return tile + SLASH + profile


def get_tile_folder_name(video_name, tile_grid):
	tile = OUTPUT + DASH
	if TIMELAPSE in video_name:
		tile += TIMELAPSE
	else:
		tile += HARBOR
	return tile + DASH + tile_grid


def build_setup_and_video_names(video_name):
	run_setups, video_paths = [], []
	for tile_grid in TILES:
		tile = get_tile_folder_name(video_name, tile_grid)
		for profile in PROFILES:
			run_setups.append(get_run_setup(tile, profile))
			video_paths.append(VIDEOS + SS + video_name + SS + tile + SS + profile)
	return run_setups, video_paths


def iterate_server_logs(server_logs, video_names):
	for server_log, video_name in zip(server_logs, video_names):
		run_setups, video_paths = build_setup_and_video_names(video_name)
		video_files = parse_server_log(server_log, run_setups)
		iterate_video_files(video_files, video_paths, video_name)


def find_video_names(server_logs):
	video_names = []
	for server_log in server_logs:
		video_names.append(UNDERSCORE.join(server_log.split(UNDERSCORE)[2:]).split('.log')[0])
	return video_names


def find_server_log_files():
	server_logs = []
	for root, dirs, files in os.walk(LOGS):
		for file in files:
			if file.find('server_out') != -1:
				server_logs.append(root + SS + file)
	return server_logs


if __name__ == '__main__':
	server_logs = find_server_log_files()
	video_names = find_video_names(server_logs)
	iterate_server_logs(server_logs, video_names)
	print(RESULTS)
