import sqlalchemy as db
import pandas as pd
import sys
import os
import time
import re #for avoiding looking at titles with starting parenthesis
import numpy as np
import tqdm
from io import StringIO 
import boto3
folder_path = "nonmatch-query"
def ls_S3(folder_path, S3_BUCKET = 'musicemotions', maxkeys = 1000):
    #Connect to S3
    s3 = boto3.client("s3")
    
    # S3 list objects
    response = s3.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix =folder_path,
                MaxKeys=maxkeys )

    files_inside_folder = list()
    for contents_folder in response["Contents"]:
        
        # Get the contents of the folder
        file_names = contents_folder["Key"].split("/")[-1]
        
        #If the name of the file is not empty:
        if len(file_names):
            files_inside_folder.append(file_names)
    return files_inside_folder

print(ls_S3(folder_path, S3_BUCKET = 'musicemotions', maxkeys = 1000))
