import os
import time
import datetime
import logging
from logging import handlers
import requests
import base64
import json


def open_json_file(file):
    python_dic = {}
    with open(file, 'r') as f:
        python_dic = json.load(f)

    if python_dic is None:
        raise NameError('The specified file was not found!')

    return python_dic


def write_json_file(file, python_dic):
    with open(file, 'w') as f:
        json.dump(python_dic, f, ensure_ascii=False, indent=2)


def refresh_access_token(spotify_env):
    url = 'https://accounts.spotify.com/api/token'
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': spotify_env['refresh_token']
    }
    encode_credentials = '%s:%s' % (spotify_env['client_id'],
                                    spotify_env['client_secret'])
    encoded_credentials_bytes = base64.b64encode(encode_credentials.encode('ascii'))
    encoded_credentials_message = encoded_credentials_bytes.decode('ascii')

    headers = {
      'Authorization': 'Basic %s' % (encoded_credentials_message, )
    }

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        response_dic = response.json()
        new_access_token = response_dic['access_token']
        spotify_env['access_token'] = new_access_token


def get_list_playlists(logger, spotify_env):
    url = "https://api.spotify.com/v1/users/%s/playlists" % (spotify_env['spotify_user_id'], )

    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }

    playlists = []
    while url is not None:
        response_dic = {}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
        else:
            raise ValueError('Something went wrong with the playlist request!')

        url = response_dic['next']
        playlists += response_dic['items']

    summary_of_playlists = []
    for playlist in playlists:
        playlist_summary = {
            'name': playlist['name'],
            'id': playlist['id'],
            'num_of_tracks': playlist['tracks']['total']
        }
        summary_of_playlists.append(playlist_summary)

    return summary_of_playlists


def get_favorites_playlist(logger, spotify_env):
    url = "https://api.spotify.com/v1/playlists/%s" % (spotify_env['my_favorites_playlist_id'], )

    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }

    counter = 0
    tracks = []
    while url is not None:
        response_dic = {}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
            logger.debug(json.dumps(response_dic, indent=2))
        else:
            raise ValueError('Something went wrong with the playlist request!')

        if counter == 0:
            url = response_dic['tracks']['next']
            request_tracks = response_dic['tracks']['items']
        else:
            url = response_dic['next']
            request_tracks = response_dic['items']
        tracks += request_tracks
        counter += 1


if __name__ == "__main__":
    start_time = time.time()

    # Select data directory
    curr_dir = os.path.dirname(os.path.realpath(__file__))

    # Get a logger of the events
    logfile = os.path.join(curr_dir, 'logs_spotify_fetcher.log')
    numeric_log_level = getattr(logging, "DEBUG", None)
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S %p',
        level=numeric_log_level,
        handlers=[
            # Max store 300MB of logs
            handlers.RotatingFileHandler(logfile,
                                         maxBytes=100e6,
                                         backupCount=3),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()
    logger.info('Logger ready. Logging to file: %s' % (logfile))

    # Creating a directory for the results of the script
    out_dir_path = os.path.join(curr_dir, 'results')
    os.makedirs(out_dir_path, exist_ok=True)
    logger.debug('Created dir for results: %s' % out_dir_path)

    # Starting with the tasks (main loop)
    try:
        env_file = os.path.join(curr_dir, 'spotify_env.json')
        all_playlists_file = os.path.join(out_dir_path, 'all_my_playlists.json')
        spotify_env = open_json_file(env_file)
        refresh_access_token(spotify_env)
        summary_of_playlists = get_list_playlists(logger, spotify_env)
        # get_favorites_playlist(logger, spotify_env)
        write_json_file(all_playlists_file, summary_of_playlists)
        write_json_file(env_file, spotify_env)
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
