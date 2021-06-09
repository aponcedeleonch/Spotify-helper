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


def download_saved_tracks(results_dir, spotify_env_file):
    logger = logging.getLogger('spotify')
    logger.info('Downloading saved tracks!')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    # Get all my saved songs
    summary_of_songs = spotify_api.get_saved_tracks(spotify_env)

    # Creating a directory for the results of the script
    os.makedirs(results_dir, exist_ok=True)
    logger.debug('Created dir for results: %s' % results_dir)

    # Write the results for getting all my playlists
    all_saved_songs_file = os.path.join(results_dir,
                                        spotify_env['all_songs_filename'])
    if os.path.isfile(all_saved_songs_file):
        logger.debug('File %s exists. Updating!' % (all_saved_songs_file, ))
        all_saved_songs = utils.open_json_file(all_saved_songs_file)
        for old_song_id, old_song_data in all_saved_songs.items():
            if old_song_id == "updated_at":
                continue
            if old_song_id in summary_of_songs:
                summary_of_songs[old_song_id]['no_of_plays'] = old_song_data['no_of_plays']
    else:
        logger.debug('File %s does not exist. Creating!' % (all_saved_songs_file, ))

    # Writes the new or updated songs
    utils.write_json_file(all_saved_songs_file, summary_of_songs)

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(spotify_env_file, spotify_env)

    logger.info('Downloaded saved tracks at: %s' % (all_saved_songs_file, ))
    return summary_of_songs


