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

from bs4 import BeautifulSoup

def process_post(post, participants):
	lines = post['text'].split('\n')
	
	post['bet_count'] = 0.0
	
	for line in lines:
		participants_in_line = 0
		for participant in participants:
			if line.find(participant) != -1:
				participants_in_line += 1
			else:
				participant_tokens = participant.split()
				for participant_token in participant_tokens:
					if line.find(participant_token) != -1:
						participants_in_line += 0.95
					
		
		if participants_in_line == 2:
			post['bet_count'] += 1.0
		elif participants_in_line > 1:
			post['bet_count'] += 0.95
				
	
	#return '\n'.join(lines)

##############################################


participants = load_participants('participants.json')
#print(participants)

posts = load_posts('thread.html')
#sys.stdout.buffer.write(b'\ufeff')
print(len(posts))

for post in posts:
	rawwrite('--------------------------------\n')
	rawwrite(post['author'])
	process_post(post, participants)
	rawwrite(post['text'])
	rawwrite('\n')
	rawwrite("%.2f" % post['bet_count'])
	rawwrite('\n')
	rawwrite('--------------------------------\n')


	#print("\n".join(post.text ))
	

