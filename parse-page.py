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


process_line.possible_outcomes = [
		(re.compile("\D1\s*[-–\\\/]\s*0($|\D)"), '1'),
		(re.compile("\D0\s*[-–\\\/]\s*1($|\D)"), '2'),
		(re.compile("\D½\s*[-–\\\/]\s*½($|\D)"), 'X'),
		(re.compile("\D1[\\\/]2($|\D)"), 'X'),
		(re.compile("\s[xX]($|\s)"), 'X'),
		(re.compile("\D1($|\D)"), '1'),
		(re.compile("\D2($|\D)"), '2')
		]

##############################################

def process_post(post, participants):
	lines = post['text'].split('\n')

	post_parse_result = {}
	post_parse_result['bet_count'] = 0
	post_parse_result['odds'] = []

	for line in lines:
		line_parse_result = process_line(line, participants)
		if not line_parse_result is None:
			post_parse_result['bet_count'] += 1
			post_parse_result['odds'].append(line_parse_result[2])

	return post_parse_result

##############################################


participants = load_participants('participants.json')
#print(participants)

posts = load_posts('thread.html')
#sys.stdout.buffer.write(b'\ufeff')
print(len(posts))

for post in posts:
	rawwrite('--------------------------------\n')
	rawwrite(post['author'])
	post_parse_result = process_post(post, participants)
	rawwrite(post['text'])
	rawwrite('\n')
	rawwrite("%d: %s" % (post_parse_result['bet_count'], post_parse_result['odds']))
	rawwrite('\n')
	rawwrite('--------------------------------\n')


	#print("\n".join(post.text ))


