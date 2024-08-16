
import os
import json
import wget
import glob
import logging
import requests
import mimetypes
from pathlib import Path
from mutagen.mp3 import MP3
from datetime import datetime
from multiprocessing import Pool
from dotenv import dotenv_values
from mutagen.id3 import ID3, APIC
from urllib.parse import urlsplit


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
logging.info(f"Start at {now} with {threads} threads")


def lastFMRequest(artist, album):
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
        response = requests.get(api_url, headers=headers, params=payload)
        logging.info(f"Get info for {artist} - {album} - OK")
        return response
    except Exception as e:
        logging.error(f"{artist} - {album}, LastFM API error: {e}")


def getMP3Img(file):
    try:
        file_ = MP3(file)
        album = file_.tags['TALB']
        artist = file_.tags['TPE1']
        if album is not None and artist is not None:
            responseData = lastFMRequest(artist, album)
            img_url = responseData.json()['album']['image'][5]['#text']
            album = responseData.json()['album']['name']
            imgFilePath = f"{os.path.dirname(file)}/{artist}-{album}_cover{os.path.splitext(urlsplit(img_url).path)[-1]}"
            if not Path(imgFilePath).exists():
                wget.download(img_url, imgFilePath)
                logging.info(f"Download image for {file} - OK")
            else:
                logging.info(f"Image for {file} already exist")
            return imgFilePath
        else:
            logging.warning(f"{file} - Album or Artist is empty, skip file")
            return None
    except Exception as e:
        logging.error(f"{file} - Get image error: {e}, skip file")



def addImgToMp3(file):
    try:
        file_ = MP3(file, ID3=ID3)
        img = getMP3Img(file)
        if img is not None:
            file_.tags.add(APIC(
                    encoding=0, 
                    mime=mimetypes.guess_type(img), 
                    type=3, 
                    desc='Cover (front)', 
                    data=open(img,'rb').read()
                    ))
            file_.save()
            logging.info(f"Add image for {file} - OK")
        else:
            logging.warning(f"{file} - Image not found, skip file")
            return None
    except Exception as e:
        logging.error(f"{file} - Add image to mp3 file error: {e}, skip file")


def main():
    start = datetime.now()
    files_ = glob.glob(dirPath + '/**/*.mp3', recursive=True)
    #for file_ in files_:
    #    addImgToMp3(file_)
    with Pool(threads) as p:
        p.map(addImgToMp3, files_)
    end = datetime.now()
    total = str(end - start)
    logging.info(f"All done for {total}. ")


if __name__ == '__main__':
    main()