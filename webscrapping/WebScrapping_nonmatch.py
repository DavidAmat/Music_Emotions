#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Web Scrapping: Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Database
import sqlalchemy as db
import pandas as pd
import sys
import os
import time
import re #for avoiding looking at titles with starting parenthesis
import numpy as np
import tqdm

# Logging
from v_log import VLogger
import logging


# In[16]:

# Arguments
batch_num = int(sys.argv[1])


# In[17]:


# Start logging
log = VLogger(f'Batch {batch_num}', uri_log=f"log/WebScrap_nonmatch.log", file_log_level = logging.INFO)


# # 1. Load the clean database

# In[18]:


## 1.1 Connect to the database CLEAN

#Paths
path_db_final = os.path.join("..","data","MSD","clean.db")
path_sql_connection_db =  'sqlite:///' + path_db_final

#Connect
engine = db.create_engine(path_sql_connection_db)
connection = engine.connect()

#Log
log.info("1 Connect to database...")


# In[19]:


def query_db(qq, con = connection, to_df = False):
    res = con.execute(qq)
    if to_df:
        return pd.DataFrame(res.fetchall())
    else:
        return res.fetchall()


# In[20]:


def query_insert(qq, con = connection):
    try:
        res = con.execute(qq)
        return res
    except:
        return False        


# In[22]:


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


# In[41]:


#Log
log.info("2 Select all songs in the nonmatch...")

# Take all songs and clean the titles and create a set to compare with yt titles
df = query_db(f"SELECT * FROM nonmatch where batch_id = {batch_num} ", to_df=True)
if df.shape[0] == 0:
    log.info("NO EXISTE ESE BATCH !!!! ")
    sys.exit("No hay este batch")
else:
    df.columns = ["track_id", "query","batch_id"]

    # Separate all the non alphabetical chracters with spaces, remove them and create a set of words
    df["query_clean_list"] = df["query"].apply(lambda x: fun_clean_title(x, prog, list_return=True))
    df["query_clean_list"] = df["query_clean_list"].apply(lambda x: re.sub('[^0-9a-zA-Z]+', ' ', x))
    df["query_clean_set"] =  df["query_clean_list"].apply(lambda x: set(x.split(" ")))
df  = df.sort_values(["track_id"])

#Log
log.info("2 Select all songs in the nonmatch...(Completed)")


# # 2. WebScrapping

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
    
def insert_dmatch(dmatch, batch_num):
    query_insert_string = "insert into match values "
    for track_id, url in dmatch.items():
        query_insert_string += f"('{track_id}', '{url}', '{batch_num + 1000}'),"
    query_insert_string = query_insert_string[:-1]
    query_insert_string = query_insert_string + ";"
    
    # Insert
    try:
        res = query_insert(query_insert_string)
        return res, query_insert_string
    except:
        return False, query_insert_string

def insert_dnonmatch(dnonmatch, batch_num):
    query_insert_string = "insert into nonmatch values "
    for track_id, yt_query in dnonmatch.items():
        yt_query = yt_query.replace("'"," ")
        query_insert_string += f"('{track_id}', '{yt_query}', '{batch_num + 1000}'),"
    query_insert_string = query_insert_string[:-1]
    query_insert_string = query_insert_string + ";"
    
     # Insert
    try:
        res = query_insert(query_insert_string)
        return res, query_insert_string
    except:
        return False, query_insert_string


# ### Action

#Log
log.info("3 Starting webscrapping...")
dict_match = dict()
dict_nonmatch = dict()
browser = webdriver.Chrome()
counter_iteration = 0

for ii, row in tqdm.tqdm(df.iterrows()):
    counter_iteration += 1
    track_id = row["track_id"]
    query = row["query"]
    batch_id = row["batch_id"]
    query_clean_set = row["query_clean_set"]
    query_clean_list = row["query_clean_list"]
    
    # Query yt song and compare the titles with the query set
    result = query_yt_song(query_clean_list, query_clean_set)
    
    # Save the cases in which we find a match
    if len(result): #there is a href
        dict_match[track_id] = result
    else: #if not, only store the query done
        dict_nonmatch[track_id] = query_clean_list
        
    # Upload each 100 iterations
    if (counter_iteration % 100) == 0: #save each 100 queried songs
        #print("Uploading ", counter_iteration)
        resmatch, qqmatch = insert_dmatch(dict_match, batch_num)
        resnonmatch, qqnonmatch = insert_dnonmatch(dict_nonmatch, batch_num)
        dict_match = dict()
        dict_nonmatch = dict()
        log.info(f"    3.1 Uploaded Counter Iteration: {counter_iteration}")
        
browser.close()
log.info("3 Starting webscrapping... (Completed)")

# In[ ]:


if len(dict_match):
    resmatch, qqmatch = insert_dmatch(dict_match, batch_num)
if len(dict_nonmatch):
    resnonmatch, qqnonmatch = insert_dnonmatch(dict_nonmatch, batch_num)
log.info("4. Uploaded the remaining songs")
log.info(f"5. Succesfully run batch: {batch_num}")