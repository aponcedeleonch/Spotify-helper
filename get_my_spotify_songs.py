import os
import time
import datetime
import logging
from logging import handlers
import requests
from spotify_env import spotify_env


def get_favorites_playlist():
    url = "https://api.spotify.com/v1/playlists/%s" % (spotify_env['my_favorites_playlist_id'], )

    headers = {
      'Authorization': 'Bearer %s' % (spotify_env['bearer'], )
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response_dic = response.json()
        print(response_dic)


if __name__ == "__main__":
    start_time = time.time()

    # Select data directory
    curr_dir = os.path.dirname(os.path.realpath(__file__))

    # Get a logger of the events
    logfile = os.path.join(curr_dir, 'logs_spotify_fetcher.log')
    numeric_log_level = getattr(logging, "DEBUG", None)
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S %p',
        level=numeric_log_level,
        handlers=[
            # Max store 1 GB of logs
            handlers.RotatingFileHandler(logfile,
                                         maxBytes=100e6,
                                         backupCount=10),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()
    logger.info('Logger ready. Logging to file: %s' % (logfile))

    # Creating a directory for the results of the script
    out_dir_path = os.path.join(curr_dir, 'results')
    os.makedirs(out_dir_path, exist_ok=True)
    logger.debug('Created dir for results: %s' % out_dir_path)

    # Starting with the tasks (main loop)
    try:
        get_favorites_playlist()
    except Exception:
        logger.exception("Fatal error in main loop")
    finally:
        elapsed_time = time.time() - start_time
        elapsed_delta = datetime.timedelta(seconds=elapsed_time)
        logger.info('Total elapsed time of execution: %s' % (elapsed_delta, ))
