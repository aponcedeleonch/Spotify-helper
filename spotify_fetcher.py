import os
import sys
import time
import json
import datetime
import logging
import logging.config
import argparse
import glob
import utils
import spotify_api


def download_saved_songs(all_songs_file, results_dir, spotify_env_file):
    logger = logging.getLogger('spotify')
    logger.info('Downloading saved tracks!')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    # Get all my saved songs
    summary_of_songs = spotify_api.get_saved_tracks(spotify_env)

    # Creating a directory for the results of the script
    os.makedirs(results_dir, exist_ok=True)
    logger.debug('Created dir for results: %s' % results_dir)

    # Write the results for getting all saved songs
    all_saved_songs_file = os.path.join(results_dir, all_songs_file)
    if os.path.isfile(all_saved_songs_file):
        logger.info('File %s exists. Updating!' % (all_saved_songs_file, ))
        all_saved_songs = utils.open_json_file(all_saved_songs_file)
        for old_song_id, old_song_data in all_saved_songs.items():
            if old_song_id in summary_of_songs:
                summary_of_songs[old_song_id]['no_of_plays'] = old_song_data['no_of_plays']
    else:
        logger.info('File %s does not exist. Creating!' % (all_saved_songs_file, ))

    # Updating the last date we downloaded the data
    now_time = datetime.datetime.now()
    spotify_env['saved_songs_updated_at'] = now_time.strftime('%d-%m-%Y')
    
    # Writes the new or updated songs
    utils.write_json_file(all_saved_songs_file, summary_of_songs)

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(spotify_env_file, spotify_env)

    logger.info('Downloaded saved tracks at: %s' % (all_saved_songs_file, ))
    return summary_of_songs


def compare_saved_songs(all_songs_file, results_dir, spotify_env_file):
    logger = logging.getLogger('spotify')
    logger.info('Comparing saved tracks')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    last_saved_songs_path = os.path.join(results_dir, all_songs_file)
    if not os.path.isfile(last_saved_songs_path):
        logger.info('Cannot do diff! There are no past saved songs!')
        return
    last_saved_songs = utils.open_json_file(last_saved_songs_path)

    match_pattern = results_dir + '/diff_songs_*.json'
    diff_songs_path = glob.glob(match_pattern)
    logger.debug('Looking songs with path: %s' % (diff_songs_path, ))

    # Initializing last_saved_time to random old time
    last_saved_time = datetime.datetime(year=1994, month=1, day=1)
    for diff_path in diff_songs_path:
        diff_file = diff_path.split('/')[-1]
        saved_time = datetime.datetime.strptime(diff_file,
                                                'diff_songs_%Y-%m-%d-%H:%M.json')
        logger.debug('Checking date of file: %s' % (diff_path, ))
        if saved_time > last_saved_time:
            last_saved_time = saved_time
    if last_saved_time == datetime.datetime(year=1994, month=1, day=1):
        logger.info('This is the first diff of saved songs.')
    else:
        logger.info('Last diff time: %s' % (last_saved_time, ))

    logger.debug('Checking for new songs!')
    new_saved_songs = download_saved_songs(all_songs_file=all_songs_file,
                                           results_dir=results_dir,
                                           spotify_env_file=spotify_env_file)
    logger.debug('New songs and last saved songs gotten!')

    ids_last_songs = set(last_saved_songs.keys())
    ids_new_songs = set(new_saved_songs.keys())

    # Getting the difference between old songs and new songs
    ids_not_in_new = ids_last_songs - ids_new_songs
    logger.debug('IDs lost: %s' % (ids_not_in_new, ))
    ids_not_in_last = ids_new_songs - ids_last_songs
    logger.debug('New IDs: %s' % (ids_not_in_last, ))

    now_time = datetime.datetime.now()
    diff_dict = {
        'last_checked_time': str(last_saved_time),
        'now_checked_time': str(now_time),
        'diff_songs': {
            'lost_songs': {},
            'new_songs': {}
        }
    }
    for track_id in ids_not_in_new:
        diff_dict['diff_songs']['lost_songs'][track_id] = last_saved_songs[track_id]
        logger.debug('Adding lost song since last diff: %s' % (track_id, ))

    for track_id in ids_not_in_last:
        diff_dict['diff_songs']['new_songs'][track_id] = new_saved_songs[track_id]
        logger.debug('Adding new song since last diff: %s' % (track_id, ))

    diff_songs_file = os.path.join(results_dir,
                                   now_time.strftime('diff_songs_%Y-%m-%d-%H:%M.json'))
    utils.write_json_file(diff_songs_file, diff_dict)
    logger.info('Finished comparing songs file! File written: %s' % (diff_songs_file, ))

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(spotify_env_file, spotify_env)

    return diff_songs_file


