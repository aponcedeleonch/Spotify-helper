import os
import sys
import time
import datetime
import logging
from logging import handlers
import argparse
import utils
import spotify_security
import spotify_api


def download_saved_tracks(logger, results_dir, spotify_env):
    # Get my Spotify credentials and variables
    env_file = os.path.join(curr_dir, )
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


# Parse script arguments
def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--action", "-a", type=str,
                        default="saved_tracks",
                        choices=["saved_tracks"],
                        help="Choose the action to perform with the script.")

    parser.add_argument("--results_dir", "-rd", type=str,
                        default='results',
                        help="Name of the directory to store the results.")

    parser.add_argument("--spotify_env", "-se", type=str,
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
                                  results_dir=args.results_dir,
                                  spotify_env=args.spotify_env)
        else:
            logger.error('The selected option is not available!')
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
