#!/usr/bin/env python
# coding: utf-8

# In[1]:

# Web Scrapping: Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

#Selenium options
options = Options()
options.add_argument("--headless")
options.add_argument("window-size=1400,1500")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("start-maximized")
options.add_argument("enable-automation")
options.add_argument("--disable-infobars")
options.add_argument("--disable-dev-shm-usage")


# Database
import sqlalchemy as db
import pandas as pd
import sys
import os
import time
import re #for avoiding looking at titles with starting parenthesis
import numpy as np
import tqdm

#S3 interaction
from io import StringIO 
import boto3

# Logging
from v_log import VLogger
import logging


# In[16]:

# Arguments
batch_num = int(sys.argv[1])
num_iter = int(sys.argv[2])

# In[17]:


# Start logging
path_local_log_file = f"log/{batch_num}.log"
log = VLogger(f'Batch {batch_num}', uri_log = path_local_log_file, file_log_level = logging.INFO)

 

#Regular expression to avoid strings in MSD initiated with NOT letters
prog = re.compile("^[A-Za-z]") 

def fun_clean_title(titart, prog, list_return = False):
    """
    Cleans the title of a MSD song to avoid () or [] or any special character
    """
    # CLEANING TITLE
    words_list = titart.split(" ")
    # we want to avoid words that don't start with a character
    words_set = set()
    words_clean = list()
    for ww in words_list:
        result = prog.match(ww)
        if result is not None: # avoid starting word with parenthesis
            if '\\' not in ww: #avoid non-coded characters \x19
                if (")" not in ww) and ("(" not in ww):
                    words_set.add(ww.lower())
                    words_clean.append(ww.lower())
    if not list_return:
        return words_set
    else:
        return " ".join(words_clean)

    
###########################################
###########################################

        # S3: functions

###########################################
###########################################

# S3 load df from batch file
def load_df_s3(folder_path, file_name, S3_BUCKET = 'musicemotions'):
    s3 = boto3.client("s3")
    path_S3 = folder_path + "/" + file_name  
    csv_obj = s3.get_object(Bucket = S3_BUCKET,  Key = path_S3)
    body = csv_obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    return df

#save any local file in the EC2 instance to S3 
def file_to_S3(local_path, S3_path,  S3_BUCKET = 'musicemotions'):
    """
    local_path = os.path.join("..","webscrapping","log","WebScrap.log")
    S3_path = nonmatch-query/log.txt
    """
    if S3_path:
        s3 = boto3.resource('s3')
        resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    else:
        s3 = boto3.resource('s3')
        resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    return resp



#######################################################################
#######################################################################

# S3: Look at nonmatch-query to find the query to launch webscrapping

#######################################################################
#######################################################################

folder_path = "nonmatch-query"
name_file = f'{batch_num}.csv'

# LOAD DATAFRAME FROM THE QUERY NONMATCH .CSV
df = load_df_s3(folder_path, name_file)

# Load dataframe of that batch
log.info("1. Select all songs in nonmatch-query (S3)")

# Separate all the non alphabetical chracters with spaces, remove them and create a set of words
df["query_clean_list"] = df["query"].apply(lambda x: fun_clean_title(x, prog, list_return=True))
df["query_clean_list"] = df["query_clean_list"].apply(lambda x: re.sub('[^0-9a-zA-Z]+', ' ', x))
df["query_clean_set"] =  df["query_clean_list"].apply(lambda x: set(x.split(" ")))
df  = df.sort_values(["track_id"])

#Log
log.info("1. Select all songs in nonmatch-query (S3) (Completed)")

#######################################################################
#######################################################################

#    WebScrapping - Functions

#######################################################################
#######################################################################

# Query the non-matched titles

# ### Functions

def query_yt_song(qq_song, query_set):
        #Search that artist on youtube
        browser.get(f"https://www.youtube.com/results?search_query={qq_song}")
        
        # List all the elements in video-title
        vid_title_elems = browser.find_elements_by_id('video-title')

        # Save videos and their URL as tuple
        for vte in vid_title_elems:
            yt_title =  vte.get_attribute("title")
            yt_href  =  vte.get_attribute('href')
            
            #Compare that title with the query and if coincides in all words except 1 get that href
            if compare_song_vs_title(yt_title, query_set):
                #Make sure that the href is not a playlist (hence playlist does not have href: None)
                if yt_href:
                    return yt_href
        return ""

