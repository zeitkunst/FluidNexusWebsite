# This file is part of the Fluid Nexus Website.
# 
# the Fluid Nexus Website is free software: you can redistribute it and/or 
# modify it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
# 
# the Fluid Nexus Website is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with the Fluid Nexus Website.  If not, see 
# <http://www.gnu.org/licenses/>.


import base64, hashlib, os, random, re, time

import Image

from sqlalchemy import desc

from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.i18n import TranslationStringFactory
from pyramid.response import Response
from pyramid.url import route_url
from pyramid.view import view_config

import oauth2

import simplejson

from fluidnexus.models import DBSession
from fluidnexus.models import User, NexusMessage, ConsumerKeySecret, Token, ConsumerNonce


_ = TranslationStringFactory('fluidnexus')

oauth_server = oauth2.Server(signature_methods = {
        'HMAC-SHA1': oauth2.SignatureMethod_HMAC_SHA1()
    })

"""
Working client code:
def build_request(url, method='POST'):
    params = {                                            
        'oauth_version': "1.0",
        'oauth_nonce': oauth2.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_callback': 'fluidnexus://access_token/',
    }
    consumer = oauth2.Consumer(key='33284051511725920213', secret='54302765268137657526')
    params['oauth_consumer_key'] = consumer.key
    req = oauth2.Request(method=method, url=url, parameters=params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, None)
    return req

def build_request(url, message, method="POST"):
    # TODO
    # do we need to add in oauth_callback to be in compliance?
    consumer = oauth2.Consumer(key='33284051511725920213', secret='54302765268137657526')
    params = {}
    params.update(message)
    token = oauth2.Token('70358969944902230656', '64671085584708351586')
    req = oauth2.Request.from_consumer_and_token(consumer, token = token, http_method=method, http_url=url, parameters=params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, token)
    return req
"""

def generateRandomKey(rounds = 20):
    s = ""

    for x in xrange(0, rounds):
        s += str(random.randint(0, 9))

    return s


# TODO
# I shouldn't have to write the serialization code by hand...there should be some way to do this automatically in SA

@view_config(route_name = "api_nexus_messages_json", renderer="json")
def api_nexus_messages(request):
    session = DBSession()
    messages = session.query(NexusMessage).join(User).order_by(desc(NexusMessage.created_time)).all()

    result = {'messages': []}

    for message in messages:
        jsonMessage = {}
        jsonMessage['title'] = message.title
        jsonMessage['content'] = message.content
        jsonMessage['message_hash'] = message.message_hash
        jsonMessage['created_time'] = message.created_time
        jsonMessage['attachment_path'] = message.attachment_path
        jsonMessage['attachment_original_filename'] = message.attachment_original_filename
        jsonMessage["username"] = message.user.username
        result['messages'].append(jsonMessage)

    return result

@view_config(route_name = "api_nexus_messages_hash_json", renderer="json")
def api_nexus_messages_hash(request):
    session = DBSession()
    matchdict = request.matchdict
    message_hash = matchdict["hash"]
    message = NexusMessage.getByMessageHash(message_hash)
    
    if (message is not None):
        result = {"message": {}}
        result["message"]["title"] = message.title
        result["message"]["content"] = message.content
        result["message"]["message_hash"] = message.message_hash
        result["message"]["created_time"] = message.created_time
        result["message"]["attachment_path"] = message.attachment_path
        result["message"]["attachment_original_filename"] = message.attachment_original_filename
        result["message"]["username"] = message.user.username

        return result
    else:
        return {"error": "No message found for hash %s" % message_hash}

