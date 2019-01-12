from bs4 import BeautifulSoup
from collections import namedtuple
import datetime
from enum import Enum
import json
from operator import itemgetter
import re as re

Post = namedtuple("Post", ["author", "date", "text"])
Prediction = namedtuple("Prediction", ["author", "white_name", "black_name", "outcome", "round"])
PredictionWithScore = namedtuple("PredictionWithScore", Prediction._fields + ("score",))
Ranking = namedtuple("Ranking", ["author", "ranking_list"])
MastersAppellatives = namedtuple("MastersAppellatives", ["names", "nicknames"])
TournamentData = namedtuple("TournamentData", [
	"last_checked_post_datetime",
	"post_corrections",
	"should_ignore_post",
	"official_ranking",
	"scoring_system",
	"enable_default_draw_prediction",
	"games_per_round",
	"team_names",
	"expected_ranking_length",
	"bonus_for_perfect_round_prediction",
	"ranking_scoring"])
RoundEntry = namedtuple("RoundEntry", [
	"round",
	"author",
	"author_predictions_count",
	"author_score",
	"author_cumulated_score"])

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

		_, last_checked_post_datetime = get_username_and_date(
			data.get("last_checked_post", "Dubois\n10 ottobre 1817\n19:14\n"))

		post_corrections = []
		for correction in data["corrections"]:
			post_correction = Post(
				author = correction["author"],
				date = datetime.datetime(1817, 10, 10),
				text = "\n".join(correction["text"]))
			post_corrections.append(post_correction)

		def should_ignore_post(post):
			return any(string in post.text for string in data["posts_string_blacklist"] if string != "")

		official_ranking = {
			int(position) : names_list
			for (position, names_list)
			in data["official_ranking"].items() }

		scoring_system = data.get("scoring_system", "2_1_3")
		
		enable_default_draw_prediction = data.get("enable_default_draw_prediction", False)

		games_per_round = data.get("games_per_round", None)

		team_names = data.get("team_names", {})

		expected_ranking_length = data.get("expected_ranking_length", 5)

		bonus_for_perfect_round_prediction = data.get("bonus_for_perfect_round_prediction", 0)

		ranking_scoring = data.get("ranking_scoring",
			{ "first_ranked_correct" : 3, "other_ranked_correct" : 2, "ranked_incorrect" : 1 } )

		tournament_data = TournamentData(
			last_checked_post_datetime = last_checked_post_datetime,
			post_corrections = post_corrections,
			should_ignore_post = should_ignore_post,
			official_ranking = official_ranking,
			scoring_system = scoring_system,
			enable_default_draw_prediction = enable_default_draw_prediction,
			games_per_round = games_per_round,
			team_names = team_names,
			expected_ranking_length = expected_ranking_length,
			bonus_for_perfect_round_prediction = bonus_for_perfect_round_prediction,
			ranking_scoring = ranking_scoring
			)

		return masters_appellatives, tournament_data
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
		post_username, post_date = get_username_and_date(post_text)
		post_author = (
			post_username if post_username not in team_names.keys()
			else team_names[post_username])

		post = Post( author = post_author, date = post_date, text = post_text )

		if should_ignore_post(post):
			continue

		posts.append(post)

	return posts

##############################################

def get_username_and_date(text):
	# date on second non-empty line
	# time on third not-empty line
	non_empty_lines = [ line for line in text.split("\n") if line != "" ]

	username = non_empty_lines[0]

	date_text = non_empty_lines[1]
	time_text = non_empty_lines[2]

	date_elements = date_text.split()
	day = int(date_elements[0])
	month = get_username_and_date.months[date_elements[1]]
	year = int(date_elements[2])

	time_elements = time_text.strip().split(":")
	hour = int(time_elements[0])
	minute = int(time_elements[1])

	date = datetime.datetime(year, month, day, hour, minute, 0)
	return username, date