def play_saved_songs(all_songs_file, results_dir, spotify_env_file,
                     refresh_time, repeat_artist, num_play_songs, sleep_time,
                     not_wait_songs_to_play):
    logger = logging.getLogger('spotify')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    # Try to get the list of songs in my library
    saved_songs_path = os.path.join(results_dir, all_songs_file)
    # There is no saved songs file, creating one
    if not os.path.isfile(saved_songs_path):
        logger.info('There are no past saved songs! Getting the list.')
        saved_songs = download_saved_songs(all_songs_file=all_songs_file,
                                           results_dir=results_dir,
                                           spotify_env_file=spotify_env_file)
    # Saved songs found
    else:
        logger.debug('Saved songs file exists. Checking update time.')
        saved_songs = utils.open_json_file(saved_songs_path)
        last_update_songs = datetime.datetime.strptime(spotify_env['saved_songs_updated_at'],
                                                       '%d-%m-%Y')
        now_time = datetime.datetime.now()
        check_update_songs = last_update_songs + datetime.timedelta(days=refresh_time)
        # Refreshing list of saved songs
        if now_time > check_update_songs:
            logger.info('Too long since last update of songs. Updating!')
            saved_songs = download_saved_songs(all_songs_file=all_songs_file,
                                               results_dir=results_dir,
                                               spotify_env_file=spotify_env_file)
    logger.info('Saved songs gotten!')

    # Get the ids and weights for each song. To choose with a weight in player
    id_song_list = [id_song for id_song in saved_songs.keys()]
    number_plays = [saved_songs[id_song]['no_of_plays'] for id_song in id_song_list]
    song_weights_unorm = [float(play) for play in number_plays]
    max_weight = max(song_weights_unorm)
    if max_weight == 0:
        # All songs have 0 plays, assigning same weight for all
        song_weights = [1]*len(song_weights_unorm)
    else:
        # Songs with more plays have more weight
        song_weights = [1 - weight/max_weight for weight in song_weights_unorm]

    # Randomize the order of our saved songs and return the random ids
    ids_to_play = utils.random_all_songs(id_song_list=id_song_list,
                                         song_weights=song_weights,
                                         songs_dictionary=saved_songs,
                                         repeat_artist=repeat_artist)

    error_songs = []
    programmed_songs = []
    id_ran = 0
    while len(programmed_songs) < num_play_songs and len(ids_to_play) > id_ran:
        id_song = ids_to_play[id_ran]
        chosen_song = saved_songs[id_song]

        # Try to add the song to the queue
        response = spotify_api.add_song_to_queue(spotify_env,
                                                 chosen_song['uri'])
        # Something went wrong when playing this song, check later
        if response is not None:
            logger.error('Error adding song to the queue:\n%s' % (json.dumps(chosen_song,
                                                                             indent=1), ))
            error_songs.append(id_song)
        else:
            # Make the call of the Spotify API
            logger.info('Adding song to the queue:\n%s' % (json.dumps(chosen_song,
                                                                      indent=1), ))
            programmed_songs.append(id_song)

        id_ran += 1

    if len(programmed_songs) < num_play_songs:
        if len(programmed_songs) == 0:
            logger.error('Script could not program any song :(')
            not_wait_songs_to_play = False
        else:
            logger.warning('Could not program all the songs. Check logs :(')

    # Something went wrong with the API requests of these songs
    if len(error_songs) > 0:
        logger.error('Logging songs with error in the API.')
    for song_id in error_songs:
        logger.error('%s' % (json.dumps(saved_songs[song_id], indent=1)))

    if not_wait_songs_to_play:
        logger.info('Waiting for all the programmed songs to play.')

    sleep_time_seconds = sleep_time*60
    # Try to catch KeyboardInterrupt for exiting the program
    try:
        while not_wait_songs_to_play:
            logger.info('Sleeping for %s minutes.' % (sleep_time, ))
            time.sleep(sleep_time_seconds)

            # Check the recently played songs
            programmed_songs = check_recently_played(
                                    spotify_env_file=spotify_env_file,
                                    programmed_songs=programmed_songs,
                                    saved_songs=saved_songs
                                )

            if len(programmed_songs) == 0:
                logger.info('All programmed songs have played.')
                break
    # Exiting the script
    except KeyboardInterrupt:
        logger.info('Interrupting waiting for songs to play.')
    finally:
        # Try to get all the songs that were played according to Spotify
        programmed_songs = check_recently_played(
                                spotify_env_file=spotify_env_file,
                                programmed_songs=programmed_songs,
                                saved_songs=saved_songs
                            )

        if len(programmed_songs) > 0:
            logger.warning('Some songs were not detected to play.')
        for song_id in programmed_songs:
            logger.warning('%s' % (json.dumps(saved_songs[song_id], indent=1)))

        # Writes the updated songs with the counters before finishing
        utils.write_json_file(saved_songs_path, saved_songs)

        # Writes again the Spotify environment with the new token.
        utils.write_json_file(spotify_env_file, spotify_env)
        logger.info('Finished to write new values to files.')

        logger.info('\n\nNumber of songs sent by the script: %d\n'
                    'Number of not detected played songs: %d\n'
                    'Number of songs with error in API: %d\n' % (num_play_songs,
                                                                 len(programmed_songs),
                                                                 len(error_songs)))
        logger.info('Closing player, bye!')


