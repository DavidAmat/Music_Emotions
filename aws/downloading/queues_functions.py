# Database
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


# Create SQS client
sqs = boto3.client('sqs')
queue_url_batch = "https://sqs.eu-west-1.amazonaws.com/555381533193/get_batch.fifo"
queue_url_stat = "https://sqs.eu-west-1.amazonaws.com/555381533193/stat"

# ###################################################################################
# %%%% RECEIVE A MESSAGE AND REMOVE IT
###################################################################################
def sqs_get_batch_iter_from_message(response):
    """Parses the response as json to output the batch and iter numbers from message"""
    sqs_batch, sqs_iter = response["Messages"][0]["Body"].split(":")
    sqs_batch = int(sqs_batch)
    sqs_iter = int(sqs_iter)
    return sqs_batch, sqs_iter

def receive_message_sqs_batch_iter():
    """Receive message from SQS queue: get_batch.fifo
    IMPORTANT! VisibilitTImeout: https://github.com/aws/aws-sdk-js/issues/1279
    """
    response = sqs.receive_message(
        QueueUrl=queue_url_batch,
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=10, # important!!! 
        WaitTimeSeconds=0
    )
    return response

def get_id_message(response):
    """From the response of SQS, it parses the identifier (receiptHandler) of the message"""
    return response["Messages"][0]['ReceiptHandle']

def delete_message(id_message):
    """Deletes the message, it should be under the visibility timeout interval this command,
    otherwise the message will be re-send to the queue"""
    sqs.delete_message(
    QueueUrl=queue_url_batch,
    ReceiptHandle=id_message
    )
    return

def read_message_and_delete(log):
    # Receive a message
    resp = receive_message_sqs_batch_iter()

    # If no message is present in the queue, finish the code
    if "Messages" not in resp:
        log.info("FINAL! No more messages in the queue!! Exiting...")
        sys.exit("No more messages to process!!")
    else:
        # Parse it to obtain batch and number of iteration
        # Add to the log file which batch num and num iter has received
        batch_num, num_iter = sqs_get_batch_iter_from_message(resp)
        log.info(f"Received message. Batch_num: {batch_num}, Num_iter: {num_iter}")

        #Get the identifier of that message to delete it
        id_message = get_id_message(resp)

        # Delete it
        delete_message(id_message)
        log.info(f"Deleted message: {batch_num}:{num_iter}")
    return batch_num, num_iter




# ###################################################################################
# %%%% SEND A NEW BATCH:ITERATION ONCE SKIPPED 5 
###################################################################################

def send_batch_iter(batch_num, counter_iteration):
    """Send message to SQS queue: get_batch.fifo
    Specifying at which batch_num and iteration it has arrived
    """
    response = sqs.send_message(
        QueueUrl=queue_url_batch,
        DelaySeconds=0,
        MessageAttributes={},
        MessageBody=(f"{batch_num}:{counter_iteration}"),
        MessageDeduplicationId=f'{batch_num},{counter_iteration}',
        MessageGroupId = "batch"
    )


# ###################################################################################
# %%%% SEND STATUS
###################################################################################

def get_now():
    now = datetime.datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    return dt_string

def get_current_instance_id():
    try:
        desc_inst = subprocess.check_output('ec2-metadata -i', shell = True).decode('utf-8')
        return desc_inst.strip().split(": ")[1]
    except:
        return False


def get_current_instance_name():
    instance_id =  get_current_instance_id()
    if instance_id is False:
        return False
    comando = f'aws ec2 describe-tags --filters "Name=resource-id,Values={instance_id}"'
    try:
        get_instance_name = subprocess.check_output(comando, shell = True)
        get_instance_name_json = json.loads(get_instance_name)
        instance_name = get_instance_name_json["Tags"][0]["Value"]
        return instance_name
    except:
        return False


def send_status(instance_name, status, batch_num, counter_iteration):
    """Send message to SQS queue: status.fifo
    instance_name: tagged name of the instance 
    status: if the instance has just taken that message, put status = "ON"
    batch_num: batch num that is actually processing (ON) / has processed (OFF) that instance
    counter_iteration: ON: iteration starting at / OFF: iteration that has ended
    date_today: date and hour/minute/second precision to account for  the time of the status
    """
    date_today = get_now()
    message_body = f'{instance_name}:{status}:{batch_num}:{counter_iteration}:{date_today}'
    response = sqs.send_message(
        QueueUrl=queue_url_stat,
        DelaySeconds=0,
        MessageAttributes={},
        MessageBody=(message_body)
    )