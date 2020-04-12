import pandas as pd
import sys
import os
import time
import numpy as np
import tqdm

# Logging
from v_log import VLogger
import logging

#S3 interaction
from io import StringIO 
import boto3
import subprocess
import re

# UPLOADING SONGS
def get_destination_folder_mp3(audio_file):
    return os.path.join("fs",audio_file[2],audio_file[3],audio_file[4], audio_file)

def file_to_S3(local_path, S3_path,  S3_BUCKET = 'musicemotions'):
    """
    local_path = os.path.join("..","webscrapping","log","WebScrap.log")
    S3_path = nonmatch-query/log.txt
    """
    s3 = boto3.resource('s3')
    resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    return resp


songs_to_upload = os.listdir("data")
for audio_file in songs_to_upload:
    audio_local_path = os.path.join("data", audio_file)
    audio_S3_path = get_destination_folder_mp3(audio_file)
    if audio_file == "TRIVMEG128F4219BA3.mp3":
        resp_audio = file_to_S3(audio_local_path, audio_S3_path,  S3_BUCKET = 'musicemotions')
        print("UPLOADED!!!\n", resp_audio)
