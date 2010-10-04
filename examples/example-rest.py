#!/usr/bin/env python

import twilio

# Twilio REST API version
API_VERSION = '2010-04-01'

# Twilio AccountSid and AuthToken
ACCOUNT_SID = 'ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
ACCOUNT_TOKEN = 'YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY'

# Outgoing Caller ID previously validated with Twilio
CALLER_ID = 'NNNNNNNNNN';

# Create a Twilio REST account object using your Twilio account ID and token
account = twilio.Account(ACCOUNT_SID, ACCOUNT_TOKEN)

# ===========================================================================
# 1. Initiate a new outbound call to 415-555-1212
#    uses a HTTP POST
try:
    print account.make_call(to_number='415-555-1212', from_number=CALLER_ID, url='http://demo.twilio.com/welcome')
except Exception, e:
    print e
    print e.read()

# ===========================================================================
# 2. Get a list of recent completed calls (i.e. Status = 2)
#    uses a HTTP GET
try:
    print account.get_calls(status='2')
except Exception, e:
    print e
    print e.read()

# ===========================================================================
# 3. Get a list of recent notification log entries
#    uses a HTTP GET
try:
    print account.get_notifications()
except Exception, e:
    print e
    print e.read()

# ===========================================================================
# 4. Get a list of audio recordings for a certain call
#    uses a HTTP GET
try:
    print account.get_recordings(call_sid='CA0c7001f3f3f5063b7f7d96def0f1ed00')
except Exception, e:
    print e
    print e.read()
    
# ===========================================================================
# 5. Delete a specific recording
#    uses a HTTP DELETE, no response is returned when using DELETE
try:
    account.delete_recording(recording_sid='RE4e75a0b62a5c52e5cb96dc25fb4101d9')
except Exception, e:
    print e
    print e.read()
