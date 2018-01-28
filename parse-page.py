from bs4 import BeautifulSoup
from collections import namedtuple
import json
from operator import itemgetter
import re as re

Post = namedtuple("Post", ["author", "text"])
Prediction = namedtuple("Prediction", ["author", "white_name", "black_name", "outcome", "round"])
PredictionWithScore = namedtuple("PredictionWithScore", Prediction._fields + ("score",))
Ranking = namedtuple("Ranking", ["author", "ranking_list"])
MastersAppellatives = namedtuple("MastersAppellatives", ["names", "nicknames"])
ManualAdjustments = namedtuple("ManualAdjustments", [
	"post_corrections",
	"should_ignore_post",
	"official_ranking",
	"scoring_system",
	"games_per_round",
	"team_names"])

######################################

import sys

def write_out(string):
	sys.stdout.buffer.write(string.encode("utf-8"))

def write_err(string):
	sys.stderr.buffer.write(string.encode("utf-8"))

######################################

def load_aux_data(filename):
	with open(filename, "r", encoding = "utf-8") as file:
		data = json.load(file)

		masters_appellatives = MastersAppellatives(
			names = data["masters_names"],
			nicknames = data["masters_nicknames"]
			)

		# Add empty nicknames list, so that every master has an entry
		# in the nicknames dictionary
		for master_name in masters_appellatives.names:
			if master_name not in masters_appellatives.nicknames.keys():
				masters_appellatives.nicknames[master_name] = []

		post_corrections = []
		for correction in data["corrections"]:
			post_correction = Post(
				author = correction["author"],
				text = "\n".join(correction["text"]))
			post_corrections.append(post_correction)

		def should_ignore_post(post):
			return any(string in post.text for string in data["posts_string_blacklist"])

		official_ranking = {
			int(position) : names_list
			for (position, names_list)
			in data["official_ranking"].items() }

		scoring_system = (
			"2_2_2" if "scoring_system" in data.keys() and data["scoring_system"] == "2_2_2"
			else "2_1_3")

		games_per_round = (
			None if "games_per_round" not in data.keys()
			else data["games_per_round"])

		team_names = (
			{} if "team_names" not in data.keys()
			else data["team_names"])

		manual_adjustments = ManualAdjustments(
			post_corrections = post_corrections,
			should_ignore_post = should_ignore_post,
			official_ranking = official_ranking,
			scoring_system = scoring_system,
			games_per_round = games_per_round,
			team_names = team_names
			)

		return masters_appellatives, manual_adjustments
	# S. also https://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object

##############################################

def load_posts(filename, should_ignore_post, team_names):
	html_page = open(filename, "rb").read().decode("utf-8", "ignore")
	soup = BeautifulSoup(html_page, "html.parser")
	post_tags = soup.find_all("li", attrs={"class": re.compile("comment byuser.*")})

	posts = []

	for post_tag in post_tags:
		comment_author_class = [
			post_tag_class
			for post_tag_class in post_tag["class"]
			if post_tag_class.startswith("comment-author-") ]

		if len(comment_author_class) != 1:
			continue

		post_text = post_tag.find("div", attrs = {"class": "info_com"}).text
		post_username = [ line for line in post_text.split("\n") if line != "" ][0]
		post_author = (
			post_username if post_username not in team_names.keys()
			else team_names[post_username])

		post = Post( author = post_author, text = post_text )

		if should_ignore_post(post):
			continue

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
				return int(search_result.group("round_number"))
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

def get_masters_names_in_line(line, masters_appellatives):
	masters_names_in_line = []
	for master_name in masters_appellatives.names:
		# Try to match just the first or family name, or the nick
		master_tokens = master_name.split()
		master_tokens.extend(masters_appellatives.nicknames[master_name])

		for master_token in master_tokens:
			token_regex = r"(\b|\d)" + master_token + r"(\b|\d)"
			maybe_match = re.search(token_regex, line, re.IGNORECASE)
			if maybe_match is not None:
				masters_names_in_line.append((master_name, maybe_match.start()))
				break

	return masters_names_in_line

def get_line_prediction(line, masters_appellatives):
	# Find result
	line_outcome = "?"
	for outcome_re, outcome in get_line_prediction.possible_outcomes:
		if outcome_re.search(line):
			line_outcome = outcome
			break

	masters_names_in_line = get_masters_names_in_line(line, masters_appellatives)

	if len(masters_names_in_line) == 2 and line_outcome != "?":
		masters_names_in_line.sort(key = itemgetter(1))
		return (masters_names_in_line[0], masters_names_in_line[1], line_outcome)
	elif len(masters_names_in_line) < 2:
		return None
	else:
		write_err("Suspect line: %s\n (%d names, %s outcome)\n"
			% (line, len(masters_names_in_line), line_outcome))


