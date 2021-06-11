import logging
import json
from random import choices


def open_json_file(file):
    '''
    Parse a JSON file and return a python dictionary

    Parameters
    ----------
    file : string
        The path to the JSON file

    Returns
    -------
    dict
        The parsed JSON content into a python dictionary
    '''
    logger = logging.getLogger('spotify')
    python_dic = {}
    with open(file, 'r') as f:
        python_dic = json.load(f)
    logger.info('Parsed JSON file: %s' % (file, ))

    if python_dic is None:
        raise NameError('The specified file was not found!')

    return python_dic


def write_json_file(file, python_dic):
    '''
    Write a JSON file with a python dictionary

    Parameters
    ----------
    file : string
        The path to store the JSON file
    python_dic : dict
        The dictionary to save as JSON
    '''
    logger = logging.getLogger('spotify')
    with open(file, 'w') as f:
        json.dump(python_dic, f, ensure_ascii=False, indent=2)
    logger.info('JSON file written: %s' % (file, ))


def random_all_songs(songs_dictionary, repeat_artist):
    '''
    Receives a dictionary of songs ('songs_dictionary')  and returns a list of
    songs randomized (ids of the songs).
    The randomization is done using the function random.choices.

    The function random.choices picks with replacement an element
    from a list with a proability 'p'. In our case we are picking
    from the ids of the songs and the probabilities are the number of
    plays that song has. The more plays/reproductions the less probable is
    for that song to be picked first.

    We also take into account the frequency in which the artists of the songs
    play. In this case an artist cannot be repeated in the last 'repeat_artist'
    songs.
    
    Parameters
    ----------
    songs_dictionary : dict
        A dictionary containing the songs that we want to randomize.
        The keys of this dictionary are the ids of the songs.

        The dictionary needs to be constrcuted using fucntion
        spotify_helper/download_saved_songs

    repeat_artist : int
        Interval of songs in which an artist cannto be repeated.

    Returns
    -------
    list
        Randomized ids of the songs. The list is constructed so the songs
        at the beginning of the list are played first.
    '''
    logger = logging.getLogger('spotify')

    # Get the ids and weights for each song
    id_song_list = list(songs_dictionary.keys())
    number_plays = [songs_dictionary[id_song]['no_of_plays']
                    for id_song in id_song_list]
    song_weights_unorm = [float(play) for play in number_plays]
    max_weight = max(song_weights_unorm)
    if max_weight == 0:
        # All songs have 0 plays, assigning same weight for all
        song_weights = [1]*len(song_weights_unorm)
    else:
        # Songs with more plays have more weight
        song_weights = [1 - weight/max_weight for weight in song_weights_unorm]

    logger.info('Randomizing all songs!')
    # Making sure all weights > 0
    for i in range(len(song_weights)):
        # If the weight is <= 0 give a very small weight but not 0
        if song_weights[i] <= 0:
            song_weights[i] = 1e-5
        assert song_weights[i] > 0

    randomized_ids = []
    # Get a dictionary with the position of every id_song in the list
    # This is done as a hasing dictionary to then access quickly to position
    positions = {id_song: i for i, id_song in enumerate(id_song_list)}

    recently_played_artists = []
    # Until we have picked all the available songs
    while len(randomized_ids) != len(id_song_list):
        # Choose one song
        chosen_id = choices(id_song_list, song_weights, k=1)[0]
        # Make sure that song hasn't been picked before
        if chosen_id not in randomized_ids:
            # Get the artists of the song
            chosen_artists = list(songs_dictionary[chosen_id]['artists'].keys())

            # Make sure the artists are not in the recently played artists
            for artist in chosen_artists:
                # If they are continue and choose another song
                if artist in recently_played_artists:
                    continue

            # The song and artists are ok. Add the artsits to recently played
            recently_played_artists += chosen_artists

            # Shorten the recently played artist list.
            # Only check the last repeat_artist
            recently_played_artists = recently_played_artists[-repeat_artist:]

            # Add the id to the list of ids
            randomized_ids.append(chosen_id)

            # Set the weight to zero so in the next iteration is not picked
            song_weights[positions[chosen_id]] = 0

    logger.info('Finished randomization, returning randomized songs!')
    return randomized_ids


def configure_logger(log_level, log_file):
    '''
    Configures a logger with the name 'spotify'.
    The logger is going to log to console and to a file.

    Parameters
    ----------
    log_level : string
        The level in whcih the logger is going to be configured
    log_file : string
        Name of the file to log
    '''
    str_format = '%(asctime)s %(filename)17s %(funcName)22s %(levelname)7s: %(message)s'
    log_config = { 
        'version': 1,
        'formatters': { 
            'standard': { 
                'format': str_format,
                'datefmt': '%m/%d/%Y %H:%M:%S'
            },
        },
        'handlers': { 
            'console': { 
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'file': {
                'formatter': 'standard',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'maxBytes': 100e6,
                'backupCount': 3
            }
        },
        'loggers': { 
            'spotify': { 
                'handlers': ['console', 'file'],
                'level': log_level
            }
        } 
    }
    logging.config.dictConfig(log_config)
