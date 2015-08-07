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
		self.url = 'https://%s:%s/api/1.1/xml' % (self.hostname, self.port)
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
		return xml_response

	def logout(self):
		xml_string = "<LogoutRequest session-id=\"%s\" />" % (self.session_id)
		xml_response = self.api_request(xml_string)
		return xml_response

	def get_sites(self):
		xml_string = "<SiteListingRequest session-id=\"%s\"></SiteListingRequest>" % self.session_id
		xml_response = self.api_request(xml_string)
		site_list = []
		for SiteSummary in xml_response.iter('SiteSummary'):
			site = {}
			site['id'] = SiteSummary.get('id')
			site['name'] = SiteSummary.get('name')
			site['description'] = SiteSummary.get('description')
			site['riskfactor'] = SiteSummary.get('riskfactor')
			site['riskscore'] = SiteSummary.get('riskscore')
			site_list.append(site)
		return site_list

	def get_site_hosts(self, site_id):
		xml_string = "<SiteConfigRequest session-id=\"%s\" site-id=\"%s\"></SiteConfigRequest>" % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		host_list = []
		site = xml_response.find('Site')
		print(site)
		hosts = site.find('Hosts')
		print(hosts)
		for hostrange in hosts.getchildren():
			if hostrange.tag == 'range':
				host_list.append(str('%s-%s' % (hostrange.attrib.get('from'), hostrange.attrib.get('to'))))
			elif hostrange.tag == 'host':
				host_list.append(str(host))
		return host_list

if __name__ == '__main__':
	# Usage: ./nexpose.py hostname port username password
	nexpose = Nexpose(sys.argv[1], sys.argv[2])
	result = nexpose.login(sys.argv[3], sys.argv[4])
	if nexpose.session_id:
		print(nexpose.get_site_hosts('1'))
		nexpose.logout()
