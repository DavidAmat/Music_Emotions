# Database
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

# Arguments
batch_num = int(sys.argv[1])
num_iter = int(sys.argv[2])


# Start logging
path_local_log_file = f"log/{batch_num}.log"
log = VLogger(f'Batch {batch_num}', uri_log = path_local_log_file, file_log_level = logging.INFO)


######################################################################################################
## FUNCTIONS
######################################################################################################
def load_df_s3(folder_list_path, file_name, S3_BUCKET = 'musicemotions'):
    """
    folder_list_path = ["folder1", "folder2", "folder3"]
    file_name = "1.csv"
    """
    # Client S3
    s3 = boto3.client("s3")

    # Convert list of folders in S3 to path
    path_S3 = os.path.join(*folder_list_path,file_name) 
    print(path_S3)
    csv_obj = s3.get_object(Bucket = S3_BUCKET,  Key = path_S3)
    body = csv_obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    return df

def get_audio_size(url,max_audio_size = 6):
    """
    Uses th youtube-dl -F argument to look for audio formats of that video
    It lists the audio formats in different lines
    Some of them terminate with MiB or KiB (size of audio file)
    Some do not end with that... so maybe the only size you get is the high quality video
    This size may be 4 or 5 times larger than the worst audio size, which is not reported in size, so we will trust
    this criteria and download it. Whichever length that the first audio surpases 6MB or the highest quality ones
    surpass 4 times that amount (24MB) they will not be eligible for download
    """
    direct_output = subprocess.check_output(f'youtube-dl -F {url}', shell=True) 
    words_output = str(direct_output).split("\\n")
    counter_audio_record = 0
    for word in words_output:
        counter_audio_record += 1 #which record has info abut MiB or KiB (maybe the first one has not this data)
        if "MiB" in word:
            try:
                size_audio = re.findall(r"(\d+)(\.\d*)?MiB",word)
                size_audio_MiB = int(size_audio[0][0])
                break
            except:
                size_audio_MiB = 1000
        if "KiB" in word:
            try:
                size_audio = re.findall(r"(\d+)(\.\d*)?KiB",word)
                size_audio_MiB = int(size_audio[0][0]) / 1000
                break
            except:
                size_audio_MiB = 1000
    if size_audio_MiB < max_audio_size:
        return True, size_audio_MiB, words_output# the size is less than the maximum, hence, download it!
    # This correction is done for songs that on the first audio record has not a MiB or KiB
    # but when looking at the high quaity audio a register is there and maybe its 10MB so the song with the worst
    #audio will be small enough to be downloaded
    elif size_audio_MiB >= max_audio_size and counter_audio_record > 5:  # if it was the first listed audio size and 
        if size_audio_MiB < max_audio_size*4: # if unless listed in HIGH quality audio does not oduble the max size
            return True, size_audio_MiB, words_output #mark it as downloadable
        else: # if it surpasses the 24MB in the high quality audio, better not to download it just in case
            return False, size_audio_MiB, words_output
    else:
        return False, size_audio_MiB, words_output
    
    
def comando_youtube(track_id, url, path_audio = 'data/'):
    """
    Once the audio file size has been checked, we will download the worst audio to mp3 format
    path_output = data/
    url = youtube url
    """
    comando1 = f'youtube-dl -ci -f "worstaudio" -x --audio-format mp3 '
    path_output = path_audio +  track_id + ".mp3"
    comando2 = f" --output {path_output}"
    return comando1 + url + comando2

def file_to_S3(local_path, S3_path,  S3_BUCKET = 'musicemotions'):
    """
    local_path = os.path.join("..","webscrapping","log","WebScrap.log")
    S3_path = nonmatch-query/log.txt
    """
    s3 = boto3.resource('s3')
    resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    return resp

# UPLOADING SONGS
def get_destination_folder_mp3(audio_file):
    return os.path.join("fs",audio_file[2],audio_file[3],audio_file[4], audio_file)

def upload_audio_minibatch():
    """
    Takes the songs in /data folder and uploads them to the S3 bucket
    """
    counter_uploaded_songs = 0
    songs_to_upload = os.listdir("data")
    for audio_file in songs_to_upload:
        audio_local_path = os.path.join("data", audio_file)
        audio_S3_path = get_destination_folder_mp3(audio_file)
        try:
            resp_audio = file_to_S3(audio_local_path, audio_S3_path,  S3_BUCKET = 'musicemotions')
            if resp_audio:
                counter_uploaded_songs += 1
            log.info(f"        -- Uploaded: {audio_file}")
        except:
            log.info(f"        -- Upload Error: {audio_file}")
        os.remove(os.path.join("data", audio_file))
    return counter_uploaded_songs

######################################################################################################
## READ from S3 the songs that matched in the WEBSCRAP
######################################################################################################
log.info("1. Select all songs in match-query (S3)")
folder_match_results = "match-results"
file_name = f'{batch_num}.csv'
df = load_df_s3([folder_match_results], file_name)
df = df.sort_values("batch_id")
log.info("1. Select all songs in match-query (S3) (Completed)")

######################################################################################################
## RUN the download!
######################################################################################################
log.info("2. Running download iterations")
iter_upload_each = 20 #each 50 songs, upload to S3

for ii, row in tqdm.tqdm_notebook(df.iterrows()):
    # In case we run the program from an iter
    if ii < num_iter:
        continue

    track_id, url, batch_id = row
    
    # Get the audio sizes available and filter out those that are over the reasonable length
    resp, size_audio, request_response = get_audio_size(url)
    
    # Skip the song that exceeds file size max in MiB:
    if not resp:
        continue
        
    # Specify command to download audio
    comando_descargar_audio = comando_youtube(track_id, url)
        
    # Download the audio file
    comando_output = subprocess.check_output(comando_descargar_audio, shell=True) 
    if "100%" in str(comando_output):
        log.info(f"        Downloaded: {track_id}")
        continue
    else:
        # create a log info event indicating that error
        log.info(f"        Skipped: {track_id}")
        continue
    
    # When it reaches 50 downloads, do a round of uploadings to the S3 bucket
    if (ii % iter_upload_each) == 0:
        num_uploads = upload_audio_minibatch()
        log.info(f"  Uploaded Counter Iteration: {ii}, Uploaded: {num_uploads} files")


log.info("2. Running download iterations (Completed)")
log.info(f"3. Succesfully run batch: {batch_num}")