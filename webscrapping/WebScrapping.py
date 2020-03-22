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


# In[415]:


# Arguments
batch_num = int(sys.argv[1])

# Fixed batch_size
batch_size = 1000


# In[416]:


# Start logging
log = VLogger(f'Batch {batch_num}', uri_log=f"log/WebScrap.log", file_log_level = logging.INFO)


# # 1. Load the clean database

# In[392]:


## 1.1 Connect to the database CLEAN

#Paths
path_db_final = os.path.join("..","data","MSD","clean.db")
path_sql_connection_db =  'sqlite:///' + path_db_final

#Connect
engine = db.create_engine(path_sql_connection_db)
connection = engine.connect()

#Log
log.info("1 Connect to database...")


# In[396]:


def query_db(qq, con = connection, to_df = False):
    res = con.execute(qq)
    if to_df:
        return pd.DataFrame(res.fetchall())
    else:
        return res.fetchall()


# In[397]:


def query_insert(qq, con = connection):
    try:
        res = con.execute(qq)
        return res
    except:
        return False        


# In[108]:


#Log
log.info("2 Select all songs...")

# Take all songs
df = query_db("SELECT * FROM youtube_url", to_df=True)
df.columns = ["track_id","title","artist_id","yt_url","duration","year","artist_name","artist_iid"]

#Log
log.info("2 Select all songs... (Completed)")


# ## 1.1 Create useful fields

# In[109]:


# Join the title and the artist name
df["tit_art"] = df["title"] + " " + df["artist_name"]
df["tit_art"] = df["tit_art"].str.lower()
df["title"] = df["title"].str.lower()
df["artist_name"] = df["artist_name"].str.lower()


# # 2. WebScrapping

# Create a list for every artist_iid, we create a tuple tit_art & track_id, so that we can iterate for that artist through all of the songs in the MSD and see if any of the track id coincides all the words in the tit_art with the words in the youtube title

# ### Functions

# In[277]:


def fun_clean_title(titart, prog):
    """
    Cleans the title of a MSD song to avoid () or [] or any special character
    """
    # CLEANING TITLE
    words_list = titart.split(" ")
    # we want to avoid words that don't start with a character
    words_set = set()
    for ww in words_list:
        result = prog.match(ww)
        if result is not None: # avoid starting word with parenthesis
            if '\\' not in ww: #avoid non-coded characters \x19
                words_set.add(ww)
    return words_set


# In[273]:


def get_MSD_title_match_yt_title(artist_name, dict_URL_artist, tuple_titart_trackid, prog):
    """
    Get the artist_name and the list of tuples of songs-songID for that artist in MSD
    Returns: a list of matchins and the list of non-mtched songs-songID
    The list of matchings includes songID - youtubeHREF
    """
    # Lista final
    list_matchings = []

    # Loop over each yt song
    for yts_tit, yts_href in dict_URL_artist[artist_name]:
        if yts_href is None:
            continue #if it is a playlist

        # Split into words the yt_title
        words_yt_tit = list(yts_tit.split(" "))
        words_yt_tit = [stt.lower() for stt in words_yt_tit] # convert strings to lower
        words_yt_tit = set(words_yt_tit)

        # Loop over all the songs in MSD for that artist_name 
        #(droping in case of we find a match the song from the MSD list)
        for ii, tup in enumerate(tuple_titart_trackid):

            # Get the MSD TitArt and the Track ID
            msd_titart, msd_tid = tup
            
            # Avoid songs that are named totally equal as their artist_name
            if msd_titart == artist_name:
                continue

            # CLEAN title of MSD
            set_titart_msd = fun_clean_title(msd_titart, prog)
            length_titart_msd = len(set_titart_msd)

            # Make the intersection
            intersect_yt_msd_tit = set_titart_msd.intersection(words_yt_tit)

            # See if all the words in MSD are present in that yt_title
            if len(intersect_yt_msd_tit) == length_titart_msd:

                # Add the track ID and the href
                list_matchings.append((msd_tid,yts_href))

                # Delete the song ffrom the tuple_titar_trackid
                del tuple_titart_trackid[ii]

                #Get out of the loop since we have found a match for that yt song
                break
    return list_matchings, tuple_titart_trackid


# In[336]:


