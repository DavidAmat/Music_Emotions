# Database
import pandas as pd
import sys
import os
import time
import numpy as np
import datetime
import tqdm

#S3 interaction
from io import StringIO 
import boto3
import json  # to process the outputs of AWS CLI
import subprocess
import re

# Create SQS client
sqs = boto3.client('sqs')
queue_url_batch = "https://sqs.eu-west-1.amazonaws.com/555381533193/get_batch.fifo"


def send_initial_batchs(batch_num):
    """Send message to SQS queue: get_batch.fifo"""
    response = sqs.send_message(
        QueueUrl=queue_url_batch,
        DelaySeconds=0,
        MessageAttributes={},
        MessageBody=(f"{batch_num}:{iter_ini}"),
        MessageDeduplicationId=f'{batch_num},{iter_ini}',
        MessageGroupId = "batch_initial"
    )


iter_ini = 0
for batch_num in tqdm.tqdm(range(0,36)):
    send_initial_batchs(batch_num)