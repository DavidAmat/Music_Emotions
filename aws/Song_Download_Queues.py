from queues_functions import *
from download_functions import *

import pandas as pd
import sys
import os
import time
import numpy as np
import datetime

# Logging
from v_log import VLogger
import logging
import tqdm

#S3 interaction
from io import StringIO 
import boto3
import json  # to process the outputs of AWS CLI
import subprocess
import re

# #####################################
# Logging
#######################################
path_local_log_file = f"log/node.log"
log = VLogger(f'Node', uri_log = path_local_log_file, 
                        file_log_level = logging.INFO)

# #####################################
# ARGUMENTS: BATCH - NUM ITER
#######################################
# Read message from the queue and delete it
batch_num, num_iter = read_message_and_delete(log)

###############
# BATCH STATUS
###############
# Send to STATUS that at this batch and iter this node is ON:
instance_name = get_current_instance_name()
status = "ON"
resp_status = send_status(instance_name, status, batch_num, num_iter)

#########################################################
## READ from S3 the songs that matched in the WEBSCRAP
#########################################################
log.info(f"1. Select all songs in match-query (S3) Batch: {batch_num}")
folder_match_results = "match-results"
file_name = f'{batch_num}.csv'
df = load_df_s3([folder_match_results], file_name)
df = df.sort_values("batch_id")
log.info("1. Select all songs in match-query (S3) (Completed)")

########################################################
## RUN the download!
########################################################
log.info("2. Running download iterations")
counter_iteration = 0
counter_skiped = 0
for ii, row in df.iterrows():
    counter_iteration += 1

    # In case we run the program from an iter
    if counter_iteration < num_iter:
        continue

    # WEBSCRAPPING PAUSES -------------------------------------------------------------
    # PAUSE POR SKIPEDS
    if counter_skiped == 5:
        # Iteration to re-start should account for the 5 skipped tracks
        iteration_restart = counter_iteration - 6


        ###############
        # BATCH QUEUE
        ###############
        # Send back to the BATCH queue the batch:iteration
        # at which another EC2 instance should re-start
        log.info(f'Stopping - Sending to batch queue batch {batch_num}, iteration {iteration_restart}')
        send_batch_iter(batch_num, iteration_restart)

        ###############
        # BATCH STATUS
        ###############
        # Send to STATUS that at this batch and iter this node is OFF!!:
        status = "OFF"
        resp_status = send_status(instance_name, status, batch_num, counter_iteration)
        log.info(f'Stopping - stopped instance {instance_name} at batch {batch_num}, iteration {counter_iteration}')
        
        ##############################
        # STOP the instance
        ##############################
        sys.exit("Stopping - Stopped instance")


    # DO a Sleep each 300 iterations of 20 min
    if (counter_iteration % 300) == 0:
        # Each 300 iterations do a 20 minute sleep
        log.info(f"     Pausing at iter: {counter_iteration}: 20 min")
        time.sleep(1200)

    time.sleep(15)

    
    # WEBSCRAPPING PAUSES -------------------------------------------------------------
    
    # GETTING THE SONG URL and REQUESTING THE SIZES AND DOWNLOADING WORST QUALITY AUDIO
    # -------------------------------------------------------------------------------
    track_id, url, batch_id = row
    # Get the audio sizes available and filter out those that are over the reasonable length
    try:
        resp, size_audio, request_response = get_audio_size(url)
    except:
        #ERROR: tsoVU04XA00: YouTube said: The uploader has not made 
        #this video available in your country.
        resp = False
        log.info(f"        Skipped A : {track_id}")
        counter_skiped +=1
        continue
    
    # Skip the song that exceeds file size max in MiB:
    if not resp:
        log.info(f"        Skipped B : {track_id}")
        # no cuenta como skipped
        continue
        
    # Specify command to download audio
    comando_descargar_audio = comando_youtube(track_id, url)
        
    # Download the audio file
    try:
        comando_output = subprocess.check_output(comando_descargar_audio, shell=True) 
    except:
        #ERROR: tsoVU04XA00: YouTube said: The uploader 
        #has not made this video available in your country.
        log.info(f"        Skipped C : {track_id}")
        counter_skiped +=1
        comando_output = False
        continue

    if "100%" in str(comando_output):
        counter_skiped = 0 # re-initialize the counter since it has downloaded a song!
        log.info(f"        Downloaded: {track_id}")
    else:
        # create a log info event indicating that error
        log.info(f"        Skipped D : {track_id}")
        counter_skiped +=1
        continue
     # -------------------------------------------------------------------------------

    # SONG UPLOAD TO S3
    # -------------------------------------------------------------------------------
    song_name_mp3 = track_id + ".mp3"
    response_S3 = False
    try:
        response_S3 = upload_audio_minibatch(song_name_mp3)
    except:
        log.info(f"        Skipped E : {track_id}")
    if response_S3:
        log.info(f"  Iter: {counter_iteration}, Uploaded: {track_id}")
        counter_skiped = 0
    else:
        log.info(f"  Iter: {counter_iteration}, Failed: {track_id}")
    # -------------------------------------------------------------------------------

log.info("2. Running download iterations (Completed)")
log.info(f"3. Succesfully run batch: {batch_num}")


#############################
# BATCH STATUS- finalizado
#############################
# Send to STATUS that at this batch and iter this node is ON:
status = "FI"
resp_status = send_status(instance_name, status, batch_num, counter_iteration)