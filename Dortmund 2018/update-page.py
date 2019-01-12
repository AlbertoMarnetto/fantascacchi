import urllib.request

user_agent = "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"

url = "http://www.scacchierando.it/fantascacchi/fantadortmund-2"
headers={"User-Agent":user_agent,} 

request = urllib.request.Request(url,None,headers) 
response = urllib.request.urlopen(request)
data = response.read()
	
with open("thread.html", "wb") as file:
	file.write(data)
