# Copyright (c) 2021 Cisco and/or its affiliates.
#
# This software is licensed to you under the terms of the Cisco Sample
# Code License, Version 1.1 (the "License"). You may obtain a copy of the
# License at
#
#                https://developer.cisco.com/docs/licenses
#
# All use of the material herein must be in accordance with the terms of
# the License. All rights not expressly granted by the License are
# reserved. Unless required by applicable law or agreed to separately in
# writing, software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

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
# 5.0 extend to include reactions   FUTURE - NO API yet this will take a while
# 6.0 extend to include mentions    DONE
# 7.0 handle the changing of tokens FUTURE
# 8.0 do something with just files  DONE
# 9.0 score a thread on +/-ve       FUTURE
# 10.0 add check for working hours  DONE


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
from wordcloud import STOPWORDS
from wordcloud import WordCloud
import os
import credentials

WXT_SPACE_ID = credentials.WXT_SPACE_ID
WXT_ACCESS_TOKEN = credentials.WXT_ACCESS_TOKEN
LOGFILE = credentials.LOGFILE
THREAD_TO_BREAK = threading.Event()
INFLUX_DB_PATH = credentials.INFLUX_DB_PATH
ABSOLUTE_PATH = credentials.ABSOLUTE_PATH

WORKING_DAYS = [0, 1, 2, 3, 4]  # 0=Monday, 6=Sunday
WORKING_HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18] # 24 hour clock



def build_word_cloud(image_width=800, image_height=600, wxt_space_id="", words_array=[]):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("build_word_cloud")
    try:
        # data_set_image_variable = []
        # function_logger.debug("made temp array")
        # today_minus_days_variable = str(datetime.datetime.now() + datetime.timedelta(days=-days_of_data))
        # function_logger.debug("time delta calulated")
        # for filename in os.listdir(RESULTS_DIRECTORY):
        #     if ".log" in filename:
        #         full_file = str(RESULTS_DIRECTORY + filename)
        #         f = open(full_file)
        #         for each in f:
        #             timestamp = each.split(" - ")[0]
        #             sku = each.split("#####")[1].replace("\n", "")
        #             if timestamp > today_minus_days_variable:
        #                 data_set_image_variable.append(sku)
        # function_logger.debug("array length variable = " + str(len(data_set_image_variable)))

        def array_to_dict_frequency(array):
            dictionary = {}
            for sku_key in array:
                if dictionary.get(sku_key) is None:
                    dictionary[sku_key] = 1
                else:
                    dictionary[sku_key] += 1
            array_length = len(array)

            for key in dictionary.keys():
                dictionary[key] = dictionary[key] / array_length
            return dictionary

        data_set_image_dict_variable = array_to_dict_frequency(words_array)
        function_logger.debug("array length variable = " + str(len(data_set_image_dict_variable)))

        def create_word_cloud(output_filename, input_dictionary):
            cloud = WordCloud(background_color="black", max_words=100, stopwords=set(STOPWORDS), include_numbers=True,
                              width=image_width, height=image_height)
            cloud.generate_from_frequencies(input_dictionary)
            output_filename = ABSOLUTE_PATH + output_filename + ".png"
            cloud.to_file(output_filename)
            word_cloud_image = cloud.to_image()
            return word_cloud_image
        output_file_name_variable = "word_graphic_" + str(wxt_space_id) + "_" + str(image_width) + "x" + str(image_width)
        return create_word_cloud(output_filename=output_file_name_variable, input_dictionary=data_set_image_dict_variable)
    except Exception as e:
        function_logger.error("something went bad creating WordClouds")
        function_logger.error("Unexpected error:" + str(sys.exc_info()[0]))
        function_logger.error("Unexpected error:" + str(e))
        function_logger.error("TRACEBACK=" + str(traceback.format_exc()))
        # api.messages.create(WXT_ALARMS_BOT_ROOM_ID, text=str("TRACEBACK=%s" % str(traceback.format_exc())))
        return



def check_working_hours(date_time_to_check):
    if date_time_to_check.weekday() in WORKING_DAYS:  # Check to see if posted on weekend
        if date_time_to_check.hour in WORKING_HOURS:  # Check to see if posted during working hours
            return True
        else:
            return False
    else:
        return False


