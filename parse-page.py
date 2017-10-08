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
Prediction = namedtuple('Prediction', ['author', 'white_name', 'black_name', 'outcome', 'round'])
PredictionWithScore = namedtuple('PredictionWithScore', Prediction._fields + ('score',))

def get_line_round(line):
	# replace turn numbers expressed in non-standard forms ("primo", "VI", etc.)
	# with Arabic numbers
	for ordinal, replacement in get_line_round.ordinal_replacements_regexps:
		(new_line, replacement_count) = ordinal.subn(replacement, line)
		if replacement_count > 0:
			rawwrite("%s --> %s\n" % (line, new_line))
			line = new_line
			break

	# Indentify and extract the turn number
	for round_regexp in get_line_round.round_regexps:
		search_result = round_regexp.search(line)
		if search_result:
			try:
				return int(search_result.group('round_number'))
			except ValueError:
				pass  # non-numeric turn number, discard it

	return None

get_line_round.ordinal_replacements = [
	("(^|\W)primo($|\W)", " 1 "),
	("(^|\W)secondo($|\W)", " 2 "),
	("(^|\W)terzo($|\W)", " 3 "),
	("(^|\W)quarto($|\W)", " 4 "),
	("(^|\W)quinto($|\W)", " 5 "),
	("(^|\W)sesto($|\W)", " 6 "),
	("(^|\W)settimo($|\W)", " 7 "),
	("(^|\W)ottavo($|\W)", " 8 "),
	("(^|\W)nono($|\W)", " 9 "),
	("(^|\W)decimo($|\W)", " 10 "),
	("(^|\W)undicesimo($|\W)", " 11 "),
	("(^|\W)dodicesimo($|\W)", " 12 "),
	("(^|\W)tredicesimo($|\W)", " 13 "),
	("(^|\W)quattordicesimo($|\W)", " 14 "),
	("(^|\W)quindicesimo($|\W)", " 15 "),
	("(^|\W)sedicesimo($|\W)", " 16 "),
	("(^|\W)I($|\W)", " 1 "),
	("(^|\W)II($|\W)", " 2 "),
	("(^|\W)III($|\W)", " 3 "),
	("(^|\W)IV($|\W)", " 4 "),
	("(^|\W)V($|\W)", " 5 "),
	("(^|\W)VI($|\W)", " 6 "),
	("(^|\W)VII($|\W)", " 7 "),
	("(^|\W)VIII($|\W)", " 8 "),
	("(^|\W)IX($|\W)", " 9 "),
	("(^|\W)X($|\W)", " 10 "),
	("(^|\W)XI($|\W)", " 11 "),
	("(^|\W)XII($|\W)", " 12 "),
	("(^|\W)XIII($|\W)", " 13 "),
	("(^|\W)XIV($|\W)", " 14 "),
	("(^|\W)XV($|\W)", " 15 "),
	("(^|\W)XVI($|\W)", " 16 "),
	]

get_line_round.ordinal_replacements_regexps = [
	( re.compile(pair[0], re.IGNORECASE), pair[1]) for pair in get_line_round.ordinal_replacements
]

get_line_round.round_regexps = [
	re.compile("(Round|Turno)\D*(?P<round_number>\d+)", re.IGNORECASE),
	re.compile("(?P<round_number>\d+)\D*(Round|Turno)", re.IGNORECASE)
	]



def get_line_prediction(line, event_players):
	participants_in_line = []

	# Find event_players
	for player_name in event_players:
		idx = line.find(player_name)
		if idx != -1:
			participants_in_line.append((player_name, idx))
		else:
			# Try to match just the first or family name
			participant_tokens = player_name.split()
			for participant_token in participant_tokens:
				idx = line.find(participant_token)
				if idx != -1:
					participants_in_line.append((player_name, idx))

	# Find result
	line_outcome = '?'
	for outcome_re, outcome in get_line_prediction.possible_outcomes:
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
get_line_prediction.possible_outcomes = [
		(re.compile("\D1\s*[-–\\\/]\s*0($|\D)"), '1'), # 1 - 0
		(re.compile("\D0\s*[-–\\\/]\s*1($|\D)"), '2'), # 0 - 1
		(re.compile("\D½\s*[-–\\\/]\s*½($|\D)"), 'X'), # ½ - ½
		(re.compile("\D1[\\\/]2($|\D)"), 'X'), # 1/2
		(re.compile("\s[xX]($|\s)"), 'X'), # X
		(re.compile("\D1($|\D)"), '1'), # 1
		(re.compile("\D2($|\D)"), '2') # 2
		]

