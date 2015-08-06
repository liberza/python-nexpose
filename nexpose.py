#!/usr/bin/python3
import xml.etree.ElementTree as etree
import urllib.request
import urllib.parse
import sys
import ssl

__author__ = 'Nick Levesque <nick@portcanary.com>'

# Nexpose API wrapper.
class Nexpose:
	def __init__(self, hostname, port):
		self.hostname = hostname
		self.port = port
		self.url = 'https://%s:%s/api/1.2/xml' % (self.hostname, self.port)
		self.session_id = None

		# Often the Nexpose Console is run with a self-signed cert. We allow for that here.
		self.ctx = ssl.create_default_context()
		self.ctx.check_hostname = False
		self.ctx.verify_mode = ssl.CERT_NONE

	# Generic API request, feed it an xml string and off it goes.
	def api_request(self, xml_string):
		# Encode the xml so that urllib will accept it.
		post_data = (xml_string).encode('utf-8')

		# Prepare the request.
		request = urllib.request.Request(self.url)
		request.add_header("Content-type", "text/xml")

		# Get a response.
		response = urllib.request.urlopen(request, post_data, context=self.ctx).read()
		xml_response = etree.fromstring(response)

		# Check for errors and return response.
		if not xml_response.tag == 'Failure':
			return xml_response
		else:
			for exception in xml_response.iter('Exception'):
				for message in exception.iter('Message'):
					raise  Exception(str("Failure: " + message.text))

	# Login function, we must capture the session-id contained in the response if successful.
	def login(self, username, password):
		xml_string = "<LoginRequest user-id=\"%s\" password=\"%s\" />" % (username, password)
		xml_response = self.api_request(xml_string)
		self.session_id = xml_response.attrib.get('session-id')

	def logout(self):
		xml_string = "<LogoutRequest session-id=\"%s\" />" % (self.session_id)
		xml_response = self.api_request(xml_string)

if __name__ == '__main__':
	# Usage: ./nexpose.py hostname port username password
	nexpose = Nexpose(sys.argv[1], sys.argv[2])
	result = nexpose.login(sys.argv[3], sys.argv[4])
	if nexpose.session_id:
		print(nexpose.session_id)
		nexpose.logout()
