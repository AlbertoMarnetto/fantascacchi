######################################
import json

def load_participants(filename):
	with open(filename, "r") as file:
		data = json.load(file)
		return data

	# S. also https://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object

######################################

import sys

def rawwrite(string):
	sys.stdout.buffer.write(string.encode("utf-8"))

##############################################

import re as re
from collections import namedtuple

from bs4 import BeautifulSoup

def load_posts(filename):
	html_page = open(filename, "rb").read().decode('utf-8', 'ignore')
	soup = BeautifulSoup(html_page, "html.parser")
	post_tags = soup.find_all('li', attrs={'class': re.compile('comment byuser.*')})

	posts = []

	for post_tag in post_tags:
		comment_author_class = [ post_tag_class for post_tag_class in post_tag['class'] if post_tag_class.startswith('comment-author-') ]

		if len(comment_author_class) != 1:
			continue

		post_author = comment_author_class[0].replace('comment-author-', '', 1)

		post_text = post_tag.find('div', attrs = {'class': 'info_com'}).text

		#print(post_text)

		post = { 'author' : post_author, 'text' : post_text}
		posts.append(post)

	return posts

##############################################

import re as re
from collections import namedtuple
from operator import itemgetter

from bs4 import BeautifulSoup

def process_line(line, participants):
	participants_in_line = []

	# Find participants
	for participant in participants:
		idx = line.find(participant)
		if idx != -1:
			participants_in_line.append((participant, idx))
		else:
			participant_tokens = participant.split()
			for participant_token in participant_tokens:
				idx = line.find(participant_token)
				if idx != -1:
					participants_in_line.append((participant, idx))

	# Find result
	line_outcome = '?'
	for outcome_re, outcome in process_line.possible_outcomes:
		if outcome_re.search(line):
			line_outcome = outcome
			break
		#else:
		#	print('%s does not match %s' % (line, outcome))

	if len(participants_in_line) == 2:
		participants_in_line.sort(key = itemgetter(1))
		return (participants_in_line[0], participants_in_line[1], line_outcome)
	else:
		return None


# In descending order of reliability,
# e.g. "0 - 1" matches both the 2nd and the 6th regexp,
# but the former has priority
process_line.possible_outcomes = [
		(re.compile("\D1\s*[-–\\\/]\s*0($|\D)"), '1'), # 1 - 0
		(re.compile("\D0\s*[-–\\\/]\s*1($|\D)"), '2'), # 0 - 1
		(re.compile("\D½\s*[-–\\\/]\s*½($|\D)"), 'X'), # ½ - ½
		(re.compile("\D1[\\\/]2($|\D)"), 'X'), # 1/2
		(re.compile("\s[xX]($|\s)"), 'X'), # X
		(re.compile("\D1($|\D)"), '1'), # 1
		(re.compile("\D2($|\D)"), '2') # 2
		]

##############################################

def extract_predictions(post_text, participants):
	lines = post_text.split('\n')

	post_predictions = {}
	post_predictions['count'] = 0
	post_predictions['predictions'] = []

	for line in lines:
		line_prediction = process_line(line, participants)
		if not line_prediction is None:
			post_predictions['count'] += 1
			prediction = (line_prediction[0][0], line_prediction[1][0], line_prediction[2])
			post_predictions['predictions'].append(prediction)

	return post_predictions

##############################################

def assign_points(post_predictions, tournament_outcome):
	post_predictions['score'] = 0
	for prediction in post_predictions['predictions']:
		if prediction in tournament_outcome['predictions']:
			post_predictions['score'] += 1
			
	return post_predictions

##############################################

participants = load_participants('participants.json')
#print(participants)

tournament_text = open('tournament.txt', "rb").read().decode('utf-8', 'ignore')
tournament_outcome = extract_predictions(tournament_text, participants)

posts = load_posts('thread.html')
#sys.stdout.buffer.write(b'\ufeff')
print(len(posts))

post_predictions_list = []
for post in posts:
	post_predictions = extract_predictions(post['text'], participants)
	post_predictions = assign_points(post_predictions, tournament_outcome)
	post_predictions['author'] = post['author']
	post_predictions_list.append(post_predictions)
	rawwrite('--------------------------------\n')
	rawwrite(post['author'])
	rawwrite(post['text'])
	rawwrite('\n')
	rawwrite("%d: %s\n" % (post_predictions['count'], post_predictions['predictions']))
	rawwrite("Score: %d\n" % post_predictions['score'])
	rawwrite('\n')
	rawwrite('--------------------------------\n')

rawwrite('--------------------------------\n')
authors = set(post['author'] for post in posts)
for author in authors:
	author_score = sum([post_predictions['score'] for post_predictions in post_predictions_list if post_predictions['author'] == author])
	rawwrite("%s: %d\n" % (author, author_score))

rawwrite('--------------------------------\n')
	
	#print("\n".join(post.text ))