def check_recently_played(spotify_env_file, programmed_songs, saved_songs):
    logger = logging.getLogger('spotify')
    logger.info('Checking for recently played songs')

    # Temporarily change level to avoid unwanted logging of function
    orig_log_level = logger.getEffectiveLevel()
    logger.setLevel(logging.WARNING)
    recently_played = get_recently_played_songs(spotify_env_file=spotify_env_file,
                                                number_songs=50)
    logger.setLevel(orig_log_level)

    iter_programmed_songs = list(programmed_songs)
    for song_id in iter_programmed_songs:
        if song_id in recently_played:
            logger.info(
                'Detected programmed song that played:\n%s' % (json.dumps(
                                                                saved_songs[song_id],
                                                                indent=1
                                                                ), )
            )
            programmed_songs.remove(song_id)
            saved_songs[song_id]['no_of_plays'] += 1
        else:
            logger.debug(
                'Song still not played:\n%s' % (json.dumps(
                                                    saved_songs[song_id],
                                                    indent=1
                                                ),)
            )

    return programmed_songs


def get_recently_played_songs(spotify_env_file, number_songs=None):
    logger = logging.getLogger('spotify')

    # Maximum number of songs in spotify history
    if number_songs is None:
        number_songs = 50
    logger.info('Getting recently played %d songs' % (number_songs, ))
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    recently_played = spotify_api.get_recently_played(spotify_env=spotify_env,
                                                      number_songs=number_songs)
    logger.info('Recently played songs: %s' % (json.dumps(recently_played,
                                                          indent=1)))

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(spotify_env_file, spotify_env)
    logger.info('Finished to write new values to files.')

    return recently_played