def compare_saved_tracks(results_dir, spotify_env_file):
    logger = logging.getLogger('spotify')
    logger.info('Comparing saved tracks')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    match_pattern = results_dir + '/diff_songs_*.json'
    diff_songs_path = glob.glob(match_pattern)
    logger.debug('Looking songs with path: %s' % (diff_songs_path, ))

    last_saved_songs_path = os.path.join(results_dir,
                                         spotify_env['all_songs_filename'])
    if not os.path.isfile(last_saved_songs_path):
        logger.info('Cannot do diff! There are no past saved songs!')
        return

    last_saved_songs = utils.open_json_file(last_saved_songs_path)

    last_saved_time = datetime.datetime(year=1994, month=1, day=1)
    for diff_path in diff_songs_path:
        diff_file = diff_path.split('/')[-1]
        saved_time = datetime.datetime.strptime(diff_file,
                                                'diff_songs_%Y-%m-%d-%H:%M.json')
        logger.debug('Checking date of file: %s' % (diff_path, ))
        if saved_time > last_saved_time:
            last_saved_time = saved_time

    logger.info('Last diff time: %s' % (last_saved_time, ))

    logger.debug('Checking for new songs!')
    new_saved_songs = download_saved_tracks(logger=logger,
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
        'checked_time': str(now_time),
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


def play_random_saved_songs(results_dir, spotify_env_file,
                            sleep_time_seconds=180, song_limit=300,
                            refresh_time=7, check_recently=40):
    logger = logging.getLogger('spotify')
    # Get my Spotify credentials and variables
    spotify_env = utils.open_json_file(spotify_env_file)

    # Try to get the list of songs in my library
    saved_songs_path = os.path.join(results_dir,
                                    spotify_env['all_songs_filename'])
    # There is no saved songs file, creating one
    if not os.path.isfile(saved_songs_path):
        logger.info('There are no past saved songs! Getting the list.')
        saved_songs = download_saved_tracks(results_dir=results_dir,
                                            spotify_env_file=spotify_env_file)
    # Saved songs found
    else:
        logger.debug('Saved songs file exists. Checking update time.')
        saved_songs = utils.open_json_file(saved_songs_path)
        last_update_songs = datetime.datetime.strptime(saved_songs['updated_at'],
                                                       '%d-%m-%Y')
        now_time = datetime.datetime.now()
        check_update_songs = last_update_songs + datetime.timedelta(days=refresh_time)
        # Refreshing list of saved songs
        if now_time > check_update_songs:
            logger.info('Too long since last update of songs. Updating!')
            saved_songs = download_saved_tracks(logger=logger,
                                                results_dir=results_dir,
                                                spotify_env_file=spotify_env_file)
    logger.info('Saved songs gotten!')

    # Get the ids and weights for each song. To choose with a weight in player
    id_song_list = [id_song for id_song in saved_songs.keys() if id_song != 'updated_at']
    number_plays = [saved_songs[id_song]['no_of_plays'] for id_song in id_song_list]
    song_weights_unorm = [float(play) for play in number_plays]
    max_weight = max(song_weights_unorm)
    if max_weight == 0:
        song_weights = [1]*len(song_weights_unorm)
    else:
        song_weights = [1 - weight/max_weight for weight in song_weights_unorm]

    ids_to_play = utils.random_all_songs(id_song_list, song_weights, saved_songs)

    total_played_songs = {}
    played_songs = []
    error_songs = []
    curr_recently_played = {}
    while True:
        # Try to catch KeyboardInterrupt for exiting the program
        try:
            for id_song in ids_to_play:
                # Get the data of the song with the ID
                chosen_song = saved_songs[id_song]

                # Try to add the song to the queue
                response = spotify_api.add_song_to_queue(spotify_env,
                                                         chosen_song['uri'])

                # Something went wrong when playing this song, check later
                if response is not None:
                    logger.error('Error adding song to the queue:\n%s' % (json.dumps(chosen_song, indent=1), ))
                    error_songs.append(id_song)
                else:
                    # Make the call of the Spotify API
                    logger.debug('Adding song to the queue:\n%s' % (json.dumps(chosen_song, indent=1), ))

                # Sleep for a certain amount of time before choosing new song
                # time.sleep(sleep_time_seconds)

            # If we have played 'check_recently' songs download the list
            # of recently played songs according to Spotify
            # Ideally 'check_recently' < 50 since that is the limit for Spotify
            curr_recently_played = diff_recently_played(logger=logger,
                                                        curr_recently_played=curr_recently_played,
                                                        spotify_env_file=spotify_env_file,
                                                        number_songs=check_recently+5)
        # Exiting the script
        except KeyboardInterrupt:
            logger.info('Interrupting adding songs to the queue!')

            # Something went wrong with the API requests of these songs
            logger.info('Going to log error songs.')
            for song_id in error_songs:
                logger.error('%s' % (json.dumps(saved_songs[song_id], indent=1)))

            # Try to get all the songs that were played according to Spotify
            num_total_played_songs = len(total_played_songs.keys())
            curr_recently_played = diff_recently_played(logger=logger,
                                                        curr_recently_played=curr_recently_played,
                                                        spotify_env_file=spotify_env_file,
                                                        number_songs=num_total_played_songs+5)

            # It maybe the case that our script send the song to play
            # but Spotify did not play it. We can know when this was the case
            # comparing the recently played songs of Spotify
            # and the songs that we sent from the script
            not_played_songs = set(total_played_songs.keys()) - set(curr_recently_played.keys())
            logger.info('Going to log not played songs.')
            for song_id in not_played_songs:
                logger.warning('%s' % (json.dumps(saved_songs[song_id], indent=1)))

            # Song was actually played. Adding one in the dictionary
            for song_id in curr_recently_played:
                try:
                    saved_songs[song_id]['no_of_plays'] += 1
                except KeyError:
                    logger.warning(('Not found key while saving: %s\n'
                                    'Probably from song not in saved songs?') % (song_id, ))

            # Writes the updated songs with the counters before finishing
            utils.write_json_file(saved_songs_path, saved_songs)

            # Writes again the Spotify environment with the new token.
            utils.write_json_file(spotify_env_file, spotify_env)
            logger.info('Finished to write new values to files.')

            logger.info('\n\nNumber of songs sent by the script: %d\n'
                        'Number of not played songs: %d\n'
                        'Number of songs with error in API: %d\n' % (len(total_played_songs.keys()),
                                                                     len(not_played_songs),
                                                                     len(error_songs)))
            logger.info('Closing player, bye!')

            # Breaking the outer while
            break


def diff_recently_played(curr_recently_played, spotify_env_file, number_songs):
    logger = logging.getLogger('spotify')
    logger.info('Getting differences in recently played songs')
    recently_played = get_recently_played_songs(logger=logger,
                                                spotify_env_file=spotify_env_file,
                                                number_songs=number_songs)

    ids_last_recently = set(curr_recently_played.keys())
    ids_new_recently = set(recently_played.keys())

    # Getting the difference between old songs and new songs
    ids_not_in_last = ids_new_recently - ids_last_recently
    logger.debug('New IDs in recently: %s' % (ids_not_in_last, ))

    for song_id in ids_not_in_last:
        curr_recently_played[song_id] = recently_played[song_id]

    logger.info('Retuning dictionary with differences')
    return curr_recently_played


def get_recently_played_songs(spotify_env_file, number_songs,
                              log_level='DEBUG'):
    logger = logging.getLogger('spotify')
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
                        choices=["saved_tracks",
                                 'compare_saved_tracks',
                                 'play_random_saved_songs',
                                 'get_recently_played_songs'],
                        help="Choose the action to perform with the script.")

    parser.add_argument("--results_dir", "-rd", type=str,
                        default='results',
                        help="Name of the directory to store the results.")

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


def configure_logger(log_level, log_file):
    log_config = { 
        'version': 1,
        'formatters': { 
            'standard': { 
                'format': '%(asctime)s %(levelname)s: %(message)s',
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


if __name__ == "__main__":
    start_time = time.time()
    args = parse_args()

    configure_logger(args.log_level, args.log_file)
    logger = logging.getLogger('spotify')
    logger.info('Logger ready. Logging to file: %s' % (args.log_file))

    # Starting with the tasks (main loop)
    try:
        if args.action == 'saved_tracks':
            download_saved_tracks(results_dir=args.results_dir,
                                  spotify_env_file=args.spotify_env_file)
        elif args.action == 'compare_saved_tracks':
            compare_saved_tracks(results_dir=args.results_dir,
                                 spotify_env_file=args.spotify_env_file)
        elif args.action == 'play_random_saved_songs':
            play_random_saved_songs(results_dir=args.results_dir,
                                    spotify_env_file=args.spotify_env_file,
                                    sleep_time_seconds=60)
        elif args.action == 'get_recently_played_songs':
            get_recently_played_songs(spotify_env_file=args.spotify_env_file)
        else:
            logger.error('The selected option is not available!')
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
