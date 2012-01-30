#!/usr/bin/python

from shmooball import app
from flask import render_template, redirect, url_for, session, flash, request, abort
from hashlib import sha256
from redis import Redis
import redis
import json
import time
import logging
import os
## Setup
r = Redis("localhost")
r_hashes = Redis("localhost", port=6379, db=2)
r_comments = Redis("localhost", port=6379, db=3)

logging.basicConfig(filename='/tmp/flask.log', level=logging.DEBUG)

app.logger.debug("starting up")

## app constants
MIN_TRACK = 1
MAX_TRACK = 3
MIN_SECS  = 30
BALL_COUNT = 2
LAST_THROW_SECONDS = 30 ## min seconds required before giving more balls

@app.route('/')
def index():
    if session.has_key('barcode_hash'):
        if is_valid_barcode(session['barcode_hash']):
            # user has a session cookie with a valid barcode hash in it
            return redirect(url_for('track_select'))
        else:
            # user has a session cookie, but it's invalid - delete it and redirect
            session.pop('barcode_hash', None)
            return redirect(url_for('register'))
    else:
        return redirect(url_for('register'))

@app.route('/save_comment/<int:track_num>', methods=['POST'])
def save_comment(track_num):
    if track_num not in [1,2,3]:
        return "LAME"

    try:
        comment = request.form['comment'][:140]
    except:
        return redirect(url_for('track_select'))

    track_var = "%s:track" % track_num

    comment_id  = r_comments.incr(track_var)
    comment_var = "comment:track:%s:%s" % (track_num, comment_id)
    time_var    = "comment:track:%s:%s:time" % (track_num, comment_id)

    r_comments.set(comment_var, comment)
    r_comments.set(time_var, int(time.time()))

    return redirect(url_for('track_select'))

def get_last_five(track_num):
    try:
	    track_var = "%s:track" % track_num

            try:
	        max_comment_id = int(r_comments.get(track_var))
            except:
                app.logger.debug("comment_id is fubar")
                max_comment_id = 0

	    comment_list = []

	    for comment in xrange(max_comment_id, max_comment_id-5, -1):
		comment_var = "comment:track:%s:%s" % (track_num, comment)

		try:
		    comment_list.append(r_comments.get(comment_var))
		except:
		    pass
	    
	    return comment_list
    except Exception, e:
        app.logger.debug("Exception is %s" % e)
        return []
    

@app.route('/register', methods=['POST', 'GET'])
def register():
    if check_auth():
        return redirect(url_for('track_select'))

    if request.method == "GET":
        # display the registration page if user
       return render_template('login.html') 
    elif request.method == "POST":
        # process registration request
        if request.form['nick'] and request.form['barcode']:
            # make sure a barcode and a nick were submitted
            barcode_hash = sha256(request.form['barcode']).hexdigest()

            # check to make sure sha256 shows a valid barcode.
            if is_valid_barcode(barcode_hash):
                # Barcode is valid, register this browser

                # Set the nick name, new user or returning
                set_nickname(barcode_hash, request.form['nick'])
                
                # set the barcode hash in session for quick reference
                session['barcode_hash'] = barcode_hash
                # Figure out if user is returning or not
                if is_registered(barcode_hash):
                    # barcode has already been used to register
                    app.logger.debug("%s:%s seen again time" % (barcode_hash, request.form['nick']))
                    return redirect(url_for('track_select'))
                else:
                    # barcode has never been used before
                    app.logger.debug("%s:%s seen for first time" % (barcode_hash, request.form['nick']))

                    # mark barcode as having been used
                    set_registered_already(barcode_hash)

                    # set initial ball count
                    set_ballcount(barcode_hash)

                    return redirect(url_for('track_select'))


            else:
                flash("Invalid barcode supplied, please check your text and try again!")
                app.logger.debug("register got invalid barcode, retrying form")
                return redirect(url_for('register'))
        else:
            flash("Please provide both a barcode and a nickname.")
            app.logger.debug("register got missing nick/barcode - retrying form")
            return redirect(url_for('register'))

@app.route('/track')
def track_select():
    if check_auth():
        return render_template('track_select.html')
    else:
        return redirect(url_for('index'))


@app.route('/throw/<int:track_num>', methods=['GET'])
def confirm_throw(track_num):
    if check_auth():
        if track_num in [1,2,3]:
            balls_in_flight = 0
            try:
                balls_in_flight = int(r.get('%s:ballcount' % track_num))
            except:
                balls_in_flight = 0

            app.logger.debug("balls in flight track %s is %s" % (track_num, balls_in_flight))
            if balls_in_flight > 20:
                moose_status = "MOOSE RAMPAGE!@#"
            elif balls_in_flight > 10:
                moose_status = "Moose is concerned"
            elif balls_in_flight > 5:
                moose_status = "Moose is suspicious"
            elif balls_in_flight > 0:
                moose_status = "Moose is curious"
            else:
                moose_status = "Moose is happy!"

            comments = get_last_five(track_num)
            #comments = []
                
            return render_template('confirm_throw2.html', track_num=track_num, balls_in_flight=balls_in_flight, moose_status=moose_status, comments=comments)
        else:
            return 'SAY WUT'
    else:
        return redirect(url_for('index'))

