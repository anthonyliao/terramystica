import logging
import json
import requests
import time

logging.basicConfig(level=logging.INFO)

def main():
	logging.info('terramonitor starting')

	sleep_time_secs = 5

	previous_game = None
	previous_player = None
	previous_move_time = None
	previous_notified_over = False

	while True:

		logging.info('sleeping for %d secs', sleep_time_secs)
		time.sleep(sleep_time_secs)

		with open('terramonitor.json') as f:
			monitor_state_raw = f.read()

		monitor_state_json = json.loads(monitor_state_raw)
		logging.info('monitor_state: %s', monitor_state_raw)
		
		url = monitor_state_json['url']
		chatid = monitor_state_json['chatid']
		game_name = monitor_state_json['game_name']
		if previous_game != game_name:
			logging.info('monitoring new game: %s', game_name)
			previous_game = game_name
			previous_player = None
			previous_move_time = None
			previous_notified_over = False

		game_url = 'https://terra.snellman.net/app/view-game/'
		game_payload = {'game': game_name}
		r = requests.get(game_url, params=game_payload)
		logging.info('monitoring game: %s at %s', game_name, r.url)
		logging.debug('game response: %s', r.text)

		game_json = json.loads(r.text)
		error = game_json['error']
		if len(error) != 0:
			logging.error('unable to monitor, error: %s', error[0])
			continue

		if game_json['metadata']['aborted'] != 0:
			if not previous_notified_over:
				notify_game_over(url, chatid, game_name)
				previous_notified_over = True

			logging.info('game aborted')
			continue

		if game_json['metadata']['finished'] != 0:
			if not previous_notified_over:
				notify_game_over(url, chatid, game_name)
				previous_notified_over = True

			logging.info('game finished')
			continue

		action_required = game_json['action_required']
		logging.info('action_required: %s', action_required)

		if len(action_required) == 0:
			logging.error('no action required but game not aborted or finished')
			continue

		faction = action_required[0]['faction']
		player = None
		if faction is not None:
			player = get_player_name(game_json, faction)

		for item in action_required:
			if item['type'] == 'full':
				player = get_player_name(game_json, item['faction'])
				logging.debug('waiting for %s to make full move', player)
				break

			elif item['type'] == 'faction':
				player = item['player']
				logging.debug('waiting for %s to pick a faction', player)
				break

		if previous_player != player:
			logging.info('player %s is new mover', player)
			move_time = time.time()
			move_time_diff = None
			if previous_move_time is not None:
				move_time_diff = move_time - previous_move_time

			notify_to_move(url, chatid, game_name, player, previous_player, move_time_diff)
			previous_player = player
			previous_move_time = move_time

		else:
			logging.info('still waiting for player %s to move', player)


	logging.info('terramonitor ending')

def get_player_name(game_json, faction):
	factions = game_json['factions']
	if faction in factions:
		username = factions[faction]['username']
	else:
		username = None
	return username

def notify_to_move(url, chatid, game_name, player, previous_player, move_time_diff):
	headers = {'content-type': 'application/json'}
	if previous_player is None:
		payload = {
    		'echo': 'game: <b>{}</b><br/>next turn: <b>{}</b>'.format(game_name, player)
		}
	else:
		payload = {
    		'echo': 'game: <b>{}</b><br/><b>{}</b> took {:.2f} mins to move<br/>next turn: <b>{}</b>'.format(game_name, previous_player, move_time_diff/60, player)
		}

	r = requests.post(url + chatid, data = json.dumps(payload), headers = headers, verify=False)
	logging.info('request: %s, %s, %s, %s', r, r.url, r.text, payload)

def notify_game_over(url, chatid, game_name):
	headers = {'content-type': 'application/json'}
	payload = {
    	'echo': 'game, <b>{}</b>, finished'.format(game_name)
	}
	r = requests.post(url + chatid, data = json.dumps(payload), headers = headers, verify=False)
	logging.info('request: %s, %s, %s, %s', r, r.url, r.text, payload)

if __name__ == '__main__':
	logging.info('__name__: %s', __name__)
	main()