get_username_and_date.months = {
	"gennaio" : 1,
	"febbraio" : 2,
	"marzo" : 3,
	"aprile" : 4,
	"maggio" : 5,
	"giugno" : 6,
	"luglio" : 7,
	"agosto" : 8,
	"settembre" : 9,
	"ottobre" : 10,
	"novembre" : 11,
	"dicembre" : 12
	}

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
	("(^|\W)primo(:|$|\W)", " 1 "),
	("(^|\W)secondo(:|$|\W)", " 2 "),
	("(^|\W)terzo(:|$|\W)", " 3 "),
	("(^|\W)quarto(:|$|\W)", " 4 "),
	("(^|\W)quinto(:|$|\W)", " 5 "),
	("(^|\W)sesto(:|$|\W)", " 6 "),
	("(^|\W)settimo(:|$|\W)", " 7 "),
	("(^|\W)ottavo(:|$|\W)", " 8 "),
	("(^|\W)nono(:|$|\W)", " 9 "),
	("(^|\W)decimo(:|$|\W)", " 10 "),
	("(^|\W)undicesimo(:|$|\W)", " 11 "),
	("(^|\W)dodicesimo(:|$|\W)", " 12 "),
	("(^|\W)tredicesimo(:|$|\W)", " 13 "),
	("(^|\W)quattordicesimo(:|$|\W)", " 14 "),
	("(^|\W)quindicesimo(:|$|\W)", " 15 "),
	("(^|\W)sedicesimo(:|$|\W)", " 16 "),
	("(^|\W)I(:|$|\W)", " 1 "),
	("(^|\W)II(:|$|\W)", " 2 "),
	("(^|\W)III(:|$|\W)", " 3 "),
	("(^|\W)IV(:|$|\W)", " 4 "),
	("(^|\W)V(:|$|\W)", " 5 "),
	("(^|\W)VI(:|$|\W)", " 6 "),
	("(^|\W)VII(:|$|\W)", " 7 "),
	("(^|\W)VIII(:|$|\W)", " 8 "),
	("(^|\W)IX(:|$|\W)", " 9 "),
	("(^|\W)X(:|$|\W)", " 10 "),
	("(^|\W)XI(:|$|\W)", " 11 "),
	("(^|\W)XII(:|$|\W)", " 12 "),
	("(^|\W)XIII(:|$|\W)", " 13 "),
	("(^|\W)XIV(:|$|\W)", " 14 "),
	("(^|\W)XV(:|$|\W)", " 15 "),
	("(^|\W)XVI(:|$|\W)", " 16 "),
	]

get_line_round.ordinal_replacements_regexps = [
	( re.compile(pair[0], re.IGNORECASE | re.ASCII), pair[1]) for pair in get_line_round.ordinal_replacements
]

get_line_round.round_regexps = [
	re.compile("(Round|Turno)\W*(?P<round_number>\d+)", re.IGNORECASE | re.ASCII),
	re.compile("(?P<round_number>\d+)\W*(Round|Turno)", re.IGNORECASE | re.ASCII)
]

def get_masters_names_in_line(line, masters_appellatives):
	masters_names_in_line = []
	for master_name in masters_appellatives.names:
		# Try to match just the first or family name, or the nick
		master_tokens = master_name.split()
		master_tokens.extend(masters_appellatives.nicknames[master_name])

		for master_token in master_tokens:
			token_regex = r"(\b|\d|½)" + master_token + r"(\b|\d|½)"
			maybe_match = re.search(token_regex, line, re.IGNORECASE)
			if maybe_match is not None:
				masters_names_in_line.append((master_name, maybe_match.start()))
				break

	return masters_names_in_line

class ParseOutcome(Enum):
	SUCCESS = 1,
	NONE = 2,
	SUSPECT = 3

LinePredictionResult = namedtuple("LinePredictionResult", [
	"parse_outcome",
	"suspect_reason",
	"first_master",
	"second_master",
	"match_outcome"])

