from bs4 import BeautifulSoup
from collections import namedtuple
import json
from operator import itemgetter
import re as re

Post = namedtuple("Post", ['author', 'text'])
Prediction = namedtuple("Prediction", ['author', 'white_name', 'black_name', 'outcome', 'round'])
PredictionWithScore = namedtuple("PredictionWithScore", Prediction._fields + ('score',))

######################################

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

		post = Post( author = post_author, text = post_text )
		posts.append(post)

	return posts

##############################################

def get_line_round(line):
	# replace turn numbers expressed in non-standard forms ("primo", "VI", etc.)
	# with Arabic numbers
	for ordinal, replacement in get_line_round.ordinal_replacements_regexps:
		(new_line, replacement_count) = ordinal.subn(replacement, line)
		if replacement_count > 0:
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

def get_line_players(line, event_players):
	line_players = []
	for player_name in event_players:
		# Try to match just the first or family name
		participant_tokens = player_name.split()
		for participant_token in participant_tokens:
			participant_regex = r"\b" + participant_token + r"\b"
			maybe_match = re.search(participant_regex, line, re.IGNORECASE)
			if maybe_match is not None:
				line_players.append((player_name, maybe_match.start()))
				break

	return line_players

def get_line_prediction(line, event_players):
	line_players = []
		
	# Find result
	line_outcome = '?'
	for outcome_re, outcome in get_line_prediction.possible_outcomes:
		if outcome_re.search(line):
			line_outcome = outcome
			break
		#else:
		#	print('%s does not match %s' % (line, outcome))

	line_players = get_line_players(line, event_players)

	if len(line_players) == 2 and outcome is not None:
		line_players.sort(key = itemgetter(1))
		return (line_players[0], line_players[1], line_outcome)
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
		
def get_line_ranking(line, event_players):
	line_players = []

	line_players = get_line_players(line, event_players)

	if len(line_players) != 1:
		return None
		
	# Check that no other words are on the line
	# except possibly for a number
	if not get_line_ranking.line_re.search(line):
		return None
	
	# Success
	return line_players[0][0]
	

# One optional numer at the beginning,
# followed by 1-2 words
get_line_ranking.line_re = re.compile("^\d*\W*(\S+\s?){1,2}$")

##############################################

def extract_predictions(post, event_players):
	lines = post.text.split('\n')

	post_predictions = []
	post_ranking = []
	
	post_current_round = None
	is_in_ranking_mode = False
	
	for line in lines:
		line_round = get_line_round(line)
		if line_round is not None:
			post_current_round = line_round

		line_prediction = get_line_prediction(line, event_players)
		if line_prediction is not None:
			prediction = Prediction(
				author = post.author,
				white_name = line_prediction[0][0],
				black_name = line_prediction[1][0],
				outcome = line_prediction[2],
				round = post_current_round)

			post_predictions.append(prediction)
			continue
		
		line_ranking = get_line_ranking(line, event_players)
		if line_ranking is not None:
			rawwrite("For the ranking? " + line + " --> " + line_ranking + "\n")
			post_ranking.append(line_ranking)
				
	return post_predictions #, post_ranking)

##############################################

def repair_turns(predictions):
	def game(prediction):
		return (
			prediction.white_name,
			prediction.black_name,
			)
	
	official_results = {
		game(official_result) : official_result
		for official_result in predictions
		if official_result.author == "Official results"
		}
	
	def repaired_prediction(prediction):
		assert game(prediction) in official_results, "Missing game in official results " + str(prediction)

		expected_round = official_results[game(prediction)].round
		assert expected_round is not None, "Missing round in official results for game" + str(prediction)

		# if the given round matches with the tournament calendar, do nothing
		if prediction.round == expected_round:
			return prediction

		# Otherwise, write the correct round number
		# Only give a warning if a wrong round was given
		# (not if it was missing)
		if prediction.round is not None:
			rawwrite("%s: wrong round, should be %d" % (prediction, expected_round))

		prediction_dict = prediction._asdict()  # make the prediction mutable
		prediction_dict['round'] = expected_round
		return Prediction(**prediction_dict)

	return list(map(repaired_prediction, predictions))

def remove_duplicates(predictions):
	# from https://stackoverflow.com/a/480227/2453661

	# Iterate the list of predictions in reverse chronological order,
	# store every seen one in a set,
	# and discard a prediction
	# if another with the same author and game was already seen

	seen = {}

	def is_obsolete(prediction, seen):
		prediction_key = (
			prediction.author,
			prediction.white_name,
			prediction.black_name,
			prediction.round
			)

		if prediction_key in seen.keys():
			return True
		else:
			seen[prediction_key] = prediction
			return False

	return list(reversed([
		prediction for prediction in reversed(predictions)
		#prediction for prediction in predictions
		if not is_obsolete(prediction, seen)
		]))


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
tournament_post = Post( author = "Official results", text = tournament_text)
official_results = extract_predictions(tournament_post, event_players)


posts = load_posts('thread.html')

all_predictions = []
all_predictions.extend(official_results)

for post in posts:
	#post_predictions, post_ranking = extract_predictions(post, event_players)
	post_predictions = extract_predictions(post, event_players)
	all_predictions.extend(post_predictions)

all_predictions = repair_turns(all_predictions)
all_predictions = remove_duplicates(all_predictions)
all_predictions = assign_scores(all_predictions)

authors = set(post.author for post in posts)
rounds = sorted(list(set(prediction.round for prediction in official_results)))

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

	# sort by descending score, then by name
	round_entries.sort( key = lambda round_entry: (-round_entry[1], round_entry[0]) )
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



