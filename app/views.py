import flask
from facebook import get_user_from_cookie, GraphAPI
from flask import Flask, g, render_template, redirect, request, session, url_for
from flaskext.mysql import MySQL
import flask_login as flask_login
import datetime
import operator
import facebook

#for image uploading
from werkzeug import secure_filename
import os, base64

import networkx as nx
import matplotlib.pyplot as plt

from keys import *
#from app import app

mysql = MySQL()
app = Flask(__name__)

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'mynewpass'
app.config['MYSQL_DATABASE_DB'] = 'whoogle'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()

# Facebook app details
import tweepy
import requests
from watson_developer_cloud import AlchemyLanguageV1
import json

class TwitterHelper(object):
	def __init__(self):
		"""
		input: none
		self.api: access to twitterAPI
		self.alchemy_language: access to AlchemyAPI
		"""
		# authentication
		self.auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
		self.auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
		# twitter api
		self.api = tweepy.API(self.auth)
		# alchemy api
		self.alchemy_language = AlchemyLanguageV1(api_key=ALCHEMY_KEY)

	def getFollowers(self, twitter_handle):
		"""
		input: twitter handle
		output: list of twitter followers for the specified handle
		"""
		followers = []
		for follower in tweepy.Cursor(self.api.followers, screen_name=twitter_handle).items():
			followers.append(follower.name)
		return followers	

	def getFollowees(self, twitter_handle):
		"""
		input: twitter handle
		output: list of people following the person specified by the handle
		"""
		friends = []
		for friend in tweepy.Cursor(self.api.friends, screen_name=twitter_handle).items():
			friends.append(friend.name)
		return friends

	def TweetSentAnalysis(self, twitter_handle, max_items=10):
		""" gets sentiment analysis on last 3200 tweets of user
		input: max_items - the number of entities to extract from all posts of the searched person
		output: json holding information about sentiment and emotions associated with the entities (10 by default)
		"""
		# get twitter data
		data = self.getTimelineAndRetweets(twitter_handle)
		# perform sentiment analysis
		raw = json.loads(self.performSentimentAnalysis(data))
		return self.stripOutput(raw)


	def searchUsers(self, query):
		""" searches for users
		input: query
		output: stripped json with relevant information
		"""
		relevant_keys = ['name', 'screen_name', 'location', 'profile_image_url', 'description', 'followers_count']
		# maximum of 20 users can be displayed
		full_dict = self.api.search_users(q=query)
		ret = []
		for i in range(len(full_dict)):
			temp_dict = {}
			temp_dict['name'] = full_dict[i].name
			temp_dict['screen_name'] = full_dict[i].screen_name
			temp_dict['location'] = full_dict[i].location
			temp_dict['profile_image_url'] = full_dict[i].profile_image_url
			temp_dict['description'] = full_dict[i].description
			temp_dict['followers_count'] = full_dict[i].followers_count
			ret.append(temp_dict)
		return ret

	def stripOutput(self, raw):
		"""
		helper function
		"""
		ret = []
		# strip/format the raw response
		for entity in raw['entities']:
			stripped_entitity = {}
			stripped_entitity['text'] = entity['text']
			max_emotion = max(entity['emotions'].iteritems(), key=operator.itemgetter(1))
			stripped_entitity['emotion'] = {'type': max_emotion[0], 'value': max_emotion[1]}
			ret.append(stripped_entitity)
		return ret

	def getTimelineAndRetweets(self, screen_name):
		"""
		helper function
		"""
		rawTweets = ''
		for status in tweepy.Cursor(self.api.user_timeline, screen_name=screen_name, count=200).items():
			# process status here
			if status.text[-1] not in ['!', '?', '.']:
				status.text += '.'
			status.text += '\n'
			rawTweets += status.text
		return rawTweets

	def performSentimentAnalysis(self, text, max_items=10):
		"""
		helper function
		"""
		return json.dumps(
		  self.alchemy_language.entities(
		    text=text,
		    sentiment=1,
			emotion=1,
			linked_data=0,
			disambiguate=0,
		    max_items=max_items),
		  indent=2)
		  

class FacebookHelper(object):
	def __init__(self, access_token):
		"""
		input: facebook access token
		graph is access to facebook api
		alchemy_language is access to alchemy api
		"""
		self.access_token = access_token
		self.graph = facebook.GraphAPI(access_token)
		self.alchemy_language = AlchemyLanguageV1(api_key=ALCHEMY_KEY)

	def getBasicInfo(self):
		"""
		output: basic info on ego user
		"""
		return self.graph.get_object('me?fields=name,picture{url},about,education,location')

	def FBSentAnalysis(self, max_items=10):
		"""
		input: max_items - the number of entities to extract from all status updates of the user
		output: json holding information about sentiment and emotions associated with the entities
		"""
		# get FB data
		rawStatusUpdateString = ''
		page = self.graph.get_object('me/posts')
		while len(page['data']) != 0:
			for post in page['data']:
				try:
					statusUpdate = post['message']
					if statusUpdate[-1] not in ['!', '?', '.']:
						statusUpdate += '.'
					statusUpdate += '\n'
					rawStatusUpdateString += statusUpdate
				except Exception as e:
					pass
			page = requests.get(page['paging']['next']).json()
		# perform sentiment on all of the status updates
		raw = self.performSentimentAnalysis(rawStatusUpdateString, max_items)
		# strips the output and returns it
		return self.stripOutput(raw)

	def stripOutput(self, raw):
		ret = []
		# strip/format the raw response
		for entity in raw['entities']:
			stripped_entitity = {}
			stripped_entitity['text'] = entity['text']
			max_emotion = max(entity['emotions'].iteritems(), key=operator.itemgetter(1))
			stripped_entitity['emotion'] = {'type': max_emotion[0], 'value': max_emotion[1]}
			ret.append(stripped_entitity)
		return ret

	def performSentimentAnalysis(self, text, max_items=10):
		"""
		input: text to analyze
		output: json holding analysis of entities
		"""
		return self.alchemy_language.entities(
		    text=text,
			emotion=1,
			linked_data=0,
			disambiguate=0,
		    max_items=max_items)
			
			
