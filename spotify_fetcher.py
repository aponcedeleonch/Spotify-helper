import os
import sys
import time
import datetime
import logging
from logging import handlers
import argparse
import glob
import utils
import spotify_security
import spotify_api


def download_saved_tracks(logger, curr_dir, results_dir, spotify_env_file):
    # Get my Spotify credentials and variables
    env_file = os.path.join(curr_dir, spotify_env_file)
    spotify_env = utils.open_json_file(logger, env_file)

    try:
        # Refresh the access token before doing anything
        spotify_security.refresh_access_token(logger, spotify_env)
    except ValueError:
        logger.info('Could not refresh access token. Try to get new one')
        # Get all the required tokens
        spotify_security.get_all_tokens(logger, spotify_env)

    # Get all my saved songs
    summary_of_songs = spotify_api.get_saved_tracks(logger, spotify_env)

    # Creating a directory for the results of the script
    out_dir_path = os.path.join(curr_dir, results_dir)
    os.makedirs(out_dir_path, exist_ok=True)
    logger.debug('Created dir for results: %s' % out_dir_path)

    # Get the current date
    now_time = datetime.datetime.now()

    # Write the results for getting all my playlists
    all_saved_songs_file = os.path.join(out_dir_path,
                                        now_time.strftime('all_my_songs_%Y-%m-%d-%H:%M.json'))
    utils.write_json_file(logger, all_saved_songs_file, summary_of_songs)

    # Writes again the Spotify environment with the new token.
    utils.write_json_file(logger, env_file, spotify_env)

    return all_saved_songs_file


def compare_saved_tracks(logger, curr_dir, results_dir, spotify_env_file):
    logger.info('Comparing saved tracks')
    results_dir_path = os.path.join(curr_dir, results_dir)
    match_pattern = results_dir_path + '/all_my_songs_*.json'
    all_songs_path = glob.glob(match_pattern)
    logger.debug('Looking songs with path: %s' % (all_songs_path, ))

    last_saved_time = datetime.datetime(year=1994, month=1, day=1)
    last_saved_songs = ''
    for saved_songs_path in all_songs_path:
        saved_songs_file = saved_songs_path.split('/')[-1]
        saved_time = datetime.datetime.strptime(saved_songs_file,
                                                'all_my_songs_%Y-%m-%d-%H:%M.json')
        if saved_time > last_saved_time:
            last_saved_time = saved_time
            last_saved_songs = saved_songs_path

    logger.debug('Last saved time: %s' % (last_saved_time, ))
    # check_time = last_saved_time + datetime.timedelta(days=7)
    # check_time = last_saved_time + datetime.timedelta(minutes=5)
    check_time = last_saved_time + datetime.timedelta(seconds=1)
    now_time = datetime.datetime.now()

    if now_time > check_time:
        new_saved_songs = download_saved_tracks(logger=logger,
                                                curr_dir=curr_dir,
                                                results_dir=results_dir,
                                                spotify_env_file=spotify_env_file)
    else:
        logger.info('Still not time to check for new songs!')
        return None

    last_saved_songs_dict = utils.open_json_file(logger, last_saved_songs)
    new_saved_songs_dict = utils.open_json_file(logger, new_saved_songs)

    ids_last_songs = set(last_saved_songs_dict.keys())
    ids_new_songs = set(new_saved_songs_dict.keys())

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
        diff_dict['diff_songs']['lost_songs'][track_id] = last_saved_songs_dict[track_id]

    for track_id in ids_not_in_last:
        diff_dict['diff_songs']['new_songs'][track_id] = new_saved_songs_dict[track_id]

    diff_songs_file = os.path.join(results_dir_path,
                                   now_time.strftime('diff_songs_%Y-%m-%d-%H:%M.json'))
    utils.write_json_file(logger, diff_songs_file, diff_dict)
    logger.info('Finished comparing songs file! File written: %s' % (diff_songs_file, ))

    return diff_songs_file


# Parse script arguments
def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--action", "-a", type=str,
                        default="saved_tracks",
                        choices=["saved_tracks", 'compare_saved_tracks'],
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
        else:
            logger.error('The selected option is not available!')
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
