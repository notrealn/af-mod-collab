from pathlib import Path
import json
import argparse

parser = argparse.ArgumentParser(description='Process a mod project')
parser.add_argument('--output, -o', type=str, nargs='?',
					default='mod_output.json', dest='output_file',
                    help='Set the destination file that the mod will be compiled to')
parser.add_argument('project_directory', metavar='Directory', type=str, nargs='?',
                    default='.', help='Directory that will be processed')
parser.add_argument('--max-projectile-depth', type=int, nargs='?',
                    default=20, dest='max_projectile_depth',
                    help='Sets the maximum depth projectiles will generate ' +
                    'in the case of recursion or sufficiently long projectile chains')
parser.add_argument('--max-parent-depth', type=int, nargs='?',
                    default=50, dest='max_parent_depth',
                    help='Sets the maximum depth parents will be searched to ' +
                    'generate in the case of nested parent chains and infinite loops')
args = parser.parse_args()

def get_jsons(directory):
	if not directory.is_dir():
		return None

	files = []

	for file in directory.iterdir():
		if file.is_dir():
			files += get_jsons(file)
		elif file.suffix == ".json":
			files.append(file)

	return files

def get_data(directory):
	returned_data = {}

	data_files = get_jsons(directory)

	for file in data_files:
		file_text = file.read_text()
		file_json = json.loads(file_text)
		data_name = file.stem
		returned_data[data_name] = file_json.copy()

	return returned_data

def get_constants(directory):
	constant_info = {}

	# AI Javascript
	ai_file = directory.joinpath("ai.js")
	if ai_file.exists() and not ai_file.is_dir():
		constant_info["Code"] = ai_file.read_text()

	# Audio constants
	audio_file = directory.joinpath("audio.json")
	if audio_file.exists() and not audio_file.is_dir():
		constant_info["Audio"] = json.loads(audio_file.read_text())

	# Choices constants
	choices_file = directory.joinpath("choices.json")
	if choices_file.exists() and not choices_file.is_dir():
		constant_info["Choices"] = json.loads(choices_file.read_text())

	# Hero constants
	hero_file = directory.joinpath("hero.json")
	if hero_file.exists() and not hero_file.is_dir():
		constant_info["Hero"] = json.loads(hero_file.read_text())

	# Matchmaking constants
	matchmaking_file = directory.joinpath("matchmaking.json")
	if matchmaking_file.exists() and not matchmaking_file.is_dir():
		constant_info["Matchmaking"] = json.loads(matchmaking_file.read_text())

	# Obstacle constants
	obstacle_file = directory.joinpath("obstacle.json")
	if obstacle_file.exists() and not obstacle_file.is_dir():
		constant_info["Obstacle"] = json.loads(obstacle_file.read_text())

	# Tips list
	tips_file = directory.joinpath("tips.json")
	if tips_file.exists() and not tips_file.is_dir():
		constant_info["Tips"] = json.loads(tips_file.read_text())

	# Visuals constants
	visuals_file = directory.joinpath("visuals.json")
	if visuals_file.exists() and not visuals_file.is_dir():
		constant_info["Visuals"] = json.loads(visuals_file.read_text())

	# World constants
	world_file = directory.joinpath("world.json")
	if world_file.exists() and not world_file.is_dir():
		constant_info["World"] = json.loads(world_file.read_text())

	return constant_info

def get_mod_info(path):
	if path.exists() and not path.is_dir():
		return json.loads(path.read_text())
	return {}

def template_projectile(spell, projectiles):
	returned_spell = spell.copy()

	if type(returned_spell["projectile"]) is str:
		projectile_template = returned_spell["projectile"].replace("ProjectileTemplate:", "")
		returned_spell["projectile"] = projectiles[projectile_template].copy()

	return returned_spell