def get_line_prediction(line, masters_appellatives, author_name):
	# Find result
	match_outcome = None
	for outcome_re, outcome in get_line_prediction.possible_outcomes:
		if outcome_re.search(line):
			match_outcome = outcome
			break

	masters_names_in_line = get_masters_names_in_line(line, masters_appellatives)

	if len(masters_names_in_line) == 2 and match_outcome is not None:
		masters_names_in_line.sort(key = itemgetter(1))
		return LinePredictionResult(
			parse_outcome = ParseOutcome.SUCCESS,
			suspect_reason = None,
			first_master = masters_names_in_line[0][0],
			second_master = masters_names_in_line[1][0],
			match_outcome = match_outcome)
	elif len(masters_names_in_line) == 1:
		return LinePredictionResult(
			parse_outcome = ParseOutcome.SUSPECT,
			suspect_reason = "One master, {}".format(masters_names_in_line[0][0]),
			first_master = None,
			second_master = None,
			match_outcome = None)
	elif len(masters_names_in_line) < 2:
		return LinePredictionResult(
			parse_outcome = ParseOutcome.NONE,
			suspect_reason = None,
			first_master = None,
			second_master = None,
			match_outcome = None)
	else:
		return LinePredictionResult(
			parse_outcome = ParseOutcome.SUSPECT,
			suspect_reason = "{} masters: {}".format(len(masters_names_in_line), (", ").join([master_name[0] for master_name in masters_names_in_line])),
			first_master = None,
			second_master = None,
			match_outcome = match_outcome)

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
		(re.compile("\s½($|\s)"), "X"), # patta
		(re.compile("\s1\s*0($|\s)"), "1"), # 1 0
		(re.compile("\s0\s*1($|\s)"), "2"), # 0 1
		(re.compile("\s[xX]($|\s)"), "X"), # X
		(re.compile("\D1($|\D)"), "1"), # 1
		(re.compile("\D2($|\D)"), "2"), # 2
		(re.compile("@@@"), "@") # @ (still to be played)
		]

def get_line_ranking(line, masters_appellatives, author_name):
	masters_names_in_line = []

	masters_names_in_line = get_masters_names_in_line(line, masters_appellatives)

	if len(masters_names_in_line) != 1:
		return None

	# Check that no other words are on the line
	# except possibly for a number
	if not get_line_ranking.line_re.search(line):
		return None

	# Success
	return masters_names_in_line[0][0]


# One optional numer at the beginning,
# followed by 1-3 words
get_line_ranking.line_re = re.compile("^\d*[).\W]*(\S+\s?){1,3}$")

##############################################

def extract_predictions(post, masters_appellatives, tournament_data):
	games_per_round = tournament_data.games_per_round

	lines = post.text.split("\n")

	post_predictions = []
	partial_ranking = []

	post_current_round = None
	is_in_ranking_mode = False

	is_post_suspect = False
	suspect_reasons = ""
	for line in lines:
		line_round = get_line_round(line)
		if line_round is not None:
			post_current_round = line_round

		line_prediction = get_line_prediction(line, masters_appellatives, post.author)

		if line_prediction.parse_outcome == ParseOutcome.SUCCESS:
			prediction = Prediction(
				author = post.author,
				white_name = line_prediction.first_master,
				black_name = line_prediction.second_master,
				outcome = line_prediction.match_outcome,
				round = post_current_round)

			post_predictions.append(prediction)
			continue
		else:
			line_ranking = get_line_ranking(line, masters_appellatives, post.author)
			if line_ranking is not None:
				partial_ranking.append(line_ranking)
			elif line_prediction.parse_outcome == ParseOutcome.SUSPECT:
				suspect_reasons += "Suspect line: {} ({})\n".format(
					line, line_prediction.suspect_reason)
				is_post_suspect = True

	if games_per_round == None:
		games_per_round_count = len(masters_appellatives.names) / 2
	else:
		games_per_round_count = games_per_round

	if len(post_predictions) % games_per_round_count != 0:
		suspect_reasons += "Unusual number of predictions: {}\n".format(
			len(post_predictions))
		is_post_suspect = True

	if len(partial_ranking) == tournament_data.expected_ranking_length:
		post_ranking = Ranking(
			author = post.author,
			ranking_list = partial_ranking)
	else:
		if len(partial_ranking) != 0:
			suspect_reasons += "Bad ranking: {}\n".format(partial_ranking)
			is_post_suspect = True
		post_ranking = None

	if len(post_predictions) == 0 and post_ranking is None:
		suspect_reasons += "No predictions nor ranking\n"
		is_post_suspect = True

	if is_post_suspect and post.date > tournament_data.last_checked_post_datetime :
		write_err("Suspect post:\n{}\nReasons:\n{}\n\n".format(repr(post.text), suspect_reasons))

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
		if game(prediction) not in official_results:
			write_err("Missing game in official results: " + str(prediction) + "\n")
			return prediction

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
		score = 0
		if prediction_key(prediction) in official_results.keys():
			if tournament_data.scoring_system == "2_2_2":
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
			elif scoring_system == "3_1_4":
				if prediction.outcome == "1":
					score = 3
				elif prediction.outcome == "X":
					score = 1
				elif prediction.outcome == "2":
					score = 4					
			else:
				assert False, "Unknown scoring system: " + scoring_system

		scored_predictions.append( PredictionWithScore(
			**prediction._asdict(),
			score = score))

	return scored_predictions

