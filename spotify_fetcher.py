import os
import sys
import random
import time
import json
import datetime
import logging
from logging import handlers
import argparse
import glob
import utils
import spotify_security
import spotify_api


def download_saved_tracks(logger, curr_dir, results_dir, spotify_env_file):
    logger.info('Downloading saved tracks!')
    # Get my Spotify credentials and variables
    env_file = os.path.join(curr_dir, spotify_env_file)
    spotify_env = utils.open_json_file(logger, env_file)

    try:
        # Refresh the access token before doing anything
        spotify_security.refresh_access_token(logger, spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Maybe we havent exchanged the user_code. Try to exchange for tokens
        spotify_security.get_all_tokens(logger, spotify_env)

    # Get all my saved songs
    summary_of_songs = spotify_api.get_saved_tracks(logger, spotify_env)

    # Creating a directory for the results of the script
    out_dir_path = os.path.join(curr_dir, results_dir)
    os.makedirs(out_dir_path, exist_ok=True)
    logger.debug('Created dir for results: %s' % out_dir_path)

    # Write the results for getting all my playlists
    all_saved_songs_file = os.path.join(out_dir_path,
                                        spotify_env['all_songs_filename'])
    if os.path.isfile(all_saved_songs_file):
        logger.debug('File %s exists. Updating!' % (all_saved_songs_file, ))
        all_saved_songs = utils.open_json_file(logger, all_saved_songs_file)
        for old_song_id, old_song_data in all_saved_songs.items():
            if old_song_id in summary_of_songs:
                summary_of_songs[old_song_id]['no_of_plays'] = old_song_data['no_of_plays']
    else:
        logger.debug('File %s does not exist. Creating!' % (all_saved_songs_file, ))

    # Writes the new or updated songs
    utils.write_json_file(logger, all_saved_songs_file, summary_of_songs)

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(logger, env_file, spotify_env)

    return summary_of_songs


def compare_saved_tracks(logger, curr_dir, results_dir, spotify_env_file):
    logger.info('Comparing saved tracks')
    # Get my Spotify credentials and variables
    env_file = os.path.join(curr_dir, spotify_env_file)
    spotify_env = utils.open_json_file(logger, env_file)

    results_dir_path = os.path.join(curr_dir, results_dir)
    match_pattern = results_dir_path + '/diff_songs_*.json'
    diff_songs_path = glob.glob(match_pattern)
    logger.debug('Looking songs with path: %s' % (diff_songs_path, ))

    last_saved_songs_path = os.path.join(results_dir,
                                         spotify_env['all_songs_filename'])
    if not os.path.isfile(last_saved_songs_path):
        logger.info('Cannot do diff! There are no past saved songs!')
        return
    last_saved_songs = utils.open_json_file(logger, last_saved_songs_path)

    last_saved_time = datetime.datetime(year=1994, month=1, day=1)
    for diff_path in diff_songs_path:
        diff_file = diff_path.split('/')[-1]
        saved_time = datetime.datetime.strptime(diff_file,
                                                'diff_songs_%Y-%m-%d-%H:%M.json')
        logger.debug('Checking date of file: %s' % (diff_path, ))
        if saved_time > last_saved_time:
            last_saved_time = saved_time

    logger.info('Last diff time: %s' % (last_saved_time, ))
    check_time = last_saved_time + datetime.timedelta(days=7)
    # check_time = last_saved_time + datetime.timedelta(minutes=5)
    # check_time = last_saved_time + datetime.timedelta(seconds=1)
    now_time = datetime.datetime.now()

    if now_time > check_time:
        logger.info('Checking for new songs!')
        new_saved_songs = download_saved_tracks(logger=logger,
                                                curr_dir=curr_dir,
                                                results_dir=results_dir,
                                                spotify_env_file=spotify_env_file)
    else:
        logger.info('Still not time to check for new songs!')
        return None

    logger.debug('New songs and last saved songs gotten!')

    ids_last_songs = set(last_saved_songs.keys())
    ids_new_songs = set(new_saved_songs.keys())

    # Getting the difference between old songs and new songs
    ids_not_in_new = ids_last_songs - ids_new_songs
    logger.debug('IDs lost: %s' % (ids_not_in_new, ))
    ids_not_in_last = ids_new_songs - ids_last_songs
    logger.debug('New IDs: %s' % (ids_not_in_last, ))
    if len(ids_not_in_new) == 0 and len(ids_not_in_last) == 0:
        logger.info('No difference in saved songs! Not writing diff file')
        return None

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

    diff_songs_file = os.path.join(results_dir_path,
                                   now_time.strftime('diff_songs_%Y-%m-%d-%H:%M.json'))
    utils.write_json_file(logger, diff_songs_file, diff_dict)
    logger.info('Finished comparing songs file! File written: %s' % (diff_songs_file, ))

    return diff_songs_file


def get_ids_and_weights(saved_songs):
    # Ensure number of plays are in the same order as ids
    id_song_list = [id_song for id_song in saved_songs.keys() if id_song != 'updated_at']
    number_plays = [saved_songs[id_song]['no_of_plays'] for id_song in id_song_list]
    song_weights_unorm = [float(play) for play in number_plays]
    max_weight = max(song_weights_unorm)
    song_weights = [1 - weight/max_weight for weight in song_weights_unorm]

    return id_song_list, song_weights


def play_random_saved_songs(logger, curr_dir, results_dir, spotify_env_file,
                            sleep_time_seconds=60, song_limit=100):
    # Get my Spotify credentials and variables
    env_file = os.path.join(curr_dir, spotify_env_file)
    spotify_env = utils.open_json_file(logger, env_file)

    saved_songs_path = os.path.join(results_dir,
                                    spotify_env['all_songs_filename'])
    if not os.path.isfile(saved_songs_path):
        logger.debug('There are no past saved songs! Getting the list.')
        saved_songs = download_saved_tracks(logger=logger,
                                            curr_dir=curr_dir,
                                            results_dir=results_dir,
                                            spotify_env_file=spotify_env_file)
    else:
        logger.debug('Saved songs file exists. Checking update time.')
        saved_songs = utils.open_json_file(logger, saved_songs_path)
        last_update_songs = datetime.datetime.strptime(saved_songs['updated_at'],
                                                       '%d-%m-%Y')
        now_time = datetime.datetime.now()
        check_update_songs = last_update_songs + datetime.timedelta(days=7)
        if now_time > check_update_songs:
            logger.debug('Too long since last update of songs. Updating!')
            saved_songs = download_saved_tracks(logger=logger,
                                                curr_dir=curr_dir,
                                                results_dir=results_dir,
                                                spotify_env_file=spotify_env_file)
    logger.info('Saved songs gotten!')

    id_song_list, song_weights = get_ids_and_weights(saved_songs)
    played_songs = []
    not_played_songs = []
    while True:
        try:
            # Getting a song that hasnt been played recently
            while True:
                chosen_id_song = random.choices(id_song_list, weights=song_weights, k=1)[0]
                if chosen_id_song not in played_songs:
                    break
                else:
                    # Sleep to try to reset the random of python
                    time.sleep(1)
            # Get the data of the song with the ID
            chosen_song = saved_songs[chosen_id_song]
            # Make the call of the Spotify API
            logger.info('Adding song to the queue:\n%s' % (json.dumps(chosen_song, indent=1), ))

            try:
                # Refresh the access token before doing anything
                spotify_security.refresh_access_token(logger, spotify_env)
            except ValueError:
                logger.info('Could not refresh access token. Try to get new one')
                # Maybe we havent exchanged the user_code. Try to exchange for tokens
                spotify_security.get_all_tokens(logger, spotify_env)
            # Try to add the song to the queue
            response = spotify_api.add_song_to_queue(logger,
                                                     spotify_env,
                                                     chosen_song['uri'])

            # Something went wrong when playing this song, check later
            if response is not None:
                not_played_songs.append(chosen_id_song)
                continue

            played_songs.append(chosen_id_song)
            # Keep only the last song_limit songs
            played_songs = played_songs[-song_limit:]
            # Add the counter to the song that was just played
            saved_songs[chosen_id_song]['no_of_plays'] += 1

            # Recalculate the weights of the songs
            id_song_list, song_weights = get_ids_and_weights(saved_songs)

            # Sleep for a certain amount of time before choosing new song
            time.sleep(sleep_time_seconds)
        except KeyboardInterrupt:
            logger.info('Interrupting adding songs to the queue!')
            # Writes the updated songs with the counters before finishing
            utils.write_json_file(logger, saved_songs_path, saved_songs)
            # Writes again the Spotify environment with the new token.
            utils.write_json_file(logger, env_file, spotify_env)
            logger.info('Finished to write new values to files.')

            logger.info('Going to log last played songs.')
            for song_id in played_songs:
                logger.info('%s' % (json.dumps(saved_songs[song_id], indent=1)))

            logger.info('Going to log not played songs.')
            for song_id in not_played_songs:
                logger.warn('%s' % (json.dumps(saved_songs[song_id], indent=1)))
            logger.info('Closing, bye!')
            break


# Parse script arguments
def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--action", "-a", type=str,
                        default="saved_tracks",
                        choices=["saved_tracks",
                                 'compare_saved_tracks',
                                 'play_random_saved_songs'],
                        help="Choose the action to perform with the script.")

    parser.add_argument("--results_dir", "-rd", type=str,
                        default='results',
                        help="Name of the directory to store the results.")

    parser.add_argument("--spotify_env_file", "-se", type=str,
                        default='spotify_env.json',
                        help="Name of the file where the keys of Spotify are stored.")

    # Arguments for logging
    parser.add_argument("--logfile", "-lf", type=str,
                        default="logs_spotify_fetcher.log",
                        help="Name of the log file of the main process.")

    parser.add_argument("--loglevel", "-ll", type=str,
                        default="DEBUG",
                        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                        help="Set logging level.")

    return parser.parse_args(args)


if __name__ == "__main__":
    start_time = time.time()
    args = parse_args()

    # Select data directory
    curr_dir = os.path.dirname(os.path.realpath(__file__))

    # Get a logger of the events
    logfile = os.path.join(curr_dir, args.logfile)
    numeric_log_level = getattr(logging, args.loglevel, None)
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
        if args.action == 'saved_tracks':
            download_saved_tracks(logger=logger,
                                  curr_dir=curr_dir,
                                  results_dir=args.results_dir,
                                  spotify_env_file=args.spotify_env_file)
        elif args.action == 'compare_saved_tracks':
            compare_saved_tracks(logger=logger,
                                 curr_dir=curr_dir,
                                 results_dir=args.results_dir,
                                 spotify_env_file=args.spotify_env_file)
        elif args.action == 'play_random_saved_songs':
            play_random_saved_songs(logger=logger,
                                    curr_dir=curr_dir,
                                    results_dir=args.results_dir,
                                    spotify_env_file=args.spotify_env_file,
                                    sleep_time_seconds=60)
        else:
            logger.error('The selected option is not available!')
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
