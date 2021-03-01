# Title
# WebEx Teams Space Analysis
#
# Language
# Python 3.9
#
# Description
# This script will take data from one or more WxT spaces and analyse the content for sentiment, subjectivity and
# polarity. It will also pick out and count positive/negative words. The tool will then upload this data to an
# InfluxDB so that it can be easily displayed graphically.
#
# Contacts
# Phil Bridges - phbridge@cisco.com
#
# EULA
# This software is provided as is and with zero support level. Support can be purchased by providing Phil bridges with a
# varity of Beer, Wine, Steak and Greggs pasties. Please contact phbridge@cisco.com for support costs and arrangements.
# Until provison of alcohol or baked goodies your on your own but there is no rocket sciecne involved so dont panic too
# much. To accept this EULA you must include the correct flag when running the script. If this script goes crazy wrong and
# breaks everything then your also on your own and Phil will not accept any liability of any type or kind. As this script
# belongs to Phil and NOT Cisco then Cisco cannot be held responsable for its use or if it goes bad, nor can Cisco make
# any profit from this script. Phil can profit from this script but will not assume any liability. Other than the boaring
# stuff please enjoy and plagerise as you like (as I have no ways to stop you) but common curtacy says to credit me in some
# way [see above comments on Beer, Wine, Steak and Greggs.].
#
#
# Version Control               Comments
# Version 0.01 Date 28/02/21    Inital draft
# Version 0.02 Date 01/03/21    cleaned up ready for first publish
#
# Version 6.9 Date xx/xx/xx     Took over world and actuially got paid for value added work....If your reading this
#                               approach me on linkedin for details of weekend "daily" rate
# Version 7.0 Date xx/xx/xx     Note to the Gaffer - if your reading this then the above line is a joke only :-)
#
# ToDo *******************TO DO*********************
# 1.0 pull data from WxT            DONE
# 2.0 provide some analysis         DONE
# 3.0 send to Influx                DONE
# 4.0 Include cloud analysis        FUTURE
# 5.0 extend to includ reactions    FUTURE
# 6.0 extend to includ mentions     FUTURE
# 7.0 handle the changing of tokens FUTURE
# 8.0 do something with just files  FUTURE


import requests
import json
import logging.handlers
import signal
import inspect
import threading
from textblob import TextBlob
import datetime
import sys
import traceback

import credentials

WXT_SPACE_ID = credentials.WXT_SPACE_ID
WXT_ACCESS_TOKEN = credentials.WXT_ACCESS_TOKEN
LOGFILE = credentials.LOGFILE
THREAD_TO_BREAK = threading.Event()
INFLUX_DB_PATH = credentials.INFLUX_DB_PATH


def check_space_for_new_content(last_x_messages=12):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("checking space for new content")
    for each_room in WXT_SPACE_ID:
        url = "https://webexapis.com/v1/messages?roomId=%s&max=%s" % (each_room, last_x_messages)  # 1000000000
        headers = {"Authorization": "Bearer %s" % WXT_ACCESS_TOKEN}
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            json_for_analysis = json.loads(response.text)["items"]
            print(json_for_analysis)
            print(len(json_for_analysis))
            person_dictionary = {}
            thread_dictionary = {}
            for each_message in json_for_analysis:
                if not person_dictionary.get(each_message['personId']):
                    person_dictionary[each_message['personId']] = each_message['personEmail']
                if each_message.get('parentId', False):
                    if thread_dictionary.get(each_message['parentId'], False):
                        thread_dictionary[each_message['parentId']].append(datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000)
                    else:
                        thread_dictionary[each_message['parentId']] = []
                        thread_dictionary[each_message['parentId']].append(datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000)
            influx_string = ""
            for each_message in json_for_analysis:
                polarity = 0
                subjectivity = 0
                positive_words = 0
                neagative_words = 0
                person_email = "N/A"
                timestamp = 0
                # try:
                timestamp = datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000
                # print(int(timestamp))
                if each_message.get('text'):
                    blob = TextBlob(each_message['text'])
                    polarity = blob.polarity
                    subjectivity = blob.subjectivity
                    for each in blob.sentiment_assessments[2]:
                        # print(each)
                        if each[1] >= 0:
                            positive_words += 1
                        else:
                            neagative_words += 1
                    is_thread = False
                    thread_size = 0
                    if thread_dictionary.get(each_message['id'], False):
                        is_thread = True
                        thread_size = len(thread_dictionary[each_message['id']])
                    is_thread_response = False
                    thread_position = 0
                    if each_message.get('parentId', False):
                        is_thread_response = True
                        temp_array = thread_dictionary[each_message['parentId']]
                        temp_array.sort()
                        # print(temp_array)
                        for each in temp_array:
                            thread_position += 1
                            if int(each) == int(datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000):
                                break
                    influx_string += "WxTSpaceMessageAnalysis," \
                                     "personId=%s,is_thread=%s,is_thread_response=%s,thread_position=%s " \
                                     "polarity=%s,subjectivity=%s,words=%s,sentences=%s," \
                                     "impact_words=%s,positive_words=%s,negative_words=%s," \
                                     "thread_size=%s %s \n" % \
                                     (each_message['personEmail'], is_thread, is_thread_response, thread_position,
                                      polarity, subjectivity, len(blob.words), len(blob.sentences),
                                      len(blob.sentiment_assessments[2]), positive_words, neagative_words,
                                      thread_size, str(int(timestamp)))
                elif each_message.get('files'):
                    polarity = 0
                    subjectivity = 0
                else:
                    print("no text or file")
                    print(each_message)
            update_influx(influx_string)
        else:
            function_logger.critical("something went wrong didnt get status 200 from WxT instead got %s" % response.status_code)
            function_logger.critical("following bad status code content was :- %s" % response.content)
            print(response.status_code)
            print(response.content)