##############################################

def calculate_round_entries(all_predictions, official_results, tournament_data):
	authors = set(post.author for post in all_predictions)
	rounds = sorted(list(set(prediction.round for prediction in official_results)))

	round_entries = []
	scores_per_rounds = []
	
	authors_with_predictions = set()
	for round in rounds:
		games_in_this_round = sum(
			1
			for prediction in official_results
			if prediction.round == round
			)

		for author in authors:
			if author == "Official results":
				continue
				
			author_predictions_for_this_round = [
				prediction
				for prediction in all_predictions
				if prediction.author == author
					and prediction.round == round]

			if len(author_predictions_for_this_round) > 0:
				authors_with_predictions.add(author)
			else:	
				# “Pronostico di riserva”: if the author was a participant
				# in previous rounds, give points as if an all-draw prediction
				# for this round had been given	
				if (tournament_data.enable_default_draw_prediction
						and author in authors_with_predictions):
					author_predictions_for_this_round = [
						prediction
						for prediction in official_results
						if prediction.round == round
						and prediction.outcome == "X"]
					
			author_score_for_this_round = sum(
				prediction.score
				for prediction in author_predictions_for_this_round)

			# “Nel caso vengano indovinate tutte le partite di un turno,
			# verranno assegnati 3 punti aggiuntivi.”
			author_good_predictions_count = sum(
				1
				for prediction in author_predictions_for_this_round
				if prediction.score > 0)
				
			if (author_good_predictions_count == games_in_this_round):
				author_score_for_this_round += tournament_data.bonus_for_perfect_round_prediction

			scores_per_rounds.append( (round, author, author_score_for_this_round) )

			author_cumulated_score = sum(
				tuple[2]
				for tuple in scores_per_rounds
				if tuple[1] == author)

			round_entries.append(RoundEntry(
				round = round,
				author = author,
				author_predictions_count = len(author_predictions_for_this_round),
				author_score = author_score_for_this_round,
				author_cumulated_score = author_cumulated_score))

	return round_entries

def calculate_grand_total_entries(round_entries, ranking_scores):
	authors = set(round_entry.author for round_entry in round_entries)

	grand_total_entries = []
	for author in authors:
		author_predictions_score = sum(
			round_entry.author_score
			for round_entry in round_entries
			if round_entry.author == author)

		if author_predictions_score > 10 and author not in ranking_scores:
			write_err("Suspect missing ranking for {}\n".format(author))

		author_ranking_score = ranking_scores.get(author, 0)
		author_final_score = author_predictions_score + author_ranking_score

		grand_total_entries.append((author, author_final_score))

	return grand_total_entries

def assign_ranking_scores(rankings, tournament_data):
	# “Indovinare il vincitore del torneo porterà 3 punti;
	# ciascun giocatore in classifica, diverso dal vincitore,
	# di cui si sia indovinata la posizione porterà 2 punti;
	# ciascun giocatore indovinato ma messo al posto sbagliato
	# porterà 1 punto.”
	official_ranking = tournament_data.official_ranking

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
				score += tournament_data.ranking_scoring["first_ranked_correct"]
			elif position > 0 and master_name in official_ranking[position + 1]:
				score += tournament_data.ranking_scoring["other_ranked_correct"]
			else:
				wrongly_placed.append(master_name)

		for master_name in wrongly_placed:
			if master_name in all_in_official_ranking:
				score += tournament_data.ranking_scoring["ranked_incorrect"]

		# This automatically overwrites older predictions
		ranking_scores[ranking.author] = score

	return ranking_scores