# In descending order of reliability,
# e.g. "0 - 1" matches both the 2nd and the 6th regexp,
# but the former has priority
get_line_prediction.possible_outcomes = [
		(re.compile("\D1\s*[-–\\\/]\s*0($|\D)"), "1"), # 1 - 0
		(re.compile("\D0\s*[-–\\\/]\s*1($|\D)"), "2"), # 0 - 1
		(re.compile("\D½\s*[-–\\\/]\s*½($|\D)"), "X"), # ½ - ½
		(re.compile("\D1\s*[\\\/]\s*2($|\D)"), "X"), # 1/2
		(re.compile("\D0\.5($|\D)"), "X"), # 0.5
		(re.compile("\spatta($|\s)"), "X"), # patta
		(re.compile("\s1\s*0($|\s)"), "1"), # 1 0
		(re.compile("\s0\s*1($|\s)"), "2"), # 0 1
		(re.compile("\s[xX]($|\s)"), "X"), # X
		(re.compile("\D1($|\D)"), "1"), # 1
		(re.compile("\D2($|\D)"), "2"), # 2
		(re.compile("@@@"), "@") # @ (still to be played)
		]

def get_line_ranking(line, masters_appellatives):
	masters_names_in_line = []

	masters_names_in_line = get_masters_names_in_line(line, masters_appellatives)

	if len(masters_names_in_line) != 1:
		return None

	# Check that no other words are on the line
	# except possibly for a number
	if not get_line_ranking.line_re.search(line):
		write_err("Suspect line: %s\n (one name but not OK for the ranking)\n"
			% (line))
		return None

	# Success
	return masters_names_in_line[0][0]


# One optional numer at the beginning,
# followed by 1-3 words
get_line_ranking.line_re = re.compile("^\d*\W*(\S+\s?){1,3}$")

##############################################

def extract_predictions(post, masters_appellatives, games_per_round):
	lines = post.text.split("\n")

	post_predictions = []
	partial_ranking = []

	post_current_round = None
	is_in_ranking_mode = False

	for line in lines:
		line_round = get_line_round(line)
		if line_round is not None:
			post_current_round = line_round

		line_prediction = get_line_prediction(line, masters_appellatives)
		if line_prediction is not None:
			prediction = Prediction(
				author = post.author,
				white_name = line_prediction[0][0],
				black_name = line_prediction[1][0],
				outcome = line_prediction[2],
				round = post_current_round)

			post_predictions.append(prediction)
			continue

		line_ranking = get_line_ranking(line, masters_appellatives)
		if line_ranking is not None:
			partial_ranking.append(line_ranking)

	if games_per_round == None:
		games_per_round_count = len(masters_appellatives.names) / 2
	else:
		games_per_round_count = games_per_round

	if len(post_predictions) % games_per_round_count != 0:
		write_err("\n***\nUnusual number of predictions: %d\n%s\n%s\n***\n"
			% (len(post_predictions), post.author, post.text))

	expected_ranking_length = 5
	if len(partial_ranking) == expected_ranking_length:
		post_ranking = Ranking(
			author = post.author,
			ranking_list = partial_ranking)
	else:
		if len(partial_ranking) != 0:
			write_err("Bad ranking: %s\nPost: %s" % (partial_ranking, post.text))
		post_ranking = None

	if len(post_predictions) == 0 and post_ranking is None:
		write_err("\n***\nNo predictions nor ranking\n***%s\n" % repr(post.text))

	return post_predictions, post_ranking

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
			write_err("%s: wrong round, should be %d" % (prediction, expected_round))

		prediction_dict = prediction._asdict()  # make the prediction mutable
		prediction_dict["round"] = expected_round
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


def assign_prediction_scores(predictions, scoring_system):
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
			if scoring_system == "2_2_2":
				if prediction.outcome == "1":
					score = 2
				elif prediction.outcome == "X":
					score = 2
				elif prediction.outcome == "2":
					score = 2
			elif scoring_system == "2_1_3":
				if prediction.outcome == "1":
					score = 2
				elif prediction.outcome == "X":
					score = 1
				elif prediction.outcome == "2":
					score = 3
			else:
				assert False, "Unknown scoring system: " + scoring_system

		scored_predictions.append( PredictionWithScore(
			**prediction._asdict(),
			score = score))

	return scored_predictions

