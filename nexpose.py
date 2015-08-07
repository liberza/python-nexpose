#!/usr/bin/python3
import defusedxml.ElementTree as ET
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

		# Often the Nexpose Console is run with a self-signed cert. 
		# We allow for that here.
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
		response = urllib.request.urlopen(request, 
										post_data, 
										context=self.ctx).read()
		xml_response = ET.fromstring(response)

		# Check for errors and return response.
		if xml_response.attrib.get('success') != ('0' or None):
			return xml_response
		else:
			raise Exception(response)

	# Login function, we must capture the session-id 
	# contained in the response if successful.
	def login(self, username, password):
		xml_string = "<LoginRequest user-id=\"%s\" password=\"%s\" />"\
					% (username, password)
		xml_response = self.api_request(xml_string)
		self.session_id = xml_response.attrib.get('session-id')
		return xml_response

	def logout(self):
		xml_string = "<LogoutRequest session-id=\"%s\" />" % (self.session_id)
		xml_response = self.api_request(xml_string)
		return xml_response

	# Returns a list of dicts containing site information.
	def get_sites(self):
		xml_string = "<SiteListingRequest session-id=\"%s\">\
					</SiteListingRequest>" % self.session_id
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

	# Returns a list of hosts for site_id, where hosts can be ranges,
	# single IPs or hostnames.
	def get_site_hosts(self, site_id):
		xml_string = "<SiteConfigRequest session-id=\"%s\" site-id=\"%s\">\
					</SiteConfigRequest>" % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		host_list = []
		site = xml_response.find('Site')
		hosts = site.find('Hosts')
		for host in hosts.getchildren():
			if host.tag == 'range':
				if host.attrib.get('to') is None:
					host_list.append(str(host.attrib.get('from')))
				else:
					host_list.append(str('%s-%s' % \
							(host.attrib.get('from'), host.attrib.get('to'))))
			elif host.tag == 'host':
				host_list.append(host.text)
		return host_list

	# Returns a dict of configuration info for site_id.
	def get_site_scan_config(self, site_id):
		xml_string = "<SiteConfigRequest session-id=\"%s\" site-id=\"%s\">\
					</SiteConfigRequest>" % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		site = xml_response.find('Site')
		scan_config = site.find('ScanConfig')
		config = {}
		config['template_id'] = scan_config.attrib.get('templateID')
		config['name'] = scan_config.attrib.get('name')
		config['id'] = scan_config.attrib.get('configID')
		config['engine_id'] = scan_config.attrib.get('engineID')
		config['config_version'] = scan_config.attrib.get('configVersion')
		return config
		
	def scan_site(self, site_id):
		xml_string = "<SiteScanRequest session-id = \"%s\" site-id=\"%s\">\
					</SiteScanRequest>" % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		scan_id = xml_response.find('Scan').attrib.get('scan-id')
		return scan_id
		

if __name__ == '__main__':
	# Usage: ./nexpose.py hostname port username password
	try:
		nexpose = Nexpose(sys.argv[1], sys.argv[2])
		result = nexpose.login(sys.argv[3], sys.argv[4])
		print(nexpose.scan_site('2'))
		nexpose.logout()
	except Exception as e:
		try:
			nexpose.logout()
		except:
			pass
		raise e