def check_space_for_new_content(last_x_messages=12):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("checking space for new content")
    for each_room in WXT_SPACE_ID:
        words_array = []
        room_url = "https://webexapis.com/v1/rooms/%s" % each_room
        url = "https://webexapis.com/v1/messages?roomId=%s&max=%s" % (each_room, last_x_messages)  # 1000000000
        headers = {"Authorization": "Bearer %s" % WXT_ACCESS_TOKEN}
        room_response = requests.get(url=room_url, headers=headers)
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200 and room_response.status_code == 200:
            json_for_analysis = json.loads(response.text)["items"]
            json_for_room_analysis = json.loads(room_response.text)
            function_logger.debug(json_for_analysis)
            function_logger.debug(json_for_analysis[0])
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
            people_url = "https://webexapis.com/v1/memberships?roomId=%s&max=500" % each_room
            response = requests.get(url=people_url, headers=headers)
            if response.status_code == 200:
                user_json_for_analysis = json.loads(response.text)["items"]
                for each_user in user_json_for_analysis:
                    if not person_dictionary.get(each_user['personId']):
                        person_dictionary[each_user['personId']] = each_user['personEmail']
            influx_string = ""

            for each_message in json_for_analysis:
                polarity = 0
                subjectivity = 0
                positive_words = 0
                neagative_words = 0
                person_email = "N/A"
                timestamp = 0
                timestamp = datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000
                inside_working_hours = check_working_hours(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ"))
                if each_message.get('text'):
                    for word in each_message.get('text'):
                        words_array.append(word)
                    blob = TextBlob(each_message['text'])
                    polarity = blob.polarity
                    subjectivity = blob.subjectivity
                    for each in blob.sentiment_assessments[2]:
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
                        for each in temp_array:
                            thread_position += 1
                            if int(each) == int(datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000):
                                break
                    has_file = 0
                    if each_message.get('files', False):
                        has_file = len(each_message['files'])
                    mentioned_people = 0
                    if each_message.get('mentionedPeople', False):
                        has_file = len(each_message['mentionedPeople'])
                    words = len(blob.words)
                    sentences = len(blob.sentences)
                    impact_words = len(blob.sentiment_assessments[2])
                    if each_message.get('mentionedPeople', False):
                        has_file = len(each_message['mentionedPeople'])
                        for each_mention in each_message['mentionedPeople']:
                            try:
                                influx_string += ('WxTSpaceMentionAnalysis,room_id=%s,room_title="%s",mentionie=%s,mentioner=%s total_mentioned=%s %s \n' %
                                                  (json_for_room_analysis["id"], json_for_room_analysis["title"].replace(" ", "\ "), person_dictionary[each_mention], each_message['personEmail'], len(each_message['mentionedPeople']), str(int(timestamp))))
                            except KeyError as e:
                                function_logger.critical("couldnt find personId = %s" % each_mention)
                elif each_message.get('files'):
                    polarity = 0
                    subjectivity = 0
                    words = 0
                    sentences = 0
                    impact_words = 0
                    is_thread = False
                    thread_size = 0
                    inside_working_hours = check_working_hours(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ"))
                    if thread_dictionary.get(each_message['id'], False):
                        is_thread = True
                        thread_size = len(thread_dictionary[each_message['id']])
                    is_thread_response = False
                    thread_position = 0
                    if each_message.get('parentId', False):
                        is_thread_response = True
                        temp_array = thread_dictionary[each_message['parentId']]
                        temp_array.sort()
                        for each in temp_array:
                            thread_position += 1
                            if int(each) == int(datetime.datetime.timestamp(datetime.datetime.strptime(str(each_message['created']), "%Y-%m-%dT%H:%M:%S.%fZ")) * 1000000000):
                                break
                    has_file = 0
                    if each_message.get('files', False):
                        has_file = len(each_message['files'])
                    mentioned_people = 0
                    if each_message.get('mentionedPeople', False):
                        has_file = len(each_message['mentionedPeople'])
                        for each_mention in each_message['mentionedPeople']:
                            try:
                                influx_string += ('WxTSpaceMentionAnalysis,room_id=%s,room_title="%s",mentionie=%s,mentioner=%s total_mentioned=%s %s \n' %
                                                  (json_for_room_analysis["id"], json_for_room_analysis["title"], person_dictionary[each_mention], each_message['personEmail'], len(each_message['mentionedPeople']), str(int(timestamp))))
                            except KeyError as e:
                                print("couldnt find personId = %s" % each_mention)

                else:
                    polarity = 0
                    subjectivity = 0
                    words = 0
                    sentences = 0
                    impact_words = 0
                    is_thread = False
                    is_thread_response = False
                    thread_position = 0
                    thread_size = 0
                    has_file = 0
                    mentioned_people = 0
                    print("no text or file")
                    print(each_message)
                influx_string += ('WxTSpaceMessageAnalysis,room_id=%s,room_title="%s",'
                                  'personId=%s,is_thread=%s,is_thread_response=%s,thread_position=%s,inside_working_hours=%s '
                                  'polarity=%s,subjectivity=%s,words=%s,sentences=%s,'
                                  'impact_words=%s,positive_words=%s,negative_words=%s,'
                                  'thread_size=%s,attached_files=%s,mentioned_people=%s %s \n') % \
                                 (json_for_room_analysis["id"], json_for_room_analysis["title"].replace(" ", "\ "),
                                  each_message['personEmail'], is_thread, is_thread_response, thread_position, inside_working_hours,
                                  polarity, subjectivity, words, sentences,
                                  impact_words, positive_words, neagative_words,
                                  thread_size, has_file, mentioned_people, str(int(timestamp)))
            update_influx(influx_string)
            build_word_cloud(wxt_space_id=each_room, words_array=words_array)
        else:
            function_logger.critical("something went wrong didnt get status 200 from WxT instead got %s" % response.status_code)
            function_logger.critical("following bad status code content was :- %s" % response.content)


def update_influx(raw_string, timestamp=None):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("updating influx")
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
                    upload_to_influx_sessions_response = upload_to_influx_sessions.post(url=influx_path_url, data=string_to_upload, timeout=(20, 10))
                    if upload_to_influx_sessions_response.status_code == 204:
                        function_logger.debug("content=%s" % upload_to_influx_sessions_response.content)
                        function_logger.info("status_code=%s" % upload_to_influx_sessions_response.status_code)
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

