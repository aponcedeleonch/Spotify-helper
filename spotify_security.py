import base64
import json
import requests


def get_all_tokens(logger, spotify_env):
    '''
    Exchanges the code authorized by the user by a set of tokens.
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
        raise ValueError('Something went wrong with the getting the token!')


def refresh_access_token(logger, spotify_env):
    '''
    Refreshes the current Spotify 'access_token' using the 'refresh_token'
    If it's the firs time getting the tokens use 'get_all_tokens'
    Reference: https://developer.spotify.com/documentation/general/guides/authorization-guide/

    Parameters
    ----------
    logger: logging object
        logger of the script
    spotify_env : dict
        Dictionary containing own Spotify keys, tokens, etc.
    '''
    # Building the request
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
        raise ValueError('Something went wrong with the refresing the token!')
