import requests
import json


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

    # The API does not return the complete list of playlists in one go
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


def get_saved_tracks(logger, spotify_env):
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
    # Building the request
    logger.info('Get saved tracks!')
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
                      'URL: %s'
                      'Headers: %s\n') % (url,
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
        playlist_summary = {
            'name': track['track']['name'],
            'artist': ["%s. ID: %s" % (artist['name'], artist['id'])
                       for artist in track['track']['artists']],
            'album': track['track']['album']['name'],
            'album_id': track['track']['album']['id']
        }
        track_id = track['track']['id']
        summary_of_tracks[track_id] = playlist_summary
        total_tracks += 1
    logger.info('Finished getting the saved tracks! Total: %d' % (total_tracks, ))

    return summary_of_tracks