def print_round_results(round_entries):
	rounds = sorted(list(set(round_entry.round for round_entry in round_entries)))

	for round in rounds:
		round_entries_for_this_round = [
			round_entry
			for round_entry in round_entries
			if round_entry.round == round ]

		# sort by descending score, then by name
		round_entries_for_this_round.sort( key = lambda round_entry: (-round_entry.author_score, round_entry.author.lower()) )

		write_out("\n────────────────────────────────\n")
		write_out("Punteggi del turno %s\n\n" % (round))
		for round_entry in round_entries_for_this_round:
			if round_entry.author_predictions_count == 0:
				continue
			write_out("%s : %d\n" % (round_entry.author, round_entry.author_score))

		write_out("\n────────────────────────────────\n")
		write_out("Classifica dopo il turno %s\n\n" % (round))

		# sort by descending cumulated score
		round_entries_for_this_round.sort( key = lambda round_entry: (-round_entry.author_cumulated_score, round_entry.author.lower()) )
		for round_entry in round_entries_for_this_round:
			write_out("%s : %d\n" % (round_entry.author, round_entry.author_cumulated_score))
		write_out("────────────────────────────────\n")


def print_ranking_scores(ranking_scores):
	ranking_entries = list(ranking_scores.items())

	# sort by descending score, then by name
	ranking_entries.sort( key = lambda round_entry: (-round_entry[1], round_entry[0].lower()) )
	write_out("\n────────────────────────────────\n")
	write_out("Punteggi per i piazzamenti\n")
	for author, author_ranking_score in ranking_entries:
		write_out("%s : %d\n" % (author, author_ranking_score))


def print_final_results(grand_total_entries):
	write_out("\n────────────────────────────────\n")
	write_out("CLASSIFICA FINALE\n")

	# sort by descending cumulated score
	grand_total_entries.sort( key = lambda round_entry: (-round_entry[1], round_entry[0].lower()))
	for author, author_final_score in grand_total_entries:
		write_out("%s : %d\n" % (author, author_final_score))
	write_out("────────────────────────────────\n")

##############################################
# aux

def print_all_rankings(sorted_rankings):
	write_err("\n")
	for ranking in sorted_rankings:
		write_err("{}:\n{}\n{}\n{}\n\n".format(
			ranking.author,
			ranking.ranking_list[0],
			ranking.ranking_list[1],
			ranking.ranking_list[2],
			))

##############################################
# main

masters_appellatives, tournament_data = load_aux_data("aux-data.json")

tournament_text = open("tournament.txt", "rb").read().decode("utf-8", "ignore")
tournament_post = Post(
	author = "Official results",
	date = datetime.datetime(1817, 10, 10),
	text = tournament_text)
official_results, _ = extract_predictions(tournament_post, masters_appellatives, tournament_data)

posts = load_posts("thread.html", tournament_data.should_ignore_post, tournament_data.team_names)
posts.extend(tournament_data.post_corrections)

all_predictions = []
all_predictions.extend(official_results)

all_rankings = []

for post in posts:
	post_predictions, post_ranking = extract_predictions(post, masters_appellatives, tournament_data)

	#write_err("%s : %s\n" % (post.text, post_predictions))

	all_predictions.extend(post_predictions)

	if post_ranking is not None:
		all_rankings.append(post_ranking)


all_predictions = repair_turns(all_predictions)
all_predictions = remove_duplicates(all_predictions)
all_predictions = assign_prediction_scores(all_predictions, tournament_data.scoring_system)

round_entries = calculate_round_entries(all_predictions, official_results, tournament_data)
ranking_scores = assign_ranking_scores(all_rankings, tournament_data)
grand_total_entries = calculate_grand_total_entries(round_entries, ranking_scores)

sorted_rankings = sorted(all_rankings, key = lambda ranking: (ranking.author.lower()))

print_round_results(round_entries)
print_ranking_scores(ranking_scores)
print_final_results(grand_total_entries)