@app.route('/throw/<int:track_num>', methods=['POST'])
def throw(track_num):
   if check_auth():
        if track_num in [1,2,3]:
            if throw_ball(track_num):
                return render_template('post_throw.html', track_num=track_num)
            else:
                return render_template('no_balls.html', track_num=track_num)
   else:
        return redirect(url_for('index'))

###############    
@app.route('/status/<int:track_num>/')
def status(track_num):
    return json.dumps(
             {'track:%d' % track_num: r.get('balls:%d' % track_num)}
           )
###############

@app.route('/logout')
def logout():
    session.pop('barcode_hash', None)
    return redirect(url_for('index'), code = 301)

@app.errorhandler(404)
def not_found(error):
    app.logger.debug("Got a 404 here: %s", request.environ['PATH_INFO'])
    #return str(request.environ)
    #return redirect('/')
    #return redirect(url_for('index'), 404)
    return "FOUR OH FOUR"

@app.route('/dohonk/<int:track>')
def dohonk(track):
    honk_variable = "%s:honk_action" % track
    r.set(honk_variable, 1) 
    return "Honk mode set."

################################################################################
def is_valid_barcode(barcode_hash):
    if r_hashes.keys(barcode_hash):
        return True
    else:
        return False

def check_auth():
    if session.has_key('barcode_hash'):
        if is_valid_barcode(session['barcode_hash']):
            return True
        else:
            app.logger.debug("invalid barcode is invalid")
            return False
    else:
        app.logger.debug("no session key")
        return False

def is_registered(barcode_hash):
    key = "%s:registered_already" % barcode_hash
    if r_hashes.get(key):
        return True 
    else:
        return False

def set_nickname(barcode_hash, nickname):
    key = "%s:nickname" % barcode_hash
    r_hashes.set(key, nickname)
    session['nick'] = nickname
    return True

def set_ballcount(barcode_hash):
    key = "%s:ballcount" % barcode_hash
    r_hashes.set(key, BALL_COUNT)
    return True    

def set_registered_already(barcode_hash):
    key = "%s:registered_already" % barcode_hash
    r_hashes.set(key, True)
    return True

def throw_ball(track_num):
    usercount_key = "%s:ballcount" % session['barcode_hash']
    last_throw_key = "%s:last_throw" % session['barcode_hash']

    last_throw_time = r_hashes.get(last_throw_key)

    if not last_throw_time: last_throw_time = time.time()
    last_throw_delta = float(time.time()) - float(last_throw_time)
    r_hashes.set(last_throw_key, last_throw_time)

    app.logger.debug("Last throw time for user %s is %s seconds", session['barcode_hash'], last_throw_delta)

    if int(r_hashes.get(usercount_key)) == 0 and last_throw_delta > LAST_THROW_SECONDS:
        ## check last throw time, if greater than threshold, replenish
        ## balls
        app.logger.debug("Adding balls for user %s" % session['barcode_hash'])
        set_ballcount(session['barcode_hash'])
    else:
        app.logger.debug("Not adding balls for user %s" % session['barcode_hash'])

    if int(r_hashes.get(usercount_key)) > 0:
        # user has balls left, throw one
        # decrement user's ballcount
        r_hashes.decr(usercount_key)
        r_hashes.set(last_throw_key, time.time())
        
        # increment talk's ballcount (create it if doesn't already exist)
        track_ball_count_key = "%s:ballcount" % track_num
        throws_since_last_poll = "%s:throws" % track_num
        try:
            r.incr(track_ball_count_key)
            r.incr(throws_since_last_poll)
        except redis.exceptions.ResponseError:
            r.set(track_ball_count_key, 1)
            r.set(throws_since_last_poll, 0)

        return True
    else:
        # user has no balls left, error out
        # if last_throw was > some seconds ago, reload
        return False

@app.route('/throw2/<int:track_num>', methods=['GET'])
def confirm_throw2(track_num):
    if check_auth():
        if track_num in [1,2,3]:
            balls_in_flight = 0
            try:
                balls_in_flight = int(r.get('%s:ballcount' % track_num))
            except:
                balls_in_flight = 0

            app.logger.debug("balls in flight track %s is %s" % (track_num, balls_in_flight))
            if balls_in_flight > 20:
                moose_status = "MOOSE RAMPAGE!@#"
            elif balls_in_flight > 10:
                moose_status = "Moose is concerned"
            elif balls_in_flight > 5:
                moose_status = "Moose is suspicious"
            elif balls_in_flight > 0:
                moose_status = "Moose is curious"
            else:
                moose_status = "Moose is happy!"
                
            return render_template('confirm_throw2.html', track_num=track_num, balls_in_flight=balls_in_flight, moose_status=moose_status)
        else:
            return 'SAY WUT'
    else:
        return redirect(url_for('index'))
