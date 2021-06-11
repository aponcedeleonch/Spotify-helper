import logging
import requests
import json
import base64


def security_get_token(spotify_env):
    '''
    Exchanges the user_code authorized by the user by a set of tokens.
    N.B. This request should only be used once!
    The user codes are only valid one time, after that use 'refresh_access_token'
    Reference: https://developer.spotify.com/documentation/general/guides/authorization-guide/

    Parameters
    ----------
    logger: logging object
        logger of the script
    spotify_env : dict
        Dictionary containing own Spotify keys, tokens, etc.
    '''
    # Building the request
    logger = logging.getLogger('spotify')
    logger.info('Getting the token for API')
    url = 'https://accounts.spotify.com/api/token'
    payload = {
        'grant_type': 'authorization_code',
        'code': spotify_env['user_code'],
        'redirect_uri': spotify_env['redirect_uri']
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
        spotify_env['refresh_token'] = response_dic['refresh_token']
        logger.debug(json.dumps(response_dic, indent=1))
        logger.info('Spotify token obtained!')
    else:
        logger.error(response.content)
        raise ValueError('Something went wrong with getting the token!')


def security_refresh_token(spotify_env):
    '''
    Refreshes the current Spotify 'access_token' using the 'refresh_token'
    If it's the first time getting the tokens use 'get_all_tokens'
    Reference: https://developer.spotify.com/documentation/general/guides/authorization-guide/

    Parameters
    ----------
    logger: logging object
        logger of the script
    spotify_env : dict
        Dictionary containing own Spotify keys, tokens, etc.
    '''
    # Building the request
    logger = logging.getLogger('spotify')
    logger.info('Refreshing the API token')
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
    else:
        logger.error(response.content)
        raise ValueError('Something went wrong with refresing the token!')


def get_list_playlists(spotify_env):
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
    logger = logging.getLogger('spotify')
    try:
        # Refresh the access token before doing anything
        security_refresh_token(spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Maybe we havent exchanged the user_code. Try to exchange for tokens
        security_refresh_token(spotify_env)

    # Builds the request
    url = "https://api.spotify.com/v1/users/%s/playlists" % (spotify_env['spotify_user_id'], )
    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }

    # The API does not return the complete list of playlists in one go
    # It keeps returning offsets and the url to the next chunk.
    # At the final offset there's a parameter set to none
    playlists = []
    while url is not None:
        # Sending the request
        logger.debug(('Sending the request..\n'
                      'URL: %s\n'
                      'Headers: %s') % (url,
                                        json.dumps(headers, indent=1)))
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
        else:
            logger.error(response.content)
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
    logger.info('Finished parsing the playlists! Total: %d' % (len(summary_of_playlists, )))

    return summary_of_playlists


def get_saved_tracks(spotify_env):
    '''
    Gets all the saved songs in my library
    Reference: https://developer.spotify.com/documentation/web-api/reference/#category-library

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
    logger = logging.getLogger('spotify')
    logger.info('Getting saved tracks!')

    try:
        # Refresh the access token before doing anything
        security_refresh_token(spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Maybe we havent exchanged the user_code. Try to exchange for tokens
        security_refresh_token(spotify_env)

    # Building the request
    url = "https://api.spotify.com/v1/me/tracks"
    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }

    # The API does not return the complete list of playlists in one go
    # It keeps returning offsets and the url to the next chunk.
    # At the final offset there's a parameter set to none
    tracks = []
    while url is not None:
        # Sending the request
        logger.debug(('Sending the request..\n'
                      'URL: %s\n'
                      'Headers: %s') % (url,
                                        json.dumps(headers, indent=1)))
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
        else:
            logger.error(response.content)
            raise ValueError('Something went wrong with the songs request!')

        # Parses the respone. Get the url for the next chunk
        url = response_dic['next']
        # Append this chunk to what we already have
        tracks += response_dic['items']

    # Only get the data relevant to us
    total_tracks = 0
    summary_of_tracks = {}
    for track in tracks:
        track_summary = {
            'name': track['track']['name'],
            'artists': {artist['id']: artist['name']
                        for artist in track['track']['artists']},
            'album': track['track']['album']['name'],
            'album_id': track['track']['album']['id'],
            'uri': track['track']['uri'],
            'no_of_plays': 0
        }
        track_id = track['track']['id']
        summary_of_tracks[track_id] = track_summary
        total_tracks += 1
    logger.info('Finished getting saved tracks! Total: %d' % (total_tracks, ))

    return summary_of_tracks


def add_song_to_queue(spotify_env, uri_song):
    logger = logging.getLogger('spotify')
    logger.info('Adding song to queue!. URI: %s' % (uri_song, ))

    try:
        # Refresh the access token before doing anything
        security_refresh_token(spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Maybe we havent exchanged the user_code. Try to exchange for tokens
        security_refresh_token(spotify_env)

    # Building the request
    url = "https://api.spotify.com/v1/me/player/queue"
    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['access_token'], )
    }
    payload = {
        'uri': uri_song
    }
    logger.debug(('Sending the request..\n'
                  'URL: %s\n'
                  'Headers: %s\n'
                  'Query params: %s\n') % (url,
                                           json.dumps(headers, indent=1),
                                           json.dumps(payload, indent=1)))
    response = requests.post(url, headers=headers, params=payload)

    if response.status_code != 204:
        logger.error(response.content)
        logger.error('Something went wrong with adding song to the queue!')
        return uri_song

    logger.debug(response.content)
    logger.info('Song added to the queue. URI: %s' % (uri_song, ))


def get_recently_played(spotify_env, number_songs):
    logger = logging.getLogger('spotify')
    logger.info('Checking recently played songs!')

    try:
        # Refresh the access token before doing anything
        security_refresh_token(spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Maybe we havent exchanged the user_code. Try to exchange for tokens
        security_refresh_token(spotify_env)

    if number_songs > 50:
        number_get_songs = 50
    else:
        number_get_songs = number_songs
    # Building the request
    url = "https://api.spotify.com/v1/me/player/recently-played"
    bearer_string = 'Bearer %s' % (spotify_env['access_token'], )
    headers = {
      'Authorization': bearer_string,
      "Content-Type": "application/json",
      "Accept": "application/json"
    }
    payload = {
        'limit': number_get_songs
    }
    logger.debug(('Sending the request..\n'
                  'URL: %s\n'
                  'Headers: %s\n'
                  'Query params: %s') % (url,
                                         json.dumps(headers, indent=1),
                                         json.dumps(payload, indent=1)))
    response = requests.get(url, headers=headers, params=payload)

    if response.status_code != 200:
        logger.error(response.content)
        raise ValueError('Something went wrong getting recently played songs!')

    played_songs = []
    response_dic = response.json()
    played_songs = response_dic['items']
    while len(played_songs) < number_songs and response_dic['next'] is not None:
        logger.debug('Getting more songs. Gotten: %d' % (len(played_songs)))

        url = response_dic['next']
        logger.debug(('Sending the request..\n'
                      'URL: %s\n'
                      'Headers: %s') % (url,
                                        json.dumps(headers, indent=1)))
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_dic = response.json()
        else:
            logger.error(response.content)
            raise ValueError('Something went wrong getting recently played songs!')

        new_songs = response_dic['items']
        logger.debug('New songs gotten: %d' % (len(new_songs), ))
        played_songs += new_songs

    # Only get the data relevant to us
    total_tracks = 0
    summary_of_tracks = {}
    for track in played_songs:
        track_summary = {
            'name': track['track']['name'],
            'artists': ["%s. ID: %s" % (artist['name'], artist['id'])
                        for artist in track['track']['artists']],
            'album': track['track']['album']['name'],
            'album_id': track['track']['album']['id'],
            'uri': track['track']['uri']
        }
        track_id = track['track']['id']
        summary_of_tracks[track_id] = track_summary
        total_tracks += 1
    logger.info('Got %d recently played tracks.' % (total_tracks, ))

    return summary_of_tracks