def compare_song_vs_title(yt_tit, query_set):
    
    # YOUTUBE SONG to SET (cleaned)
    yt_set = fun_clean_title(yt_tit, prog, list_return=True) #returns a string
    
    #SUBSTITUTE ANY NON ALPHANUMERICA CHARACTERS by white space
    yt_set = re.sub('[^0-9a-zA-Z]+', ' ', yt_set)
    yt_set = set(yt_set.split(" ")) #convert the words separated by spaces into a set
    
    #Maybe that set contains words with one letter, so in that case we will remove them
    neat_query_set = set()
    for nn in list(query_set):
        if len(nn) > 1:
            neat_query_set.add(nn)
    query_set = neat_query_set; # only take the query set as the neat set without single letters or white spaces
    
    # Intersection
    int_set = query_set.intersection(yt_set)
    
    # Compare the length of the yt_set with the query set
    if len(int_set) >= (len(query_set) - 1): # allow one missing word in the intersection compared to the query set
        return True
    elif len(query_set) > 4: # if the query is bigger thatn 4, allow a intersection set coincidence of 2 words less
        if len(int_set) >= (len(query_set) - 2):
            return True
    else:
        return False
    
def load_df_s3(folder_path, file_name, S3_BUCKET = 'musicemotions'):
    s3 = boto3.client("s3")
    path_S3 = folder_path + "/" + file_name  
    csv_obj = s3.get_object(Bucket = S3_BUCKET,  Key = path_S3)
    body = csv_obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    return df

def save_df_to_S3(df, folder_path, name_file, S3_BUCKET = 'musicemotions'):
    #Connect to S3
    s3 = boto3.client("s3")
    
    #Set the destination path
    path_S3 = folder_path + "/" + name_file
    
    # Buffer dataframe to upload
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index = False)

    resp = s3.put_object(Bucket = S3_BUCKET, Key = path_S3, Body = csv_buffer.getvalue())
    return resp
    
def dmatch_to_df(dmatch, batch_num, columns_df):
    df = pd.DataFrame(dmatch.items())
    df.columns = columns_df
    # Add 1000 to the batch num to identify those nonmatched rescued as matched
    df["batch_id"] = batch_num + 1000
    return df

def dmatch_to_S3(dmatch, batch_num, folder_path):
    
    # Get the S3 file with that name
    name_file = f'{batch_num}.csv'
    
    # From the match_results
    df_S3 = load_df_s3(folder_path, name_file)
    
    # Get the dmatch and convert it to dataframe
    df_match = dmatch_to_df(dmatch, batch_num, columns_df = ["track_id","url"])
    
    # Join the existing df in S3 with the df_match for that iteration
    df_concat = pd.concat([df_S3, df_match], axis=0)
    
    # Save DMATCH to S3
    res = save_df_to_S3(df_concat, folder_path, name_file, S3_BUCKET = 'musicemotions')
    
    return res
    

#######################################################################
#######################################################################

#    WebScrapping - Iterate

#######################################################################
#######################################################################

#Log
log.info("3 Starting webscrapping...")
dict_match = dict()
browser = webdriver.Chrome(options=options)
counter_iteration = 0

iter_download = 50; #upload each 100 iterations

for ii, row in tqdm.tqdm(df.iterrows()):
    counter_iteration += 1
    if ii<num_iter:
        continue
    track_id = row["track_id"]
    query = row["query"]
    batch_id = row["batch_id"]
    query_clean_set = row["query_clean_set"]
    query_clean_list = row["query_clean_list"]
    
    try:
        # Query yt song and compare the titles with the query set
        result = query_yt_song(query_clean_list, query_clean_set)
    except:
        log.info(f"    3.0 ERROR: Error in iteration : {counter_iteration}")
        continue
    
    # Save the cases in which we find a match
    if len(result): #there is a href
        dict_match[track_id] = result

    # Upload each iter_download iterations
    if (counter_iteration % iter_download) == 0: #save each iter_download queried songs
        res = dmatch_to_S3(dict_match, batch_num, "match-results")        
        dict_match = dict()
        log.info(f"    3.1 Uploaded Counter Iteration: {counter_iteration}")
        
browser.close()
log.info("3 Starting webscrapping... (Completed)")
log.info(f"5. Succesfully run batch: {batch_num}")


# Upload the log file to S3
def file_to_S3(local_path, S3_path,  S3_BUCKET = 'musicemotions'):
    """
    local_path = os.path.join("..","webscrapping","log","WebScrap.log")
    S3_path = nonmatch-query/log.txt
    """
    if S3_path:
        s3 = boto3.resource('s3')
        resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    else:
        s3 = boto3.resource('s3')
        resp = s3.Object(S3_BUCKET, S3_path).put(Body=open(local_path, 'rb'))
    return resp

# Upload log file to log/nonmatch-query
#       path log in S3
log_S3_path = f"log/nonmatch-query/{batch_num}.log"
resp_log = file_to_S3(path_local_log_file, log_S3_path,  S3_BUCKET = 'musicemotions')

