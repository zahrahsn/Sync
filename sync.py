import argparse
import glob
import os
import shutil
import logging
import hashlib
import threading
import time
from pathlib import Path

parser = argparse.ArgumentParser(prog='sync.py')
parser.add_argument('source', help='Source folder path')
parser.add_argument('destination', help='Destination folder path')
parser.add_argument(
    '--time', nargs='?',
    help='Set time period',
    type=int, default=60
)
parser.add_argument(
    '--log', nargs='?',
    help='The path of log file (including name)',
    type=str, default='std.log'
)
args = parser.parse_args()


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler(filename=args.log, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

source_folder = args.source
destination_folder = args.destination
run_event = threading.Event()


def listing_file(path):
    dir_path = os.path.join(path, '**', '*.*')
    file_list = glob.glob(dir_path, recursive=True)
    file_list = list(map(lambda x: os.path.relpath(x, path), file_list))
    file_list.sort()
    return file_list


def getting_absolute_path(folder_path, file):
   return os.path.join(folder_path, file)


def file_hash(path):
    md5_hash = hashlib.md5()
    content = open(path, "rb").read()
    md5_hash.update(content)
    return md5_hash.hexdigest()


def actions():
    while run_event.is_set():
        logger.info("SYNCING...")
        source_list = listing_file(source_folder)
        destination_list = listing_file(destination_folder)

        to_delete = [getting_absolute_path(
            destination_folder, d) for d in destination_list if d not in source_list]
        to_copy = []
        to_update = []
        for s in source_list:
            peer = next(filter(lambda x: x == s, destination_list), None)
            if peer is None:
                to_copy.append(s)
            else:
                file_path = getting_absolute_path(source_folder, s)
                peer_path = getting_absolute_path(destination_folder, peer)
                if file_hash(file_path) != file_hash(peer_path):
                    to_update.append(s)
        delete(to_delete)
        copy(to_copy)
        update(to_update)
        logger.info("DONE!")
        time.sleep(args.time)


def delete(to_delete):
    for d in to_delete:
        os.remove(d)
        logger.info(f'DELETED: {d}')


def copy(to_copy):
     for c in to_copy:
        file_path = getting_absolute_path(source_folder, c)
        peer_path = getting_absolute_path(destination_folder, c)
        path, file = os.path.split(peer_path)
        Path(path).mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, peer_path)
        logger.info(f'COPIED: {file_path} --> {peer_path}')


def update(to_update):
    for u in to_update:
        u_path = getting_absolute_path(destination_folder, u)
        os.remove(u_path)
        file_path = getting_absolute_path(source_folder, u)
        shutil.copy2(file_path, u_path)
        logger.info(f'UPDATED: {file_path} --> {u_path}')


if __name__ == '__main__':
    try:
        run_event.set()
        th = threading.Thread(target = actions)
        th.start()
        # Waiting for keyboard interrupt   
        while True: 
            time.sleep(100)
    except KeyboardInterrupt:
        logger.info('Exitting...Please wait')
        run_event.clear()
        th.join()
        exit(0)