@view_config(route_name = "api_nexus_message_nonce", renderer="json", request_method = "POST")
def api_nexus_message_nonce(request):
    session = DBSession()
    auth_header = {}

    if ('Authorization' in request.headers):
        auth_header = {'Authorization': request.headers['Authorization']}
   
    # make temp request to get our header parameters
    req = oauth2.Request.from_request(
        request.method,
        request.url,
        headers = auth_header,
        parameters = dict([(k,v) for k,v in request.params.iteritems()]))

    consumer = ConsumerKeySecret.getByConsumerKey(req.get("oauth_consumer_key"))

    if (consumer is False):
        return {"Error": "No record for the key and secret found."}

    token = Token.getByToken(req.get("oauth_token"))
    if (token is False):
        return {"Error": "No record for the token key and token secret found."}

    req = oauth2.Request.from_consumer_and_token(consumer, 
        token = token, 
        http_method = request.method, 
        http_url = request.url, 
        parameters = dict([(k, v) for k,v in req.iteritems()]))

    try:
        oauth_server.verify_request(req, consumer, token)
    except oauth2.Error, e:
        return {"Oauth error": str(e)}
    except KeyError, e:
        return {"KeyError error": str(e)}
    except Exception, e:
        return {"General error": str(e)}

    nonce = ConsumerNonce()
    nonce.consumer_id = consumer.id
    nonce.timestamp = time.time()
    nonce.nonce = generateRandomKey()
    session.add(nonce)

    return {"nonce": nonce.nonce}

@view_config(route_name = "api_nexus_message_update", renderer="json", request_method = "POST")
def api_nexus_message_update(request):
    # TODO
    # add signed API call to request a nonce
    # and then in this call, check for nonce and for nonce time < 2 hours
    session = DBSession()

    if ("message" not in request.params):
        return {"error": _("No 'message' parameter found")}
    else:
        message = simplejson.loads(request.params["message"], encoding="utf-8")

        # Get the nonce
        try:
            nonce = message["message_nonce"]
        except KeyError:
            return {"error": "You think you can get in without following the rules?  No cookie for you!"}

        # Check the nonce
        if (not ConsumerNonce.checkNonce(nonce)):
            return {"error": "Nonce not correct."}
        
        # Get the consumer key
        consumer = ConsumerKeySecret.getByConsumerKey(message["message_key"])
        if ("message_title" not in message):
            return {"error": _("No 'message_title' found in POSTed message.")}
        elif ("message_content" not in message):
            return {"error": _("No 'message_content' found in POSTed message.")}
        elif ("message_hash" not in message):
            return {"error": _("No 'message_hash' found in POSTed message.")}
        elif ("message_time" not in message):
            return {"error": _("No 'message_time' found in POSTed message.")}
        elif ("message_type" not in message):
            return {"error": _("No 'message_type' found in POSTed message.")}

        computed_hash = hashlib.sha256(unicode(message["message_title"]).encode("utf-8") + unicode(message["message_content"]).encode("utf-8")).hexdigest()

        if (computed_hash != message["message_hash"]):
            return {"error": _("The computed hash (%s) does not match the hash sent with the POST (%s)." % (computed_hash, message["message_hash"]))}

        if (NexusMessage.getByMessageHash(computed_hash)):
            return {"error": "The message with hash '%s' already exists in the Nexus" % message["message_hash"]}


        m = NexusMessage()
        m.title = message["message_title"]

        # Strip any potential HTML tags in the content
        m.content = re.sub(r'<[^>]*?>', '', message["message_content"]) 
        m.message_hash = message["message_hash"]
        m.message_type = message["message_type"]
        m.created_time = message["message_time"]
        m.priority = message["message_priority"]

        if (request.params.has_key("message_attachment")):
            attachment = request.params.get("message_attachment")

            if not hasattr(attachment, 'file'):
                raise TypeError("Not a valid file field")

            attachmentsDir = request.registry.settings["attachments.data_dir"]

            #attachmentDataBase64 = message["message_attachment"]
            #attachmentData = base64.b64decode(attachmentDataBase64)
            message_attachment_path = os.path.join(attachmentsDir, message["message_hash"])
            attachment_original_filename = message["message_attachment_original_filename"]

            fullPath, extension = os.path.splitext(attachment_original_filename)
            fp = open(message_attachment_path + extension, "wb")
            while True:
                data = attachment.file.read(8192)
                if not data:
                    break

                fp.write(data)
            fp.close()

            # Resize if an image
            if (m.message_type == 2):
                size = 200, 200
                try:
                    # Probably needs some validation here...
                    im = Image.open(message_attachment_path + extension)
                    im.thumbnail(size)
                    im.save(message_attachment_path + "_tn" + extension)
                except IOError, e:
                    pass

            m.attachment_original_filename = attachment_original_filename
            m.attachment_path = message_attachment_path
        else:
            m.attachment_path = message.get("message_attachment_path", "")
            m.attachment_original_filename = message.get("message_attachment_original_filename", "")
        m.user_id = consumer.user.id
        session.add(m)

        return {"result": True}