##############################################

def extract_predictions(post_author, post_text, event_players):
	lines = post_text.split('\n')

	post_predictions = []

	post_round = None

	for line in lines:
		line_round = get_line_round(line)
		if line_round is not None:
			post_round = line_round

		line_prediction = get_line_prediction(line, event_players)
		if line_prediction is None:
			continue

		prediction = Prediction(
			author = post_author,
			white_name = line_prediction[0][0],
			black_name = line_prediction[1][0],
			outcome = line_prediction[2],
			round = post_round)

		post_predictions.append(prediction)

	return post_predictions

##############################################

def assign_scores(predictions):
	def prediction_key(prediction):
		return (
			prediction.white_name,
			prediction.black_name,
			prediction.outcome
			)

	official_results = {
		prediction_key(official_result) : official_result
		for official_result in predictions
		if official_result.author == "Official results"
		}


	scored_predictions = []
	for prediction in predictions:
		if prediction.author == "Official results":
			continue

		score = 0
		if prediction_key(prediction) in official_results.keys():
			if prediction.outcome == '1':
				score = 2
			elif prediction.outcome == 'X':
				score = 1
			elif prediction.outcome == '2':
				score = 3

		scored_predictions.append( PredictionWithScore(
			**prediction._asdict(),
			score = score))

	return scored_predictions

##############################################

event_players = load_participants('participants.json')
#print(participants)

tournament_text = open('tournament.txt', "rb").read().decode('utf-8', 'ignore')
tournament_outcome = extract_predictions("Official results", tournament_text, event_players)

posts = load_posts('thread.html')

all_predictions = []
for post in posts:
	post_predictions = extract_predictions(post['author'], post['text'], event_players)
	post_predictions = assign_scores(post_predictions + tournament_outcome)
	all_predictions.extend(post_predictions)
	rawwrite('--------------------------------\n')
	rawwrite(post['author'])
	rawwrite(post['text'])
	rawwrite('\n')
	rawwrite("%d: %s\n" % (len(post_predictions), post_predictions))
	rawwrite("Score: %d\n" % sum(prediction.score for prediction in post_predictions))
	rawwrite('\n')
	rawwrite('--------------------------------\n')

rawwrite('--------------------------------\n')

authors = set(post['author'] for post in posts)
rounds = sorted(list(set(prediction.round for prediction in tournament_outcome)))

#rawwrite(str(all_predictions))

rawwrite('\n')
for round in rounds:
	rawwrite('--------------------------------\n')
	rawwrite("Punteggi turno %s\n" % (round))

	round_entries = []
	for author in authors:
		author_score = sum(
			prediction.score
			for prediction in all_predictions
			if prediction.author == author and prediction.round == round)

		author_cumulated_score = sum(
			prediction.score
			for prediction in all_predictions
			if prediction.author == author
				and prediction.round is not None
				and prediction.round <= round)

		round_entries.append((author, author_score, author_cumulated_score))

	# sort by descending score
	round_entries.sort( key = lambda round_entry: -round_entry[1])
	for author, author_score, author_cumulated_score in round_entries:
		rawwrite("%s : %d\n" % (author, author_score))

	rawwrite('--------------------------------\n')
	rawwrite("Classifica turno %s\n" % (round))

	# sort by descending cumulated score
	round_entries.sort( key = lambda round_entry: -round_entry[2])
	for author, author_score, author_cumulated_score in round_entries:
		rawwrite("%s : %d\n" % (author, author_cumulated_score))
	rawwrite('--------------------------------\n')

rawwrite('--------------------------------\n')



