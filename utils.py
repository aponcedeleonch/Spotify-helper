import logging
import json
from random import choices


def open_json_file(file):
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
    logger: logging object
        logger of the script
    file : string
        The path to store the JSON file
    python_dic : dict
        The dictionary to save as JSON
    '''
    logger = logging.getLogger('spotify')
    with open(file, 'w') as f:
        json.dump(python_dic, f, ensure_ascii=False, indent=2)
    logger.info('JSON file written: %s' % (file, ))


def weighted_sample_without_replacement(population, weights, k=1):
    weights = list(weights)
    positions = range(len(population))
    indices = []
    while True:
        needed = k - len(indices)
        if not needed:
            break
        for i in choices(positions, weights, k=needed):
            if weights[i]:
                weights[i] = 0.0
                indices.append(i)
    return [population[i] for i in indices]


def random_all_songs(id_song_list, song_weights, songs_dictionary,
                     repeat_artist=20):
    logger = logging.getLogger('spotify')
    logger.info('Randomizing all songs!')
    # Making sure all weights > 0
    for i in range(len(song_weights)):
        # If the weight is <= 0 give a very small weight but not 0
        if song_weights[i] <= 0:
            song_weights[i] = 1e-5
        assert song_weights[i] > 0

    randomized_ids = []
    # Get a dictionary with the position of every id_song in the list
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
                if artist in recently_played_artists:
                    continue
            # The song and artists are ok
            # Add the artsits to the recently played
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