def assign_ranking_scores(rankings, official_ranking):
	# “Indovinare il vincitore del torneo porterà 3 punti;
	# ciascun giocatore in classifica, diverso dal vincitore,
	# di cui si sia indovinata la posizione porterà 2 punti;
	# ciascun giocatore indovinato ma messo al posto sbagliato
	# porterà 1 punto.”

	all_in_official_ranking = [
		master_name
		for names_list in official_ranking.values()
		for master_name in names_list
		]

	ranking_scores = {}  # author --> points

	for ranking in rankings:
		if ranking.author == "Official results":
			continue

		wrongly_placed = []

		score = 0

		for position, master_name in enumerate(ranking.ranking_list):
			if position == 0 and master_name in official_ranking[position + 1]:
				score += 3
			elif position > 0 and master_name in official_ranking[position + 1]:
				score += 2
			else:
				wrongly_placed.append(master_name)

		for master_name in wrongly_placed:
			if master_name in all_in_official_ranking:
				score += 1

		# This automatically overwrites older predictions
		ranking_scores[ranking.author] = score

	return ranking_scores

##############################################

masters_appellatives, manual_adjustments = load_aux_data("aux-data.json")

tournament_text = open("tournament.txt", "rb").read().decode("utf-8", "ignore")
tournament_post = Post( author = "Official results", text = tournament_text)
official_results, _ = extract_predictions(tournament_post, masters_appellatives, manual_adjustments.games_per_round)

posts = load_posts("thread.html", manual_adjustments.should_ignore_post, manual_adjustments.team_names)
posts.extend(manual_adjustments.post_corrections)

all_predictions = []
all_predictions.extend(official_results)

all_rankings = []

for post in posts:
	post_predictions, post_ranking = extract_predictions(post, masters_appellatives, manual_adjustments.games_per_round)

	#write_err("%s : %s\n" % (post.text, post_predictions))

	all_predictions.extend(post_predictions)

	if post_ranking is not None:
		all_rankings.append(post_ranking)


all_predictions = repair_turns(all_predictions)
all_predictions = remove_duplicates(all_predictions)
all_predictions = assign_prediction_scores(all_predictions, manual_adjustments.scoring_system)

authors = set(post.author for post in posts)
rounds = sorted(list(set(prediction.round for prediction in official_results)))
games_per_round_count = len(masters_appellatives.names) / 2

scores_per_rounds = []
for round in rounds:
	round_entries = []
	for author in authors:
		author_score = sum(
			prediction.score
			for prediction in all_predictions
			if prediction.author == author and prediction.round == round)

		# “Nel caso vengano indovinate tutte le partite di un turno,
		# verranno assegnati 3 punti aggiuntivi.”
		author_good_predictions_count = sum(
			1
			for prediction in all_predictions
			if prediction.author == author
				and prediction.round == round
				and prediction.score > 0)

		if author_good_predictions_count == games_per_round_count:
			author_score += 3

		scores_per_rounds.append( (round, author, author_score) )

		author_cumulated_score = sum(
			tuple[2]
			for tuple in scores_per_rounds
			if tuple[1] == author)

		round_entries.append((author, author_score, author_cumulated_score))

	# sort by descending score, then by name
	round_entries.sort( key = lambda round_entry: (-round_entry[1], round_entry[0].lower()) )

	write_out("\n────────────────────────────────\n")
	write_out("Punteggi del turno %s\n\n" % (round))
	for author, author_score, author_cumulated_score in round_entries:
		write_out("%s : %d\n" % (author, author_score))

	write_out("\n────────────────────────────────\n")
	write_out("Classifica dopo il turno %s\n\n" % (round))

	# sort by descending cumulated score
	round_entries.sort( key = lambda round_entry: (-round_entry[2], round_entry[0].lower()) )
	for author, author_score, author_cumulated_score in round_entries:
		write_out("%s : %d\n" % (author, author_cumulated_score))
	write_out("────────────────────────────────\n")

ranking_scores = assign_ranking_scores(all_rankings, manual_adjustments.official_ranking)
#write_out("Punti piazzamenti:\n%s\n" % str(ranking_scores))

grand_total_entries = []
for author in authors:
	author_predictions_score = sum(
		round_entry[2]
		for round_entry in round_entries
		if round_entry[0] == author)

	author_ranking_score = ranking_scores[author] if author in ranking_scores.keys() else 0

	author_final_score = author_predictions_score + author_ranking_score

	grand_total_entries.append((author, author_ranking_score, author_final_score))

# sort by descending score, then by name
grand_total_entries.sort( key = lambda round_entry: (-round_entry[1], round_entry[0].lower()) )
write_out("\n────────────────────────────────\n")
write_out("Punteggi per i piazzamenti\n")
for author, author_ranking_score, author_final_score in grand_total_entries:
	write_out("%s : %d\n" % (author, author_ranking_score))

write_out("\n────────────────────────────────\n")
write_out("CLASSIFICA FINALE\n")

# sort by descending cumulated score
grand_total_entries.sort( key = lambda round_entry: (-round_entry[2], round_entry[0].lower()))
for author, author_ranking_score, author_final_score in grand_total_entries:
	write_out("%s : %d\n" % (author, author_final_score))
write_out("────────────────────────────────\n")