# Parse script arguments
def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--action", "-a", type=str,
                        default="saved_tracks",
                        choices=["download_saved_songs",
                                 'compare_saved_songs',
                                 'play_saved_songs',
                                 'get_recently_played_songs'],
                        help="Choose the action to perform with the script.")

    parser.add_argument("--all_songs_file", "-sf", type=str,
                        default='all_my_songs.json',
                        help="Name of the file to save the saved songs.")

    parser.add_argument("--refresh_time", "-rt", type=int,
                        default=7,
                        help=("Check if the saved songs were downloaded at "
                              "most 'refresh_time' days back."))

    parser.add_argument("--repeat_artist", "-ra", type=int,
                        default=20,
                        help=("Do not repeat an artist when playing saved "
                              "songs in at least 'repeat_artist' songs."))

    parser.add_argument("--num_play_songs", "-ns", type=int,
                        default=100,
                        help=("Play 'num_play_songs' when playing saved "
                              "songs."))

    parser.add_argument('--not_wait_songs_to_play', action='store_false',
                        help=('If set the script will not wait for all '
                              'programmed songs to play.'))

    parser.add_argument("--sleep_time", "-st", type=float,
                        default=5,
                        help=("Sleep for 'sleep_time' minutes while waiting "
                              "for all programmed songs to play."))
    
    parser.add_argument("--results_dir", "-rd", type=str,
                        default='results',
                        help=("Name of the directory to store the results."
                              "The specified dir path is relative to this file."))

    parser.add_argument("--spotify_env_file", "-se", type=str,
                        default='spotify_env.json',
                        help="Path to the file where the keys for Spotify are stored.")

    # Arguments for logging
    parser.add_argument("--log_file", "-lf", type=str,
                        default="logs_spotify_fetcher.log",
                        help="Name of the log file.")

    parser.add_argument("--log_level", "-ll", type=str,
                        default="INFO",
                        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                        help="Set logging level.")

    return parser.parse_args(args)


def spotify_fetcher(action, results_dir, spotify_env_file, refresh_time,
                    log_level, log_file, all_songs_file, repeat_artist,
                    not_wait_songs_to_play, num_play_songs, sleep_time):
    start_time = time.time()

    utils.configure_logger(log_level, log_file)
    logger = logging.getLogger('spotify')
    logger.info('Logger ready. Logging to file: %s' % (log_file))

    dir_path = os.path.dirname(os.path.realpath(__file__))
    results_dir = os.path.join(dir_path, results_dir)
    # Starting with the tasks (main loop)
    try:
        if action == 'download_saved_songs':
            download_saved_songs(all_songs_file=all_songs_file,
                                 results_dir=results_dir,
                                 spotify_env_file=spotify_env_file)
        elif action == 'compare_saved_songs':
            compare_saved_songs(all_songs_file=all_songs_file,
                                results_dir=results_dir,
                                spotify_env_file=spotify_env_file)
        elif action == 'play_saved_songs':
            play_saved_songs(all_songs_file=all_songs_file,
                             results_dir=results_dir,
                             spotify_env_file=spotify_env_file,
                             refresh_time=refresh_time,
                             repeat_artist=repeat_artist,
                             num_play_songs=num_play_songs,
                             sleep_time=sleep_time,
                             not_wait_songs_to_play=not_wait_songs_to_play)
        elif action == 'get_recently_played_songs':
            get_recently_played_songs(spotify_env_file=spotify_env_file)
        else:
            logger.error('The selected option is not available!')
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))


if __name__ == "__main__":
    args = parse_args()
    spotify_fetcher(action=args.action,
                    spotify_env_file=args.spotify_env_file,
                    log_level=args.log_level,
                    log_file=args.log_file,
                    results_dir=args.results_dir,
                    all_songs_file=args.all_songs_file,
                    refresh_time=args.refresh_time,
                    repeat_artist=args.repeat_artist,
                    num_play_songs=args.num_play_songs,
                    sleep_time=args.sleep_time,
                    not_wait_songs_to_play=args.not_wait_songs_to_play)
