import re as re
import sys
from bs4 import BeautifulSoup

#htmltext = open('thread.html', "rb").read().decode('utf-8', 'ignore')
htmltext = open('thread.html', "rb").read().decode('utf-8')
soup = BeautifulSoup(htmltext, "html.parser")

post_tags = soup.find_all('li', attrs={'class': re.compile('comment byuser.*')})

#sys.stdout.buffer.write(b'\ufeff')
print(len(post_tags))

for post_tag in post_tags:
	comment_author_class = [ post_tag_class for post_tag_class in post_tag['class'] if post_tag_class.startswith('comment-author-') ]
	
	if len(comment_author_class) != 1:
		continue
		
	print(comment_author_class[0].replace('comment-author-', '', 1))
	
	post_body = post_tag.find('div', attrs = {'class': 'info_com'})
	
	sys.stdout.buffer.write('--------------------------------'.encode("utf-8"))
	sys.stdout.buffer.write(post_body.text.encode("utf-8"))
	sys.stdout.buffer.write('--------------------------------'.encode("utf-8"))
	
	
	#print("\n".join(post.text ))
