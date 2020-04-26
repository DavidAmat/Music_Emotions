# Database
import pandas as pd
import sys
import os
import time
import numpy as np

# Logging
from v_log import VLogger
import logging

#S3 interaction
from io import StringIO 
import boto3
import subprocess
import re


# Create SQS client
sqs = boto3.client('sqs')
queue_url_ = 'SQS_QUEUE_URL'


print(sqs)