def getGraph(egoUser):
	followers = TwitterHelper().getFollowers(egoUser)
	followees = TwitterHelper().getFollowees(egoUser)

	DG = nx.DiGraph()
	e_followers = [(egoUser, f) for f in followers]

	filtered_followees = [t for t in followees if t in followers]
	e_followees = [(t, egoUser) for t in filtered_followees]

	DG.add_edges_from(e_followers, color = 'blue')
	DG.add_edges_from(e_followees, color = 'red')

	labels = {}
	for node in DG.nodes():
	    labels[node] = node

	pos=nx.spring_layout(DG)

	nx.draw_networkx_nodes(DG, pos, nodelist = followers, node_color = 'b')
	nx.draw_networkx_nodes(DG, pos, nodelist = [egoUser], node_color = 'r')

	nx.draw_networkx_edges(DG, pos, edgelist = e_followers, edge_color = 'b', arrows = True)
	nx.draw_networkx_edges(DG, pos, edgelist = e_followees, edge_color = 'r', arrows = True)

	nx.draw_networkx_labels(DG, pos, labels)
	plt.axis('off')
	plt.savefig('maps/'+egoUser+'_relationship_map.png')

			

@app.route('/')
def index():
    # If a user was set in the get_current_user function before the request,
    # the user is logged in.
    #print(g.user)
    #if g.user:
		#return render_template('search.html')
      #  return render_template('index.html', app_id=FB_APP_ID,
       #                        app_name=FB_APP_NAME, user=g.user)
    # Otherwise, a user is not logged in.
    return render_template('login.html', app_id=FB_APP_ID, name=FB_APP_NAME)


@app.route("/search", methods=['GET', 'POST'])
def search():
	if request.method == 'POST':
		input_name = request.form.get('search')
		#return render_template('search.html', name)
		return results(input_name)
	else:
		return render_template('search.html')
	#search=request.form.get('searchterm')
	
#@app.route("/results", methods=['GET','POST'])
def results(input_name):
	helper = TwitterHelper()
	returned = helper.searchUsers(input_name)
	return render_template('results.html', search = returned)
	#return render_template('results.html', search = input_name)
	
	
@app.route("/profile/<string:handle>", methods=['GET'])
def profile(handle):
    helper = TwitterHelper()
    returned = helper.searchUsers(handle)
    tsentiment = helper.TweetSentAnalysis(handle)
    return render_template('profile.html', profile = returned[0], usersentiment = tsentiment, h = handle)
	
	
@app.route("/fb", methods=['GET'])
def fb():
    helper = FacebookHelper('EAAZAx4mZAxoJkBAETkEtzNZAXagGiRnm8RfGWMmCxVLQt3HeZBnq8snABZACdiSh8oDD8ZC44UcmkwyVLMnaV0qwR9Hng4noWWmmHm356PgkmguBQshXprRLyRRgjdLoYpreKK7PfKNtQnkZBt30dE9JgwgCuWiTazZAtZCf2KIzPkwZDZD') ##need to put the key in here!!
    returned2 = helper.getBasicInfo()
    fbsentiment = helper.FBSentAnalysis()
    return render_template('fbprofile.html', profile = returned2, usersentiment = fbsentiment)
	
@app.route("/map/<string:handle>", methods=['GET', 'POST'])	
def map(handle):
	map = returnmap(handle)
	return render_template('map.html', handle = handle, map = map)

def returnmap(handle):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(*) FROM (Maps M) WHERE M.handle_id = '{0}'".format(handle))
	count = cursor.fetchone()[0]
	if (count == 1):
		cursor.execute("SELECT M.date_of_creation FROM (Maps M) WHERE M.handle_id = '{0}'".format(handle))
		date = cursor.fetchone()[0]
		days = datetime.date.today() - date
		print(days.days)
		if ( days.days < 7):
			cursor.execute("SELECT M.mapdata FROM (Maps M) WHERE M.handle_id = '{0}'".format(handle))
			map = cursor.fetchone()[0]
			return map
		else:
			cursor.execute("DELETE FROM (MAPS M) WHERE M.handle_id = '{0}'".format(handle))
	getGraph(handle)
	photo_data = base64.b64encode(open("maps/"+handle+"_relationship_map.png", "rb").read())
	cursor.execute("INSERT INTO MAPS (handle_id, mapdata, date_of_creation) VALUES ('{0}', '{1}', '{2}')".format(handle, photo_data, datetime.datetime.today().strftime('%Y-%m-%d')))
	cursor.execute("SELECT M.mapdata FROM (Maps M) WHERE M.handle_id = '{0}'".format(handle))
	map = cursor.fetchone()[0]
	conn.commit()
	return map