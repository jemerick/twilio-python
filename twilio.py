"""
Copyright (c) 2009 Twilio, Inc.

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__VERSION__ = "2.0.8"

import urllib, urllib2, base64, hmac
from hashlib import sha1
from xml.sax.saxutils import escape, quoteattr

try:
    from google.appengine.api import urlfetch
    APPENGINE = True
except:
    APPENGINE = False
    
try:
    import simplejson as json
except ImportError:
    import json

_TWILIO_API_URL = 'https://api.twilio.com'

class TwilioException(Exception): pass

# Twilio REST Helpers
# ===========================================================================

class HTTPErrorProcessor(urllib2.HTTPErrorProcessor):
    def https_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()
        if code >= 300:
            response = self.parent.error(
                'http', request, response, code, msg, hdrs)
        return response

class HTTPErrorAppEngine(Exception): pass

class TwilioUrlRequest(urllib2.Request):
    def get_method(self):
        if getattr(self, 'http_method', None):
            return self.http_method
        return urllib2.Request.get_method(self)

class Account:
    """Twilio account object that provides helper functions for making
    REST requests to the Twilio API.  This helper library works both in
    standalone python applications using the urllib/urlib2 libraries and
    inside Google App Engine applications using urlfetch.
    """
    def __init__(self, id, token, api_version='2010-04-01'):
        """initialize a twilio account object
        
        id: Twilio account SID/ID
        token: Twilio account token
        
        returns a Twilio account object
        """
        self.id = id
        self.token = token
        self.api_version = api_version
        self.response_format = '.json'
        self.opener = None
    
    def _build_get_uri(self, uri, params):
        if params and len(params) > 0:
            if uri.find('?') > 0:
                if uri[-1] != '&':
                    uri += '&'
                uri = uri + urllib.urlencode(params)
            else:
                uri = uri + '?' + urllib.urlencode(params)
        return uri
    
    def _urllib2_fetch(self, uri, params, method=None):
        # install error processor to handle HTTP 201 response correctly
        if self.opener == None:
            self.opener = urllib2.build_opener(HTTPErrorProcessor)
            urllib2.install_opener(self.opener)
        
        if method and method == 'GET':
            uri = self._build_get_uri(uri, params)
            req = TwilioUrlRequest(uri)
        else:
            req = TwilioUrlRequest(uri, urllib.urlencode(params))
            if method and (method == 'DELETE' or method == 'PUT'):
                req.http_method = method
        
        authstring = base64.encodestring('%s:%s' % (self.id, self.token))
        authstring = authstring.replace('\n', '')
        req.add_header("Authorization", "Basic %s" % authstring)
        
        response = urllib2.urlopen(req)
        return response.read()
    
    def _appengine_fetch(self, uri, params, method):
        if method == 'GET':
            uri = self._build_get_uri(uri, params)
        
        try:
            httpmethod = getattr(urlfetch, method)
        except AttributeError:
            raise NotImplementedError(
                "Google App Engine does not support method '%s'" % method)
        
        authstring = base64.encodestring('%s:%s' % (self.id, self.token))
        authstring = authstring.replace('\n', '')
        r = urlfetch.fetch(url=uri, payload=urllib.urlencode(params),
            method=httpmethod,
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic %s' % authstring})
        if r.status_code >= 300:
            raise HTTPErrorAppEngine("HTTP %s: %s" % \
                (r.status_code, r.content))
        return r.content
    
    def request(self, path, method=None, vars={}):
        """sends a request and gets a response from the Twilio REST API
        
        path: the URL (relative to the endpoint URL, after the /v1
        method: the HTTP method to use, defaults to POST
        vars: for POST, PUT, or GET, a dict of data to send
        
        returns Twilio response in JSON dictionary or raises an exception on error
        """
        if not path or len(path) < 1:
            raise ValueError('Invalid path parameter')
        if method and method not in ['GET', 'POST', 'DELETE', 'PUT']:
            raise NotImplementedError(
                'HTTP %s method not implemented' % method)
        
        if path[0] == '/':
            uri = _TWILIO_API_URL + path + self.response_format
        else:
            uri = _TWILIO_API_URL + '/' + path + self.response_format

        if APPENGINE:
            response = self._appengine_fetch(uri, vars, method)
        else:
            response = self._urllib2_fetch(uri, vars, method)
        
        if response:
            return json.loads(response)
        return None
    
    def get_account(self):
        request_url = '/%s/Accounts/%s' % (self.api_version, self.id)
        return self.request(request_url, 'GET')
        
    def update_account(self, friendly_name):
        request_url = '/%s/Accounts/%s' % (self.api_version, self.id)
        parameters = {'FriendlyName': friendly_name}
        return self.request(request_url, 'POST', parameters)
        
    def available_local_phone_numbers(self, country='US', area_code=None, contains=None, in_region=None, in_postal_code=None, 
                                        near_lat_long=None, near_number=None, in_lata=None, in_rate_center=None, distance=None):
        request_url = '/%s/Accounts/%s/AvailablePhoneNumbers/%s/Local' % (self.api_version, self.id, country)
        parameters = dict()
        if area_code:
            parameters['AreaCode'] = area_code
        if contains:
            parameters['Contains'] = contains
        if in_region:
            parameters['InRegion'] = in_region
        if in_postal_code:
            parameters['InPostalCode'] = in_postal_code
        if near_lat_long:
            parameters['NearLatLong'] = near_lat_long
        if near_number:
            parameters['NearLatLong'] = near_lat_long
        if in_lata:
            parameters['InPostalCode'] = in_postal_code
        if in_rate_center:
            parameters['NearLatLong'] = near_lat_long
        if distance:
            parameters['NearLatLong'] = near_lat_long
        return self.request(request_url, 'GET', parameters)
        
    def available_toll_free_phone_numbers(self, country='US', contains=None):
        request_url = '/%s/Accounts/%s/AvailablePhoneNumbers/%s/TollFree' % (self.api_version, self.id, country)
        parameters = dict()
        if contains:
            parameters['Contains'] = contains
        return self.request(request_url, 'GET', parameters)
        
    def get_incoming_phone_number(self, incoming_phone_number_sid):
        request_url = '/%s/Accounts/%s/IncomingPhoneNumbers/%s' % (self.api_version, self.id, incoming_phone_number_sid)
        return self.request(request_url, 'GET')
        
    def release_incoming_phone_number(self, incoming_phone_number_sid):
        request_url = '/%s/Accounts/%s/IncomingPhoneNumbers/%s' % (self.api_version, self.id, incoming_phone_number_sid)
        return self.request(request_url, 'DELETE')
    
    def update_incoming_phone_number(self, incoming_phone_number_sid, friendly_name=None, api_version=None, voice_url=None, voice_method=None,
                                    voice_fallback_url=None, voice_fallback_method=None, status_callback=None, status_callback_method=None,
                                    sms_url=None, sms_method=None, sms_fallback_url=None, sms_fallback_method=None, voice_caller_id_lookup=None):
        request_url = '/%s/Accounts/%s/IncomingPhoneNumbers/%s' % (self.api_version, self.id, incoming_phone_number_sid)
        parameters = dict()
        
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
        if api_version:
            parameters['ApiVersion'] = api_version
        if voice_url:
            parameters['VoiceUrl'] = voice_url
        if voice_method:
            parameters['VoiceMethod'] = voice_method
        if voice_fallback_url:
            parameters['VoiceFallbackUrl'] = voice_fallback_url
        if voice_fallback_method:
            parameters['VoiceFallbackMethod'] = voice_fallback_method
        if status_callback:
            parameters['StatusCallback'] = status_callback
        if status_callback_method:
            parameters['StatusCallbackMethod'] = status_callback_method
        if sms_url:
            parameters['SmsUrl'] = sms_url
        if sms_method:
            parameters['SmsMethod'] = sms_method
        if sms_fallback_url:
            parameters['SmsFallbackUrl'] = sms_fallback_url
        if sms_fallback_method:
            parameters['SmsFallbackMethod'] = sms_fallback_method
        if voice_caller_id_lookup:
            parameters['VoiceCallerIdLookup'] = voice_caller_id_lookup
        
        return self.request(request_url, 'POST', parameters)
    
    def get_incoming_phone_numbers(self, phone_number=None, friendly_name=None):
        request_url = '/%s/Accounts/%s/IncomingPhoneNumbers' % (self.api_version, self.id)
        
        parameters = dict()
        
        if phone_number:
            parameters['PhoneNumber'] = phone_number
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
        
        return self.request(request_url, 'GET', parameters)
    
    def request_incoming_phone_number(self, phone_number=None, area_code=None, friendly_name=None, api_version=None, voice_url=None, voice_method=None,
                                    voice_fallback_url=None, voice_fallback_method=None, status_callback=None, status_callback_method=None,
                                    sms_url=None, sms_method=None, sms_fallback_url=None, sms_fallback_method=None, voice_caller_id_lookup=None):
        request_url = '/%s/Accounts/%s/IncomingPhoneNumbers' % (self.api_version, self.id)
        
        if not phone_number and not area_code:
            raise TwilioException('PhoneNumber or AreaCode is required.')
        
        # required parameters
        if phone_number:
            parameters['PhoneNumber'] = phone_number
        elif area_code:
            parameters['AreaCode'] = area_code
        
        # optional parameters
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
        if api_version:
            parameters['ApiVersion'] = api_version
        if voice_url:
            parameters['VoiceUrl'] = voice_url
        if voice_method:
            parameters['VoiceMethod'] = voice_method
        if voice_fallback_url:
            parameters['VoiceFallbackUrl'] = voice_fallback_url
        if voice_fallback_method:
            parameters['VoiceFallbackMethod'] = voice_fallback_method
        if status_callback:
            parameters['StatusCallback'] = status_callback
        if status_callback_method:
            parameters['StatusCallbackMethod'] = status_callback_method
        if sms_url:
            parameters['SmsUrl'] = sms_url
        if sms_method:
            parameters['SmsMethod'] = sms_method
        if sms_fallback_url:
            parameters['SmsFallbackUrl'] = sms_fallback_url
        if sms_fallback_method:
            parameters['SmsFallbackMethod'] = sms_fallback_method
        if voice_caller_id_lookup:
            parameters['VoiceCallerIdLookup'] = voice_caller_id_lookup
        
        return self.request(request_url, 'POST', parameters)
        
    def get_outgoing_caller_id(self, outgoing_caller_id_sid):
        request_url = '/%s/Accounts/%s/OutgoingCallerIds/%s' % (self.api_version, self.id, outgoing_caller_id_sid)
        return self.request(request_url, 'GET')
        
    def update_outgoing_caller_id(self, outgoing_caller_id_sid, friendly_name):
        request_url = '/%s/Accounts/%s/OutgoingCallerIds/%s' % (self.api_version, self.id, outgoing_caller_id_sid)
        parameters = {'FriendlyName': friendly_name}
        return self.request(request_url, 'POST', parameters)
    
    def delete_outgoing_caller_id(self, outgoing_caller_id_sid):
        request_url = '/%s/Accounts/%s/OutgoingCallerIds/%s' % (self.api_version, self.id, outgoing_caller_id_sid)
        return self.request(request_url, 'DELETE')
    
    def get_outgoing_caller_ids(self, phone_number=None, friendly_name=None):
        request_url = '/%s/Accounts/%s/OutgoingCallerIds' % (self.api_version, self.id)
        parameters = dict()
        
        if phone_number:
            parameters['PhoneNumber'] = phone_number
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
            
        return self.request(request_url, 'GET', parameters)
        
    def request_outgoing_caller_id(self, phone_number, friendly_name=None, call_delay=None):
        request_url = '/%s/Accounts/%s/OutgoingCallerIds' % (self.api_version, self.id)
        parameters = {'PhoneNumber': phone_number}
        
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
        if call_delay:
            parameters['CallDelay'] = call_delay
            
        return self.request(request_url, 'POST', parameters)
    
    def get_call(self, call_sid):
        request_url = '/%s/Accounts/%s/Calls/%s' % (self.api_version, self.id, call_sid)
        return self.request(request_url, 'GET')
    
    def modify_call(self, call_sid, url=None, method=None, status=None):
        request_url = '/%s/Accounts/%s/Calls/%s' % (self.api_version, self.id, call_sid)
        parameters = dict()
        if url:
            parameters['Url'] = url
        if method:
            parameters['Method'] = method
        if status:
            parameters['Status'] = status
            
        return self.request(request_url, 'POST', parameters)
    
    def get_calls(self, to_number=None, from_number=None, status=None, start_time=None, end_time=None):
        request_url = '/%s/Accounts/%s/Calls' % (self.api_version, self.id)
        parameters = dict()

        if to_number:
            parameters['To'] = to_number
        if from_number:
            parameters['From'] = from_number
        if status:
            parameters['Status'] = status
        if start_time:
            parameters['StartTime'] = start_time
        if end_time:
            parameters['EndTime'] = end_time
            
        return self.request(request_url, 'GET', parameters)
    
    def make_call(self, to_number, from_number, url, method=None, fallback_url=None, fallback_method=None, status_callback=None,
                    status_callback_method=None, send_digits=None, if_machine=None, timeout=None):
                    
        request_url = '/%s/Accounts/%s/Calls' % (self.api_version, self.id)
        parameters = dict()

        if to_number:
            parameters['To'] = to_number
        if from_number:
            parameters['From'] = from_number
        if url:
            parameters['Url'] = url
        if method:
            parameters['Method'] = method
        if fallback_url:
            parameters['FallbackUrl'] = fallback_url
        if fallback_method:
            parameters['FallbackMethod'] = fallback_method
        if status_callback:
            parameters['StatusCallback'] = status_callback
        if status_callback_method:
            parameters['StatusCallbackMethod'] = status_callback_method
        if send_digits:
            parameters['SendDigits'] = send_digits
        if if_machine:
            parameters['IfMachine'] = if_machine
        if timeout:
            parameters['Timeout'] = timeout       
        
        return self.request(request_url, 'POST', parameters)
        
    def get_conference(self, conference_sid):
        request_url = '/%s/Accounts/%s/Conferences/%s' % (self.api_version, self.id, conference_sid)
        return self.request(request_url, 'GET')
        
    def get_conferences(self, status=None, friendly_name=None, date_created=None, date_updated=None):
        request_url = '/%s/Accounts/%s/Conferences/%s' % (self.api_version, self.id, conference_sid)
        parameters = dict()

        if status:
            parameters['Status'] = status
        if friendly_name:
            parameters['FriendlyName'] = friendly_name
        if date_created:
            parameters['DateCreated'] = date_created
        if date_updated:
            parameters['DateUpdated'] = date_updated
            
        return self.request(request_url, 'GET', parameters)
        
    def get_conference_participant(self, conference_sid, call_sid):
        request_url = '/%s/Accounts/%s/Conferences/%s/Participants/%s' % (self.api_version, self.id, conference_sid, call_sid)
        return self.request(request_url, 'GET')
        
    def update_conference_participant(self, conference_sid, call_sid, muted):
        request_url = '/%s/Accounts/%s/Conferences/%s/Participants/%s' % (self.api_version, self.id, conference_sid, call_sid)
        parameters = {'Muted': muted and 'true' or 'false',}
        return self.request(request_url, 'POST', parameters)
    
    def remove_conference_participant(self, conference_sid, call_sid):
        request_url = '/%s/Accounts/%s/Conferences/%s/Participants/%s' % (self.api_version, self.id, conference_sid, call_sid)
        return self.request(request_url, 'DELETE')
    
    def get_conference_participants(self, conference_sid, muted=None):
        request_url = '/%s/Accounts/%s/Conferences/%s/Participants' % (self.api_version, self.id, conference_sid, call_sid)
        parameters = dict()
        if muted is not None:
            parameters['Muted'] = muted and 'true' or 'false'
        return self.request(request_url, 'GET', parameters)
        
    def get_sms_message(self, sms_message_sid):
        request_url = '/%s/Accounts/%s/SMS/Messages/%s' % (self.api_version, self.id, sms_message_sid)
        return self.request(request_url, 'GET')
    
    def get_sms_messages(self, to_number=None, from_number=None, date_sent=None):
        request_url = '/%s/Accounts/%s/SMS/Messages' % (self.api_version, self.id)
        parameters = dict()

        if to_number:
            parameters['To'] = to_number
        if from_number:
            parameters['From'] = from_number
        if date_sent:
            parameters['DateSent'] = date_sent
            
        return self.request(request_url, 'GET', parameters)
        
    def send_sms_message(self, to_number, from_number, body, status_callback=None):
        request_url = '/%s/Accounts/%s/SMS/Messages' % (self.api_version, self.id)
        parameters = {'From': from_number, 'To': to_number, 'Body': body}

        if status_callback:
            parameters['StatusCallback'] = status_callback
            
        return self.request(request_url, 'POST', parameters)
        
    def get_recording(self, recording_sid):
        request_url = '/%s/Accounts/%s/Recordings/%s' % (self.api_version, self.id, recording_sid)
        return self.request(request_url, 'GET')
        
    def get_recording_url(self, recording_sid, mp3=False):
        request_url = '/%s/Accounts/%s/Recordings/%s' % (self.api_version, self.id, recording_sid)
        if mp3:
            request_url += '.mp3'    
        return _TWILIO_API_URL + request_url
    
    def delete_recording(self, recording_sid):
        request_url = '/%s/Accounts/%s/Recordings/%s' % (self.api_version, self.id, recording_sid)
        return self.request(request_url, 'DELETE')

    def get_recordings(self, call_sid=None, date_created=None):
        request_url = '/%s/Accounts/%s/Recordings' % (self.api_version, self.id)
        parameters = dict()
        if call_sid:
            parameters['CallSid'] = call_sid
        if date_created:
            parameters['DateCreated'] = date_created
        return self.request(request_url, 'GET', parameters)
        
    def get_transcription(self, transcription_sid):
        request_url = '/%s/Accounts/%s/Transcriptions/%s' % (self.api_version, self.id, transcription_sid)
        return self.request(request_url, 'GET')
        
    def get_transcriptions(self, recording_sid=None):
        request_url = '/%s/Accounts/%s/Transcriptions' % (self.api_version, self.id)
        if recording_sid:
            request_url = '/%s/Accounts/%s/Recordings/%s/Transcriptions' % (self.api_version, self.id, recording_sid)
        return self.request(request_url, 'GET')
        
    def get_notification(self, notification_sid):
        request_url = '/%s/Accounts/%s/Notifications/%s' % (self.api_version, self.id, notification_sid)
        return self.request(request_url, 'GET')
    
    def delete_notification(self, notification_sid):
        request_url = '/%s/Accounts/%s/Notifications/%s' % (self.api_version, self.id, notification_sid)
        return self.request(request_url, 'DELETE')
        
    def get_notifications(self, call_sid=None, log=None, message_date=None):
        request_url = '/%s/Accounts/%s/Notifications' % (self.api_version, self.id)
        if call_sid:
            request_url = '/%s/Accounts/%s/Calls/%s/Notifications' % (self.api_version, self.id, call_sid)
        
        parameters = dict()
        if log:
            parameters['Log'] = log
        if message_date:
            parameters['MessageDate'] = message_date
        return self.request(request_url, 'GET', parameters)
        
    def get_sandbox(self):
        request_url = '/%s/Accounts/%s/Sandbox' % (self.api_version, self.id)
        return self.request(request_url, 'GET')
    
    def update_sandbox(self, voice_url=None, voice_method=None, sms_url=None, sms_method=None):
        request_url = '/%s/Accounts/%s/Sandbox' % (self.api_version, self.id)
        parameters = dict()
        if voice_url:
            parameters['VoiceUrl'] = voice_url
        if voice_method:
            parameters['VoiceMethod'] = voice_method
        if sms_url:
            parameters['SmsUrl'] = sms_url
        if sms_method:
            parameters['SmsMethod'] = sms_method
            
        return self.request(request_url, 'POST', parameters)
        
# TwiML Response Helpers
# ===========================================================================

class Verb:
    """Twilio basic verb object.
    """
    def __init__(self, **kwargs):
        self.name = self.__class__.__name__
        self.body = None
        self.nestables = None
        
        self.verbs = []
        self.attrs = {}
        for k, v in kwargs.items():
            if k == "sender": k = "from"
            if v: self.attrs[k] = quoteattr(str(v))
    
    def __repr__(self):
        s = '<%s' % self.name
        keys = self.attrs.keys()
        keys.sort()
        for a in keys:
            s += ' %s=%s' % (a, self.attrs[a])
        if self.body or len(self.verbs) > 0:
            s += '>'
            if self.body:
                s += escape(self.body)
            if len(self.verbs) > 0:
                s += '\n'
                for v in self.verbs:
                    for l in str(v)[:-1].split('\n'):
                        s += "\t%s\n" % l
            s += '</%s>\n' % self.name
        else:
            s += '/>\n'
        return s
    
    def append(self, verb):
        if not self.nestables:
            raise TwilioException("%s is not nestable" % self.name)
        if verb.name not in self.nestables:
            raise TwilioException("%s is not nestable inside %s" % \
                (verb.name, self.name))
        self.verbs.append(verb)
        return verb
    
    def asUrl(self):
        return urllib.quote(str(self))
    
    def addSay(self, text, **kwargs):
        return self.append(Say(text, **kwargs))
    
    def addPlay(self, url, **kwargs):
        return self.append(Play(url, **kwargs))
    
    def addPause(self, **kwargs):
        return self.append(Pause(**kwargs))
    
    def addRedirect(self, url=None, **kwargs):
        return self.append(Redirect(url, **kwargs))   
    
    def addHangup(self, **kwargs):
        return self.append(Hangup(**kwargs)) 
    
    def addGather(self, **kwargs):
        return self.append(Gather(**kwargs))
    
    def addNumber(self, number, **kwargs):
        return self.append(Number(number, **kwargs))
    
    def addDial(self, number=None, **kwargs):
        return self.append(Dial(number, **kwargs))
    
    def addRecord(self, **kwargs):
        return self.append(Record(**kwargs))
    
    def addConference(self, name, **kwargs):
        return self.append(Conference(name, **kwargs))
        
    def addSms(self, msg, **kwargs):
        return self.append(Sms(msg, **kwargs))

class Response(Verb):
    """Twilio response object.
    
    version: Twilio API version e.g. 2008-08-01
    """
    def __init__(self, version=None, **kwargs):
        Verb.__init__(self, version=version, **kwargs)
        self.nestables = ['Say', 'Play', 'Gather', 'Record', 'Dial',
            'Redirect', 'Pause', 'Hangup', 'Sms']

class Say(Verb):
    """Say text
    
    text: text to say
    voice: MAN or WOMAN
    language: language to use
    loop: number of times to say this text
    """
    MAN = 'man'
    WOMAN = 'woman'
    
    ENGLISH = 'en'
    SPANISH = 'es'
    FRENCH = 'fr'
    GERMAN = 'de'
    
    def __init__(self, text, voice=None, language=None, loop=None, **kwargs):
        Verb.__init__(self, voice=voice, language=language, loop=loop,
            **kwargs)
        self.body = text
        if voice and (voice != self.MAN and voice != self.WOMAN):
            raise TwilioException( \
                "Invalid Say voice parameter, must be 'man' or 'woman'")
        if language and (language != self.ENGLISH and language != self.SPANISH 
            and language != self.FRENCH and language != self.GERMAN):
            raise TwilioException( \
                "Invalid Say language parameter, must be " + \
                "'en', 'es', 'fr', or 'de'")

class Play(Verb):
    """Play audio file at a URL
    
    url: url of audio file, MIME type on file must be set correctly
    loop: number of time to say this text
    """
    def __init__(self, url, loop=None, **kwargs):
        Verb.__init__(self, loop=loop, **kwargs)
        self.body = url

class Pause(Verb):
    """Pause the call
    
    length: length of pause in seconds
    """
    def __init__(self, length=None, **kwargs):
        Verb.__init__(self, length=length, **kwargs)

class Redirect(Verb):
    """Redirect call flow to another URL
    
    url: redirect url
    """
    GET = 'GET'
    POST = 'POST'
    
    def __init__(self, url=None, method=None, **kwargs):
        Verb.__init__(self, method=method, **kwargs)
        if method and (method != self.GET and method != self.POST):
            raise TwilioException( \
                "Invalid method parameter, must be 'GET' or 'POST'")
        self.body = url

class Hangup(Verb):
    """Hangup the call
    """
    def __init__(self, **kwargs):
        Verb.__init__(self)

class Gather(Verb):
    """Gather digits from the caller's keypad
    
    action: URL to which the digits entered will be sent
    method: submit to 'action' url using GET or POST
    numDigits: how many digits to gather before returning
    timeout: wait for this many seconds before returning
    finishOnKey: key that triggers the end of caller input
    """
    GET = 'GET'
    POST = 'POST'

    def __init__(self, action=None, method=None, numDigits=None, timeout=None,
        finishOnKey=None, **kwargs):
        
        Verb.__init__(self, action=action, method=method,
            numDigits=numDigits, timeout=timeout, finishOnKey=finishOnKey,
            **kwargs)
        if method and (method != self.GET and method != self.POST):
            raise TwilioException( \
                "Invalid method parameter, must be 'GET' or 'POST'")
        self.nestables = ['Say', 'Play', 'Pause']

class Number(Verb):
    """Specify phone number in a nested Dial element.
    
    number: phone number to dial
    sendDigits: key to press after connecting to the number
    """
    def __init__(self, number, sendDigits=None, **kwargs):
        Verb.__init__(self, sendDigits=sendDigits, **kwargs)
        self.body = number

class Sms(Verb):
    """ Send a Sms Message to a phone number
    
    to: whom to send message to, defaults based on the direction of the call
    sender: whom to send message from.
    action: url to request after the message is queued
    method: submit to 'action' url using GET or POST
    statusCallback: url to hit when the message is actually sent
    """
    GET = 'GET'
    POST = 'POST'
    
    def __init__(self, msg, to=None, sender=None, method=None, action=None,
        statusCallback=None, **kwargs):
        Verb.__init__(self, action=action, method=method, to=to, sender=sender,
            statusCallback=statusCallback, **kwargs)
        if method and (method != self.GET and method != self.POST):
            raise TwilioException( \
                "Invalid method parameter, must be GET or POST")
        self.body = msg

class Conference(Verb):
    """Specify conference in a nested Dial element.
    
    name: friendly name of conference 
    muted: keep this participant muted (bool)
    beep: play a beep when this participant enters/leaves (bool)
    startConferenceOnEnter: start conf when this participants joins (bool)
    endConferenceOnExit: end conf when this participants leaves (bool)
    waitUrl: TwiML url that executes before conference starts
    waitMethod: HTTP method for waitUrl GET/POST
    """
    GET = 'GET'
    POST = 'POST'
    
    def __init__(self, name, muted=None, beep=None,
        startConferenceOnEnter=None, endConferenceOnExit=None, waitUrl=None,
        waitMethod=None, **kwargs):
        Verb.__init__(self, muted=muted, beep=beep,
            startConferenceOnEnter=startConferenceOnEnter,
            endConferenceOnExit=endConferenceOnExit, waitUrl=waitUrl,
            waitMethod=waitMethod, **kwargs)
        if waitMethod and (waitMethod != self.GET and waitMethod != self.POST):
            raise TwilioException( \
                "Invalid waitMethod parameter, must be GET or POST")
        self.body = name

class Dial(Verb):
    """Dial another phone number and connect it to this call
    
    action: submit the result of the dial to this URL
    method: submit to 'action' url using GET or POST
    """
    GET = 'GET'
    POST = 'POST'
    
    def __init__(self, number=None, action=None, method=None, **kwargs):
        Verb.__init__(self, action=action, method=method, **kwargs)
        self.nestables = ['Number', 'Conference']
        if number and len(number.split(',')) > 1:
            for n in number.split(','):
                self.append(Number(n.strip()))
        else:
            self.body = number
        if method and (method != self.GET and method != self.POST):
            raise TwilioException( \
                "Invalid method parameter, must be GET or POST")

class Record(Verb):
    """Record audio from caller
    
    action: submit the result of the dial to this URL
    method: submit to 'action' url using GET or POST
    maxLength: maximum number of seconds to record
    timeout: seconds of silence before considering the recording complete
    """
    GET = 'GET'
    POST = 'POST'
    
    def __init__(self, action=None, method=None, maxLength=None, 
        timeout=None, **kwargs):
        Verb.__init__(self, action=action, method=method, maxLength=maxLength,
            timeout=timeout, **kwargs)
        if method and (method != self.GET and method != self.POST):
            raise TwilioException( \
                "Invalid method parameter, must be GET or POST")

class Reject(Verb):
    """Reject an incoming call
    
    reason: message to play when rejecting a call
    """
    REJECTED = 'rejected'
    BUSY = 'busy'
    
    def __init__(self, reason=None, **kwargs):
        Verb.__init__(self, reason=reason, **kwargs)
        if reason and (reason != self.REJECTED and reason != self.BUSY):
            raise TwilioException( \
                "Invalid reason parameter, must be BUSY or REJECTED")

# Twilio Utility function and Request Validation
# ===========================================================================

class Utils:
    def __init__(self, id, token):
        """initialize a twilio utility object
        
        id: Twilio account SID/ID
        token: Twilio account token
        
        returns a Twilio util object
        """
        self.id = id
        self.token = token
    
    def validateRequest(self, uri, postVars, expectedSignature):
        """validate a request from twilio
        
        uri: the full URI that Twilio requested on your server
        postVars: post vars that Twilio sent with the request
        expectedSignature: signature in HTTP X-Twilio-Signature header
        
        returns true if the request passes validation, false if not
        """
        
        # append the POST variables sorted by key to the uri
        s = uri
        if len(postVars) > 0:
            for k, v in sorted(postVars.items()):
                s += k + v
        
        # compute signature and compare signatures
        return (base64.encodestring(hmac.new(self.token, s, sha1).digest()).\
            strip() == expectedSignature)