def update_influx(raw_string, timestamp=None):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    try:
        string_to_upload = ""
        if timestamp is not None:
            timestamp_string = str(int(timestamp.timestamp()) * 1000000000)
            for each in raw_string.splitlines():
                string_to_upload += each + " " + timestamp_string + "\n"
        else:
            string_to_upload = raw_string
        success_array = []
        upload_to_influx_sessions = requests.session()
        for influx_path_url in INFLUX_DB_PATH:
            success = False
            attempts = 0
            attempt_error_array = []
            while attempts < 5 and not success:
                try:
                    upload_to_influx_sessions_response = upload_to_influx_sessions.post(url=influx_path_url, data=string_to_upload, timeout=(2, 1))
                    if upload_to_influx_sessions_response.status_code == 204:
                        function_logger.debug("content=%s" % upload_to_influx_sessions_response.content)
                        function_logger.debug("status_code=%s" % upload_to_influx_sessions_response.status_code)
                        success = True
                    else:
                        attempts += 1
                        function_logger.warning("status_code=%s" % upload_to_influx_sessions_response.status_code)
                        function_logger.warning("content=%s" % upload_to_influx_sessions_response.content)
                except requests.exceptions.ConnectTimeout as e:
                    attempts += 1
                    function_logger.debug("attempted " + str(attempts) + " Failed Connection Timeout")
                    function_logger.debug("Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.debug("Unexpected error:" + str(e))
                    function_logger.debug("String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                except requests.exceptions.ConnectionError as e:
                    attempts += 1
                    function_logger.debug("attempted " + str(attempts) + " Failed Connection Error")
                    function_logger.debug("Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.debug("Unexpected error:" + str(e))
                    function_logger.debug("String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                except Exception as e:
                    function_logger.error("attempted " + str(attempts) + " Failed")
                    function_logger.error("Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.error("Unexpected error:" + str(e))
                    function_logger.error("String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                    break
            success_array.append(success)
        upload_to_influx_sessions.close()
        super_success = False
        for each in success_array:
            if not each:
                super_success = False
                break
            else:
                super_success = True
        if not super_success:
            function_logger.error("FAILED after 5 attempts. Failed up update " + str(string_to_upload.splitlines()[0]))
            function_logger.error("FAILED after 5 attempts. attempt_error_array: " + str(attempt_error_array))
            return False
        else:
            function_logger.debug("string for influx is " + str(string_to_upload))
            function_logger.debug("influx status code is  " + str(upload_to_influx_sessions_response.status_code))
            function_logger.debug("influx response is code is " + str(upload_to_influx_sessions_response.text[0:1000]))
            return True
    except Exception as e:
        function_logger.error("something went bad sending to InfluxDB")
        function_logger.error("Unexpected error:" + str(sys.exc_info()[0]))
        function_logger.error("Unexpected error:" + str(e))
        function_logger.error("TRACEBACK=" + str(traceback.format_exc()))
    return False


def run_this():
    check_space_for_new_content(last_x_messages=1000000)


def graceful_killer(signal_number, frame):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("Got Kill signal")
    function_logger.info('Received:' + str(signal_number))
    THREAD_TO_BREAK.set()
    function_logger.info("set threads to break")
    function_logger.info("joined threads")
    function_logger.info("stopped HTTP server")
    quit()


if __name__ == "__main__":
    # Create Logger
    logger = logging.getLogger("__main__")
    handler = logging.handlers.TimedRotatingFileHandler(LOGFILE, backupCount=30, when='D')
    logger_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(process)d:%(name)s - %(message)s')
    handler.setFormatter(logger_formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("---------------------- STARTING ----------------------")
    logger.info("cisco EoS EoL script started")

    # Catch SIGTERM etc
    signal.signal(signal.SIGHUP, graceful_killer)
    signal.signal(signal.SIGTERM, graceful_killer)

    run_this()