def template_projectile_spawners(projectile, projectiles, spawner_depth = 0):
	returned_projectile = projectile.copy()
	if not returned_projectile.get("behaviours"):
		return returned_projectile
	popped_items = []
	for behaviour_index, behaviour_data in reversed(list(enumerate(returned_projectile["behaviours"].copy()))):
		if behaviour_data["type"] == "spawn" and type(behaviour_data["projectile"]) is str:
			projectile_template = behaviour_data["projectile"].replace("ProjectileTemplate:", "")
			if spawner_depth >= args.max_projectile_depth:
				popped_items.append(behaviour_index)
				continue
			else:
				returned_projectile["behaviours"][behaviour_index]["projectile"] = template_projectile_spawners(projectiles[projectile_template], projectiles, spawner_depth + 1).copy()

	returned_projectile["behaviours"] = [behaviour.copy() for index, behaviour in enumerate(returned_projectile["behaviours"]) if index not in popped_items]
	return returned_projectile

def process_projectiles(projectiles):
	returned_projectiles = process_parents(projectiles)

	for projectile_index, projectile_data in returned_projectiles.items():
		returned_projectiles[projectile_index] = template_projectile_spawners(projectile_data, returned_projectiles)

	return returned_projectiles

def process_spells(spells, projectiles):
	returned_spells = process_parents(spells)

	for spell_index, spell_data in returned_spells.items():
		if spell_data.get("projectile"):
			returned_spells[spell_index] = template_projectile(spell_data, projectiles)

	return returned_spells

def process_parents(data):
	returned_data = data.copy()

	# Start parenting projectiles
	data_remains = True
	nested_parent_attempts = 0
	while nested_parent_attempts < args.max_parent_depth and data_remains:
		data_remains = False
		for data_index, data in returned_data.items():
			parent_data = data.get("basedOn")
			if parent_data:
				if not returned_data.get(parent_data):
					raise(f"{data['basedOn']} does not exist")
				if returned_data[parent_data].get("basedOn"):
					data_remains = True
					nested_parent_attempts += 1
					continue
				else:
					returned_data[data_index] = dict(returned_data[parent_data].copy(), **data)
					returned_data[data_index].pop("basedOn")
			else:
				returned_data[data_index] = data.copy()

	if nested_parent_attempts == args.max_parent_depth:
		raise("Timed out on parenting data. Infinite loop?")

	return returned_data

def main():
	project_directory = Path(args.project_directory)

	# Process all the mod data
	mod_path = project_directory.joinpath("mod.json")
	constant_path = project_directory.joinpath("constants")
	projectile_path = project_directory.joinpath("projectiles")
	spell_path = project_directory.joinpath("spells")
	obstacle_path = project_directory.joinpath("obstacles")
	map_path = project_directory.joinpath("maps")
	sound_path = project_directory.joinpath("sounds")
	icon_path = project_directory.joinpath("icons")

	mod_info = get_mod_info(mod_path) if mod_path.exists() and not mod_path.is_dir() else {}
	constant_info = get_constants(constant_path) if constant_path.exists() and constant_path.is_dir() else {}

	processed_projectiles = process_projectiles(get_data(projectile_path)) if projectile_path.exists() and projectile_path.is_dir() else {}
	processed_spells = process_spells(get_data(spell_path), processed_projectiles) if spell_path.exists() and spell_path.is_dir() else {}
	processed_obstacles = process_parents(get_data(obstacle_path)) if obstacle_path.exists() and obstacle_path.is_dir() else {}
	processed_maps = process_parents(get_data(map_path)) if map_path.exists() and map_path.is_dir() else {}
	processed_sounds = process_parents(get_data(sound_path)) if sound_path.exists() and sound_path.is_dir() else {}
	processed_icons = process_parents(get_data(icon_path)) if icon_path.exists() and icon_path.is_dir() else {}

	# Format the mod data into a json
	mod_data = {}
	mod_data["Mod"] = mod_info
	for constant_index, constant_values in constant_info.items():
		mod_data[constant_index] = constant_values
	mod_data["Spells"] = processed_spells
	mod_data["Layouts"] = processed_maps
	mod_data["ObstacleTemplates"] = processed_obstacles
	mod_data["Sounds"] = processed_sounds
	mod_data["Icons"] = processed_icons

	# Export the mod data to the specified file
	mod_file = Path(args.output_file)
	mod_json = json.dumps(mod_data, indent=4)
	mod_file.write_text(str(mod_json))

main()