def WebScrapperYoutube(df_WS):
    """
    Performs the WebScrapping
    """
    #Log
    log.info("5.1 Launching Chrome...")

    # Create a dictionary of all the searches with the artist and the titles-href as tuples in that dictionary
    browser = webdriver.Chrome()

    # OUTPUT: Dict for the matching songs and the non-matching
    dict_matching = dict()
    dict_non_matching = dict()

    #Regular expression to avoid strings in MSD initiated with NOT letters
    prog = re.compile("^[A-Za-z]") 

    # Loop for each batch of artists
    for ii,row in tqdm.tqdm(df_WS.iterrows()):

        # Get all the list of tracks for that artist
        artist_iid, artist_name, tuple_titart_trackid = row
        
        #Log
        log.info(f"5.1 Scrapping Artist {artist_name}...")

        # ----------------------------------------------
        # Dicts for each artist
        dict_URL_artist = dict()

        #Output
        dict_matching[artist_name] = dict()
        dict_non_matching[artist_name] = dict()
        # ----------------------------------------------

        # ----------------------------------------------
        #Search that artist on youtube
        browser.get(f"https://www.youtube.com/results?search_query={artist_name}")

        # List all the elements in video-title
        vid_title_elems = browser.find_elements_by_id('video-title')

        #Save youtube results for that artists
        dict_URL_artist[artist_name] = list()

        # Save videos and their URL as tuple
        for vte in vid_title_elems:
            try:
                yt_title =  vte.get_attribute("title")
                yt_href  =  vte.get_attribute('href')
                dict_URL_artist[artist_name].append((yt_title, yt_href))
            except:
                continue
        # ----------------------------------------------

        # ----------------------------------------------
        try:
            # Run the title comparator function
            match_LIST, notmatch_LIT = get_MSD_title_match_yt_title(artist_name, dict_URL_artist, tuple_titart_trackid, prog)
            # ----------------------------------------------
            dict_matching[artist_name] = match_LIST
            dict_non_matching[artist_name] = notmatch_LIT
        except:
            #Log
            log.info(f"5.2 Exception in Artist {artist_name}...")
            dict_non_matching[artist_name] = tuple_titart_trackid

    browser.close()        
    return dict_matching, dict_non_matching


# In[429]:


def insert_dmatch(dmatch, batch_num):
    query_insert_string = "insert into match values "
    for arr, tup in dmatch.items():
        for song in tup:
            track_id, url = song
            query_insert_string += f"('{track_id}', '{url}', '{batch_num}'),"
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
    for arr, tup in dnonmatch.items():
        for song in tup:
            yt_query, track_id = song
            if "'" in yt_query:
                yt_query = yt_query.replace("'"," ")
            query_insert_string += f"('{track_id}', '{yt_query}', '{batch_num}'),"
    query_insert_string = query_insert_string[:-1]
    query_insert_string = query_insert_string + ";"
    
     # Insert
    try:
        res = query_insert(query_insert_string)
        return res, query_insert_string
    except:
        return False, query_insert_string


# # 3 -  Songs for the artists in the same register as a list

# In[338]:


#Log
log.info("3 Create list of songs for each artist...")

# Create a unique register for each artist to store all of his songs
df_list_tit_art = df.groupby(['artist_iid','artist_name'])[['tit_art', "track_id"]].apply(lambda x: x.values.tolist())     .reset_index(name = "tuple_titart_trackid").sort_values(['artist_iid']).set_index("artist_iid")

#Log
log.info("3 Create list of songs for each artist... (Completed)")


# ### Launch as batchs the artists queries to youtube (Selenium)

# In[344]:


#Log
log.info("4 Select artists in batch...")

# Number of all artists
num_queries = df_list_tit_art.shape[0]

#List of artist_iid that will take part in that batch
l_queries = df_list_tit_art.index.values

# Select the range of artist_iid for that batch
idx_artist_iid_batch =  l_queries[batch_num*batch_size : (batch_num+1)*batch_size]

# Select the dataframe registers for that batch
df_WebScrapping = df_list_tit_art.loc[idx_artist_iid_batch,:].reset_index()

#Log
log.info("4 Select artists in batch... (Completed)")


# In[346]:


#Log
log.info("5 Scrapping...")

dmatch, dnonmatch = WebScrapperYoutube(df_WebScrapping)

#Log
log.info("5 Scrapping... (Completed)")


# In[398]:


#Log
log.info("6 Inserting into match and nonmatch tables...")

# Run the queries to insert info
resmatch, qqmatch = insert_dmatch(dmatch, batch_num)
resnonmatch, qqnonmatch = insert_dnonmatch(dnonmatch, batch_num)

# Report errors in the logging
if resmatch is False:
    log.info(f"6.1 EROR INSERTING query in match: {qqmatch}...")
    
if resnonmatch is False:
    log.info(f"6.1 EROR INSERTING query in nonmatch: {qqnonmatch}...")
    
if resmatch:
    if resnonmatch:
        log.info(f"7 Succesfully scrapped Batch {batch_num}")


# In[ ]:




