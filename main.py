""" Get cover from last FM API """

import os
import glob
import logging
import mimetypes
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool
from urllib.parse import urlsplit
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen import MutagenError
import requests
from dotenv import dotenv_values


now = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

config = dotenv_values()

api_url = config['API_URL']
api_key = config['API_KEY']
dirPath = config['DIR_PATH']
fileExt = config['FILE_EXT']
method = config['METHOD']
request_format = config['REQUEST_FORMAT']
threads = int(config['THREADS'])
logs_dir = config['LOGS_DIR']

logging.basicConfig(level=logging.INFO, filename=f"{logs_dir}/getCover_{now}.log", filemode="w")
logging.info("Start at %s with %s threads", now, threads)


def download_file(url, filename):
    """ Download file from over http """
    try:
        with open(filename, 'wb') as file:
            file.write(requests.get(url, timeout=10).content)
    except Exception as e:
        logging.error("%s - %s Download file error %s", url, filename, e)


def last_fm_request(artist, album):
    """ Request to lastfm API """
    try:
        headers = {
            'user-agent': 'Dataquest'
        }
        payload = {
            'api_key': api_key,
            'method': method,
            'format': request_format,
            'artist': artist,
            'album': album
        }
        response = requests.get(api_url, headers=headers, params=payload, timeout=10)
        logging.info("Get info for %s - %s - OK", artist, album)
        return response
    except requests.exceptions.ConnectionError:
        logging.error("%s - %s LastFM API error - A connection error occurred." , artist, album)
    except requests.exceptions.Timeout:
        logging.error("%s - %s LastFM API error - The request timed out." , artist, album)
    except requests.exceptions.HTTPError as e:
        logging.error("%s - %s LastFM API error - HTTP Error: %s", artist, album, e)
    except requests.exceptions.RequestException as e:
        logging.error("%s - %s LastFM API error - An error occurred: %s", artist, album, e)


def get_mp3_img(file):
    """ Download album image """
    try:
        file_ = MP3(file)
        if 'TALB' in file_:
            album = file_.tags['TALB']
        else:
            album = None
            logging.error("No album field in %s", file)
        if 'TPE1' in file_:
            artist = file_.tags['TPE1']
        else:
            artist = None
            logging.error("No artist field in %s", file)
        if album is not None and artist is not None:
            response_data = last_fm_request(artist, album)
            img_url = response_data.json()['album']['image'][5]['#text']
            album = response_data.json()['album']['name']
            img_filename = f"{artist}-{album}_cover{os.path.splitext(urlsplit(img_url).path)[-1]}"
            img_file_path = f"{os.path.dirname(file)}/{img_filename}"
            if not Path(img_file_path).exists():
                download_file(img_url, img_file_path)
                logging.info("Download image for %s - OK", file)
            else:
                logging.info("Image for %s already exist", file)
            return img_file_path
        else:
            logging.warning("%s - Album or Artist is empty, skip file", file)
            return None
    except MutagenError as e:
        logging.error("%s - Mutagen error: %e, skip file", file, e)
    except Exception as e:
        logging.error("%s - Get image error: %e, skip file", file, e)



def add_img_to_mp3(file):
    """ Add image to mp3 file """
    try:
        file_ = MP3(file, ID3=ID3)
        img = get_mp3_img(file)
        if img is not None:
            file_.tags.add(APIC(
                    encoding=0,
                    mime=mimetypes.guess_type(img),
                    type=3,
                    desc='Cover (front)',
                    data=open(img,'rb').read()
                    ))
            file_.save()
            logging.info("Add image for %s - OK", file)
        else:
            logging.warning("%s - Image not found, skip file", file)
            return None
    except MutagenError as e:
        logging.error("%s - Mutagen error: %e, skip file", file, e)
    except Exception as e:
        logging.error("%s - Add image to mp3 file error: %s, skip file", file, e)


def main():
    """ Main """
    start = datetime.now()
    files_ = glob.glob(dirPath + '/**/*.mp3', recursive=True)
    #for file_ in files_:
    #    addImgToMp3(file_)
    with Pool(threads) as p:
        p.map(add_img_to_mp3, files_)
    end = datetime.now()
    total = str(end - start)
    logging.info("All done for %s. ", total)


if __name__ == '__main__':
    main()
