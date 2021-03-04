# Title
WebEx Teams Space Analysis

# Language
Python 3.9

# Description
This script will take data from one or more WxT spaces and analyse the content for sentiment, subjectivity and
polarity. It will also pick out and count positive/negative words. The tool will then upload this data to an
InfluxDB so that it can be easily displayed graphically.
This script uses TextBlob which makes use of NLTK using some of the most common packages (averaged-tagger, 
brown-corpora, punkt-tokenizer) for sentiment analysis 

# Contacts
Phil Bridges - phbridge@cisco.com

# EULA
This software is provided as is and with zero support level. Support can be purchased by providing Phil bridges with a
varity of Beer, Wine, Steak and Greggs pasties. Please contact phbridge@cisco.com for support costs and arrangements.
Until provison of alcohol or baked goodies your on your own but there is no rocket sciecne involved so dont panic too
much. To accept this EULA you must include the correct flag when running the script. If this script goes crazy wrong and
breaks everything then your also on your own and Phil will not accept any liability of any type or kind. As this script
belongs to Phil and NOT Cisco then Cisco cannot be held responsable for its use or if it goes bad, nor can Cisco make
any profit from this script. Phil can profit from this script but will not assume any liability. Other than the boaring
stuff please enjoy and plagerise as you like (as I have no ways to stop you) but common curtacy says to credit me in some
way [see above comments on Beer, Wine, Steak and Greggs.].

# Version Control               Comments
Version 0.01 Date 28/02/21    Inital draft 

Version 0.02 Date 01/03/21    cleaned up ready for first publish

# ToDo

1.0 pull data from WxT            DONE

2.0 provide some analysis         DONE

3.0 send to Influx                DONE

4.0 Include cloud analysis        FUTURE

5.0 extend to includ reactions    FUTURE - NO API yet this will take a while

6.0 extend to includ mentions     DONE

7.0 handle the changing of tokens FUTURE

8.0 do something with just files  DONE 

9.0 scare a thread on +/-ve       FUTURE