@view_config(route_name = "api_nexus_hashes_json", renderer="json")
def api_nexus_hashes(request):
    session = DBSession()
    hashes = session.query(NexusMessage.message_hash).join(User).order_by(desc(NexusMessage.created_time)).all()

    result = {'hashes': []}

    for message_hash in hashes:
        result['hashes'].append(message_hash[0])

    return result

@view_config(route_name = "api_nexus_hashes_hash_json", renderer="json")
def api_nexus_hashes_hash(request):
    session = DBSession()
    matchdict = request.matchdict
    message_hash = matchdict["hash"]
    message = NexusMessage.getByMessageHash(message_hash)

    if (message is not None):
        return {"result": True}
    else:
        return {"result": False}

@view_config(route_name = "api_request_key", renderer="../templates/api_request_key.pt")
def api_request_key(request):
    session = DBSession()

    if (not request.logged_in):
        request.session.flash(_("You must be registered and logged in to request a consumer key and secret."))
        return HTTPForbidden(location = route_url("home", request))
    
    keySecret = ConsumerKeySecret.getByUserID(request.logged_in)
    if (keySecret):
        key = keySecret.consumer_key
        secret = keySecret.consumer_secret
    else:
        # generate a consumer key and secret
        randomData = hashlib.sha1(str(random.random())).hexdigest()
        keySecret = ConsumerKeySecret()
        key = generateRandomKey()
        secret = generateRandomKey()
        keySecret.consumer_key = key
        keySecret.consumer_secret = secret
        keySecret.user_id = request.logged_in
        keySecret.setNormalStatus()
        session.add(keySecret)

    return dict(key = key, secret = secret, title = _("Fluid Nexus Key and Secret"))

@view_config(route_name = "api_request_token", request_method = "POST")
def api_request_token(request):
    session = DBSession()
    auth_header = {}
    matchdict = request.matchdict
    appType = matchdict.get("appType", False)

    if ('Authorization' in request.headers):
        auth_header = {'Authorization': request.headers['Authorization']}
    
    req = oauth2.Request.from_request(
        request.method,
        request.url,
        headers = auth_header,
        parameters = dict([(k,v) for k,v in request.params.iteritems()]))

    consumer = ConsumerKeySecret.getByConsumerKey(req.get("oauth_consumer_key"))

    #if (request.logged_in != consumer.id):
    #    request.session.flash(_("You are trying to request a token using credentials that do not belong to you."))
    #    return HTTPForbidden(location = route_url("home", request))

    try:
        oauth_server.verify_request(req, consumer, None)

        # Check that this user doesn't already have an access token
        consumerToken = Token.getByConsumerID(consumer.id)
        if consumerToken:
            if (consumerToken.token_type == consumerToken.ACCESS):
                return Response(simplejson.dumps({'result': route_url('api_access_token', request)}))
            elif (consumerToken.token_type == consumerToken.AUTHORIZATION):
                # TODO
                # Check that the token hasn't already expired
                token = oauth2.Token(consumerToken.token, consumerToken.token_secret)
                if (appType == "android"):
                    return Response(token.to_string())
                else:
                    return Response(simplejson.dumps({'result': route_url('api_authorize_token', request, appType = appType) + '?' + token.to_string()}))

        nonce = ConsumerNonce.getByNonce(req.get("oauth_nonce"))
        if (nonce):
            return simplejson.dumps({"error": "Nonce is already registered for an authorization token; please generate another request token, or wait five minutes and try again."})
        else:
            nonce = ConsumerNonce()
            nonce.consumer_id = consumer.id
            nonce.timestamp = req.get("oauth_timestamp")
            nonce.nonce = req.get("oauth_nonce")
            session.add(nonce)

        randomData = hashlib.sha1(str(random.random())).hexdigest()
        key = generateRandomKey()
        secret = generateRandomKey()
        token = oauth2.Token(key, secret)
        token.callback_confirmed = True

        tokenData = Token()
        tokenData.token = key
        tokenData.token_secret = secret
        tokenData.consumer_id = consumer.id
        tokenData.timestamp = time.time()
        tokenData.callback_url = req.get("oauth_callback")
        tokenData.setAuthorizationType()
        session.add(tokenData)

        if (appType == "android"):
            return Response(token.to_string())
        elif (appType == "desktop"):
            result = {'result': route_url('api_authorize_token', request, appType = appType) + '?' + token.to_string()}
            return Response(simplejson.dumps(result))
    except oauth2.Error, e:
        return Response(simplejson.dumps({"oauth2 error": str(e)}))
    except KeyError, e:
        return Response(simplejson.dumps({"keyerror": str(e)}))
    except Exception, e:
        return Response(simplejson.dumps({"general exception error": str(e)}))

