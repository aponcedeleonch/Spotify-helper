import json


def open_json_file(logger, file):
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
    python_dic = {}
    with open(file, 'r') as f:
        python_dic = json.load(f)
    logger.info('Parsed JSON file: %s' % (file, ))

    if python_dic is None:
        raise NameError('The specified file was not found!')

    return python_dic


def write_json_file(logger, file, python_dic):
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
    with open(file, 'w') as f:
        json.dump(python_dic, f, ensure_ascii=False, indent=2)
    logger.info('JSON file written: %s' % (file, ))
