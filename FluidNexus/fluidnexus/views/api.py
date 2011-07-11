from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden
from pyramid.i18n import TranslationStringFactory
from pyramid.url import route_url
from pyramid.view import view_config

from formalchemy import types, Field, FieldSet, Grid

import oauth2

from fluidnexus.models import DBSession
from fluidnexus.models import User, NexusMessage, ConsumerKeySecret, Token, ConsumerNonce
from fluidnexus.forms import AuthorizeTokenFieldSet

import hashlib, random, time
import simplejson

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
    consumer = oauth2.Consumer(key='b9085cb942dc427c92dd', secret='1735fd5b090381dcaf57')
    params['oauth_consumer_key'] = consumer.key
    req = oauth2.Request(method=method, url=url, parameters=params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, None)
    return req

# Not quite working, for some reason...
def build_request(url, message, method="POST"):
    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauth2.generate_nonce(),
        'oauth_timestamp': str(int(time.time())),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_callback': 'fluidnexus://access_token/',
    }
    consumer = oauth2.Consumer(key='b9085cb942dc427c92dd', secret='1735fd5b090381dcaf57')
    params['oauth_consumer_key'] = consumer.key
    #params.update(message)
    token = oauth2.Token('b1735523a92a064fb6fd', 'e455b92259b6e5dc0163')
    req = oauth2.Request.from_consumer_and_token(consumer, token = token, http_method=method, http_url=url, parameters=params)
    #req = oauth2.Request(method = "POST", url = url, parameters = params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, token)
    return req
"""

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

@view_config(route_name = "api_nexus_message_update", renderer="json", request_method = "POST")
def api_nexus_message_update(request):
    """TODO
    add oauth"""

    session = DBSession()

    auth_header = {}
    if ('Authorization' in request.headers):
        auth_header = {'Authorization': request.headers['Authorization']}
    
    consumer = ConsumerKeySecret.getByConsumerKey(request.params.get("oauth_consumer_key"))
    token = Token.getByToken(request.params.get("oauth_token"))
    
    req = oauth2.Request.from_consumer_and_token(consumer, 
        token = token, 
        http_method = request.method, 
        http_url = request.url, 
        parameters = dict([(k, v) for k,v in request.params.iteritems()]))

    try:
        oauth_server.verify_request(req, consumer, token)
    except oauth2.Error, e:
        print e
        return simplejson.dumps({"error": e})
    except KeyError, e:
        print e
        return simplejson.dumps({"error": e})
    except Exception, e:
        print e
        return simplejson.dumps({"error": e})


    if ("message" not in request.params):
        return {"error": _("No 'message' parameter found")}
    else:
        message = simplejson.loads(request.params["message"])

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

        computed_hash = hashlib.sha256(message["message_title"] + message["message_content"]).hexdigest()

        if (computed_hash != message["message_hash"]):
            return {"error": _("The computed hash (%s) does not match the hash sent with the POST (%s)." % (computed_hash, message["message_hash"]))}

        if (NexusMessage.getByMessageHash(computed_hash)):
            return {"error": "The message with hash '%s' already exists in the Nexus" % message["message_hash"]}


        # TODO
        # make user based on user_id attached to this oauth token
        m = NexusMessage()
        m.title = message["message_title"]
        m.content = message["message_content"]
        m.message_hash = message["message_hash"]
        m.message_type = message["message_type"]
        m.created_time = message["message_time"]
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
        key = randomData[0:20]
        secret = randomData[20:]
        keySecret.consumer_key = key
        keySecret.consumer_secret = secret
        keySecret.user_id = request.logged_in
        keySecret.setNormalStatus()
        session.add(keySecret)

    return dict(key = key, secret = secret, title = _("Consumer Key and Secret"))

@view_config(route_name = "api_request_token", request_method = "POST", renderer = "json")
def api_request_token(request):
    session = DBSession()
    auth_header = {}
    if ('Authorization' in request.headers):
        auth_header = {'Authorization': request.headers['Authorization']}
    
    req = oauth2.Request.from_request(
        request.method,
        request.url,
        headers = auth_header,
        parameters = dict([(k,v) for k,v in request.params.iteritems()]))

    consumer = ConsumerKeySecret.getByConsumerKey(request.params.get("oauth_consumer_key"))

    #if (request.logged_in != consumer.id):
    #    request.session.flash(_("You are trying to request a token using credentials that do not belong to you."))
    #    return HTTPForbidden(location = route_url("home", request))

    try:
        oauth_server.verify_request(req, consumer, None)

        nonce = ConsumerNonce.getByNonce(request.params.get("oauth_nonce"))
        if (nonce):
            return simplejson.dumps({"error": "Nonce is already registered for an authorization token; please generate another request token, or wait five minutes and try again."})
        else:
            nonce = ConsumerNonce()
            nonce.consumer_id = consumer.id
            nonce.timestamp = request.params.get("oauth_timestamp")
            nonce.nonce = request.params.get("oauth_nonce")
            session.add(nonce)

        randomData = hashlib.sha1(str(random.random())).hexdigest()
        key = randomData[0:20]
        secret = randomData[20:]
        token = oauth2.Token(key, secret)
        token.callback_confirmed = True

        tokenData = Token()
        tokenData.token = key
        tokenData.token_secret = secret
        tokenData.consumer_id = consumer.id
        tokenData.callback_url = request.params.get("oauth_callback")
        tokenData.setAuthorizationType()
        session.add(tokenData)

        return simplejson.dumps({"result": route_url("api_authorize_token", request) + "?" + token.to_string()})
    except oauth2.Error, e:
        return simplejson.dumps({"error": e})
    except KeyError, e:
        return simplejson.dumps({"error": e})
    except Exception, e:
        return simplejson.dumps({"error": e})

@view_config(route_name = "api_authorize_token", request_method = "GET", renderer = "../templates/api_authorize_token.pt")
def api_authorize_token(request):
    session = DBSession()

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

    return dict(title = _("Authorization application to post to Nexus"), token = token.token, token_secret = token.token_secret, callback_url = token.callback_url)

@view_config(route_name = "api_do_authorize_token", request_method = "POST")
def api_do_authorize_token(request):
    session = DBSession()

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
    key = randomData[0:20]
    secret = randomData[20:]

    token.token = key
    token.token_secret = secret
    token.consumer_id = consumer.id
    callback_url = token.callback_url + "?oauth_token=%s&oauth_token_secret=%s" % (key, secret)
    token.callback_url = callback_url
    token.setAccessType()
    session.add(token)

    return HTTPFound(location = callback_url)