@view_config(route_name = "api_authorize_token", request_method = "GET", renderer = "../templates/api_authorize_token.pt")
def api_authorize_token(request):
    session = DBSession()

    matchdict = request.matchdict
    appType = matchdict.get("appType", "")

    # First check that the logged in user is the holder of this token
    token = Token.getByToken(request.params.get("oauth_token"))
    consumer = ConsumerKeySecret.getByConsumerKey(request.params.get("oauth_consumer_key"))


    if (token):
        if (token.consumer_key_secret.user.id != request.logged_in):
            request.session.flash(_("Attempt to use an authorization token that does not belong to you."))
            return HTTPFound(location = route_url("home", request))
    else:
        request.session.flash(_("Malformed authorization token parameters."))
        return HTTPFound(location = route_url("home", request))

    #fs = AuthorizeTokenFieldSet().bind(token, session = session, data = request.POST or None)

    return dict(title = _("Authorization application to post to Nexus"), token = token.token, token_secret = token.token_secret, callback_url = token.callback_url, appType = appType)

@view_config(route_name = "api_do_authorize_token", request_method = "POST")
def api_do_authorize_token(request):
    session = DBSession()

    matchdict = request.matchdict
    appType = matchdict.get("appType", "")

    # First check that the logged in user is the holder of this token
    given_token = request.params.get("token")
    token = Token.getByToken(given_token)
    consumer = ConsumerKeySecret.getByConsumerID(token.consumer_key_secret.id)

    if (not consumer):
        request.session.flash(_("Unable to find consumer key in the database; this should never happen!"))
        return HTTPFound(location = route_url("home", request))

    if (token):
        if (token.consumer_key_secret.user.id != request.logged_in):
            request.session.flash(_("Attempt to use an authorization token that does not belong to you."))
            return HTTPFound(location = route_url("home", request))
    else:
        request.session.flash(_("Malformed authorization token parameters."))
        return HTTPFound(location = route_url("home", request))

    # Generate a new token to replace this now non-useful authorization token
    randomData = hashlib.sha1(str(random.random())).hexdigest()
    key = generateRandomKey()
    secret = generateRandomKey()

    token.token = key
    token.token_secret = secret
    token.consumer_id = consumer.id
    token.timestamp = time.time()
    token.setAccessType()

    if (appType == "android"):
        token.callback_url = token.callback_url + "?oauth_token=%s&oauth_token_secret=%s" % (token.token, token.token_secret)
    session.add(token)

    return HTTPFound(location = token.callback_url)

@view_config(route_name = "api_access_token", renderer = "../templates/access_token.pt")
def api_access_token(request):
    session = DBSession()

    if (not request.logged_in):
        request.session.flash(_("You must be logged in."))
        return HTTPFound(location = route_url("home", request))

    consumer = ConsumerKeySecret.getByUserID(request.logged_in)

    if (not consumer):
        return HTTPFound(location = route_url("api_request_key", request))

    token = Token.getByConsumerID(consumer.id)

    if (not token):
        request.session.flash(_("Attempt to retrieve an access token that does not belong to you."))
        return HTTPFound(location = route_url("home", request))

    return dict(title = _("Your token and token secret"), token = token.token, token_secret = token.token_secret)
