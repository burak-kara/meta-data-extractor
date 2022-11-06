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
BOXES = ["ftyp", "styp", "moof", "moov", "mdat", "imda"]

SERVER_LOG = "server_out-15-09-2022-1650.log"


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)


def parse_server_log(file_path, run_setup):
	run_count, files = 0, []
	with open(file_path) as f:
		lines = f.readlines()
		for line in lines:
			if line.find(run_setup) != -1:
				try:
					parsed = line.split()
					if parsed[2].find("mpd") != -1:
						run_count += 1
					file_name = parsed[2].split(SLASH)[3][:-6]
					files.append(file_name)
				except:
					eprint("segment_bytes caused exception", file_path)
					continue
	return run_count, files


def calculate_video_size_with_mp4box(video_path, files):
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

		if file_name.find("mpd") != -1 or file_name.find("base") != -1:
			continue

		if not os.path.isfile(xml_file_path):
			try:
				os.system("mp4box.exe {} -diso".format(file_path))
			except:
				eprint("mp4box.exe caused exception", file_path)
				continue
		input_root = ET.parse(xml_file_path).getroot()

		for box in input_root:
			box_name = box.get('Type')
			if box_name in sizes:
				sizes[box_name] += int(box.get('Size'))
	return sizes


def parse_box_file(file_path, sizes):
	with open(file_path) as f:
		lines = f.readlines()
		for line_id in range(len(lines)):
			if any(box in lines[line_id] for box in BOXES) and lines[line_id].find('-') != -1:
				box_name = lines[line_id].split('-')[-1].strip()
				if box_name in ['ftyp', 'styp']:
					if file_path.find('v1') != 1:
						if box_name == 'styp':
							sizes['styp'] += 40
						elif box_name == 'ftyp':
							sizes['ftyp'] += 28
					elif file_path.find('v2') != 1:
						if box_name == 'styp':
							if file_path.find('index') != -1:
								sizes['styp'] += 20
							else:
								sizes['styp'] += 36
						elif box_name == 'ftyp':
							sizes['ftyp'] += 36
				elif lines[line_id + 1].find('size') != -1:
					size = lines[line_id + 1].split(':')[1].strip()
					sizes[box_name] += int(size)

def calculate_video_size(video_path, files):
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
		output_file_path = video_path + SS + file_name[:-4] + "_info.txt"

		if file_name.find("mpd") != -1:
			continue

		if not os.path.isfile(output_file_path):
			try:
				os.system(
					"python27.exe .\mp4viewer\src\showboxes.py -o stdout -c off {} > {}".format(file_path,
					                                                                            output_file_path))
			except Exception as e:
				eprint(file_path, e)
				continue
		parse_box_file(output_file_path, sizes)
	return sizes


if __name__ == '__main__':
	tile = 'output-harbor-6x4'
	profile = 'case9-omafv2-livezipped'
	# for tile in TILES:
	# 	for profile in PROFILES:
	print("tile: ", tile)
	print("profile: ", profile)
	video_path = VIDEOS + SS + VIDEO_NAME + SS + tile + SS + profile
	output_path = VIDEOS + SS + VIDEO_NAME + SS + tile + SS + profile
	server_log_path = LOGS + SS + SERVER_LOG
	setup = tile + SLASH + profile + SLASH

	# parse_mpd(video_path + SS + MPD_NAMES[profile], MPD_UNIQUE_IDS[tile])
	run_count, files = parse_server_log(server_log_path, setup)
	# video_size_with_mp4box = calculate_video_size_with_mp4box(video_path, files)
	video_size = calculate_video_size(video_path, files)
	# print(run_count, video_size_with_mp4box)
	print(run_count, video_size)
