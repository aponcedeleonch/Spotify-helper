import os
import time
import datetime
import logging
from logging import handlers
import requests
import base64
import json


def open_json_file(logger, file):
    '''
    Parse a JSON file and return a python dictionary

    Parameters
    ----------
    logger: logging object
        logger of the script
    file : string
        The path to the JSON file

    Returns
    -------
    dict
        The parsed JSON content into a python dictionary
    '''
    python_dic = {}
    with open(file, 'r') as f:
        python_dic = json.load(f)
    logger.info('Parsed JSON file: %s' % (file, ))

    if python_dic is None:
        raise NameError('The specified file was not found!')

    return python_dic


def write_json_file(logger, file, python_dic):
    '''
    Write a JSON file with a python dictionary

    Parameters
    ----------
    logger: logging object
        logger of the script
    file : string
        The path to store the JSON file
    python_dic : dict
        The dictionary to save as JSON
    '''
    with open(file, 'w') as f:
        json.dump(python_dic, f, ensure_ascii=False, indent=2)
    logger.info('JSON file written: %s' % (file, ))


def refresh_access_token(logger, spotify_env):
    '''
    Refreshes the current Spotify 'access_token' using the 'refresh_token'
    I sitll have not yet seen if the 'refresh_token' fails.
    Reference: https://developer.spotify.com/documentation/general/guides/authorization-guide/

    Parameters
    ----------
    logger: logging object
        logger of the script
    spotify_env : dict
        Dictionary containing own Spotify keys, tokens, etc.
    '''
    # Building the request
    url = 'https://accounts.spotify.com/api/token'
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': spotify_env['refresh_token']
    }
    # Getting my own credentials encoded into Base64
    encode_credentials = '%s:%s' % (spotify_env['client_id'],
                                    spotify_env['client_secret'])
    encoded_credentials_bytes = base64.b64encode(encode_credentials.encode('ascii'))
    encoded_credentials_message = encoded_credentials_bytes.decode('ascii')

    headers = {
      'Authorization': 'Basic %s' % (encoded_credentials_message, )
    }

    # Sending the request
    logger.debug(('Sending the request..\n'
                  'URL: %s'
                  'Headers: %s\n'
                  'Payload: %s\n') % (url,
                                      json.dumps(headers, indent=1),
                                      json.dumps(payload, indent=1)))
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        response_dic = response.json()
        # Renewing the 'access_token'
        # Using the fact that the dictionaries are immutable
        # we don't return anything
        spotify_env['access_token'] = response_dic['access_token']
        logger.info('Spotify token renewed!')


def get_list_playlists(logger, spotify_env):
    '''
    Gets all my created playlists and returns only the relevant information
    Reference: https://developer.spotify.com/documentation/web-api/reference/#category-playlists

    Parameters
    ----------
    logger: logging object
        logger of the script
    spotify_env : dict
        Dictionary containing own Spotify keys, tokens, etc.

    Returns
    -------
    list of dicts
        The parsed response from the API with the relevant information
    '''
    # Builds the request
    url = "https://api.spotify.com/v1/users/%s/playlists" % (spotify_env['spotify_user_id'], )
    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }

    # The API does not return the complet list of playlists in one go
    # It keeps returning offsets and the url to the next chunk.
    # At the final offset there's a parameter set to none
    playlists = []
    while url is not None:
        # Sending the request
        logger.debug(('Sending the request..\n'
                      'URL: %s'
                      'Headers: %s\n') % (url,
                                          json.dumps(headers, indent=1)))
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
        else:
            raise ValueError('Something went wrong with the playlist request!')

        # Parses the respone. Get the url for the next chunk
        url = response_dic['next']
        # Append this chunk to what we already have
        playlists += response_dic['items']
    logger.info('Finished querying for playlists!. Total: %d' % (len(playlists), ))

    # Only get the data relevant to us
    summary_of_playlists = []
    for playlist in playlists:
        playlist_summary = {
            'name': playlist['name'],
            'id': playlist['id'],
            'num_of_tracks': playlist['tracks']['total']
        }
        summary_of_playlists.append(playlist_summary)
    logger.info('Finished parsing the playlists!')

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

    # Starting with the tasks (main loop)
    try:
        # Creating a directory for the results of the script
        out_dir_path = os.path.join(curr_dir, 'results')
        os.makedirs(out_dir_path, exist_ok=True)
        logger.debug('Created dir for results: %s' % out_dir_path)

        # Get my Spotify credentials and variables
        env_file = os.path.join(curr_dir, 'spotify_env.json')
        spotify_env = open_json_file(logger, env_file)

        # Refresh the access token before doing anything
        refresh_access_token(logger, spotify_env)

        # Get all my playlists
        # summary_of_playlists = get_list_playlists(logger, spotify_env)

        # Get my saved songs
        get_favorites_playlist(logger, spotify_env)

        # Write the results for getting all my playlists
        # all_playlists_file = os.path.join(out_dir_path, 'all_my_playlists.json')
        # write_json_file(logger, all_playlists_file, summary_of_playlists)

        # Writes again the Spotify environment with the new token.
        write_json_file(logger, env_file, spotify_env)
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
