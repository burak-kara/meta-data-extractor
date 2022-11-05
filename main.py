import sys
import os
import subprocess
import xml.etree.ElementTree as ET

SS = "\\"
SLASH = "/"
NEW_LINE = "\n"
VIDEOS = "videos"
LOGS = "logs"
VIDEO_NAME = "3secs_harbor"
TILES = ["output-harbor-6x4", "output-harbor-8x6", "output-harbor-12x8"]
# TILES = ["output-timelapse-6x4", "output-timelapse-8x6", "output-timelapse-12x8"]
MPD_UNIQUE_IDS = [217, 433, 865]  # depending on the tile grid
PROFILES = ["case9-omafv1-live", "case9-omafv2-live", "case9-omafv2-livezipped"]
MPD_NAMES = ["omafv1.mpd", "omafv2.mpd", "omafv2.mpd"]

SERVER_LOG = "server_out-15-09-2022-1650.log"


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)


def parse_mpd(file_path, unique_id):
	input_root = ET.parse(file_path).getroot()

	# keep all adaptation sets
	adaptation_sets = list(input_root[0])

	# empty dict to keep AdaptationSet's id as key and Representation(s) inside that AdaptationSet as value
	representations_dict = dict()

	for adaptation in adaptation_sets:
		adaptation_id = adaptation.get('id')
		print(adaptation_id)
		representations = list(adaptation.findall('{urn:mpeg:dash:schema:mpd:2011}Representation'))

		if int(adaptation_id) != unique_id:
			representations_dict[adaptation_id] = representations
		elif int(adaptation_id) == unique_id:
			flag = False


def parse_server_log(file_path, run_setup):
	run_count = 0
	files = []
	with open(file_path) as f:
		lines = f.readlines()
		for line in lines:
			if line.find(run_setup) != -1:
				try:
					parsed = line.split()
					if parsed[2].find("mpd") != -1:
						run_count += 1
					file_name = parsed[2].split(SLASH)[3]
					file_name = file_name[:-6]  # remove trash bytes from file_name
					files.append(file_name)
				except:
					eprint("segment_bytes caused exception", file_path)
					continue
	return run_count, files


def calculate_video_size(video_path, output_path, files):
	sizes = {
		"ftyp": 0,
		"styp": 0,
		"moof": 0,
		"moov": 0,
		"mdat": 0,
		"imda": 0,
	}
	for file_name in files:
		file_path = video_path + SS + file_name
		xml_file_path = video_path + SS + file_name[:-4] + "_info.xml"

		if file_name.find("mpd") != -1 or file_name.find("base.init") != -1:
			continue

		if not os.path.isfile(xml_file_path):
			os.system("mp4box.exe {} -diso".format(file_path))
		input_root = ET.parse(xml_file_path).getroot()

		for box in input_root:
			box_name = box.get('Type')
			if box_name in sizes:
				sizes[box_name] += int(box.get('Size'))
	print(sizes)


def collect_downloaded_segments(file_name):
	representations = dict()
	with open(LOGS + SS + file_name) as f:
		file_name = file_name.split(".")[0]
		lines = f.readlines()
		for line in lines:
			if line.find("DOWNLOAD(Time/Repr/SegmentID/Bytes/DownloadTime/cached") != -1:
				try:
					split = line.split()
					representation = split[3]
					segment_id = split[4]
					if representation in representations:
						representations[representation].append(segment_id)
					else:
						representations[representation] = [segment_id]
				except:
					eprint("segment_bytes caused exception", file_name)
					continue
	return representations


if __name__ == '__main__':
	tile = 0
	profile = 0

	video_path = VIDEOS + SS + VIDEO_NAME + SS + TILES[tile] + SS + PROFILES[profile]
	output_path = VIDEOS + SS + VIDEO_NAME + SS + TILES[tile] + SS + PROFILES[profile]
	server_log_path = LOGS + SS + SERVER_LOG
	setup = TILES[tile] + SLASH + PROFILES[profile]

	# parse_mpd(video_path + SS + MPD_NAMES[profile], MPD_UNIQUE_IDS[tile])
	run_count, files = parse_server_log(server_log_path, setup)
	video_size = calculate_video_size(video_path, output_path, files)
