import logging
import os

import yaml


def read_yaml(path_to_yaml: str) -> dict:
    """Reads a yaml file and returns its content as a dictionary."""
    with open(path_to_yaml) as yaml_file:
        content = yaml.safe_load(yaml_file)
    return content


def create_directories(path_to_directories: list):
    """Creates directories if they do not exist."""
    for path in path_to_directories:
        os.makedirs(path, exist_ok=True)
        logging.info(f"Created directory at: {path}")


def get_size(path: str) -> str:
    """Returns size in KB."""
    size_in_kb = round(os.path.getsize(path) / 1024)
    return f"~ {size_in_kb} KB"
