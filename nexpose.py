#!/usr/bin/python3
import defusedxml.ElementTree as ET
import urllib.request
import urllib.parse
import sys
import ssl

__author__ = 'Nick Levesque <nick@portcanary.com>'

class Nexpose:
	'''
	Nexpose API wrapper.
	'''
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

	def api_request(self, xml_string):
		'''Send an API request and return the response\'s root XML element.'''
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

	def login(self, username, password):
		'''Send a LoginRequest and capture the returned session-id.'''
		xml_string = '<LoginRequest user-id=\"%s\" password=\"%s\" />'\
					% (username, password)
		xml_response = self.api_request(xml_string)
		self.session_id = xml_response.attrib.get('session-id')
		return xml_response

	def logout(self):
		'''Send a LogoutRequest.'''
		xml_string = "<LogoutRequest session-id=\"%s\" />" % (self.session_id)
		xml_response = self.api_request(xml_string)
		return xml_response

	def get_sites(self):
		'''Return a list of dicts containing site information.'''
		xml_string = '<SiteListingRequest session-id=\"%s\">\
					</SiteListingRequest>' % self.session_id
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
		'''Return list of ranges and hostnames associated with a site.'''
		xml_string = '<SiteConfigRequest session-id=\"%s\" site-id=\"%s\">\
					</SiteConfigRequest>' % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		host_list = []
		site = xml_response.find('Site')
		hosts = site.find('Hosts')
		for host in hosts.getchildren():
			if host.tag == 'range':
				if host.attrib.get('to') is None:
					host_list.append({'range' : host.attrib.get('from')})
				else:
					host_list.append({'range' : ('%s-%s' % \
							(host.attrib.get('from'), host.attrib.get('to')))})
			elif host.tag == 'host':
				host_list.append({'host' : host.text})
		return host_list

	def get_site_scan_config(self, site_id):
		'''Return a dict of configuration info for a site.'''
		xml_string = '<SiteConfigRequest session-id=\"%s\" site-id=\"%s\">\
					</SiteConfigRequest>' % (self.session_id, site_id)
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
		
	def get_scan_summary_attributes(self, scan_id, engine_id):
		'''
		Send a ScanStatisticsRequest and return the ScanSummary 
		attributes as a dict.
		'''
		xml_string = '<ScanStatisticsRequest session-id = \"%s\" \
					engine-id = \"%s\" scan-id = \"%s\">\
					</ScanStatisticsRequest>' % \
					(self.session_id, engine_id, scan_id)
		xml_response = self.api_request(xml_string)
		scan_summary = xml_response.find('ScanSummary')
		scan_summary_attributes = {}
		for key in scan_summary.attrib:
			scan_summary_attributes[key] = scan_summary.attrib[key]
		return scan_summary_attributes
		

	def scan_site(self, site_id):
		'''Send SiteScanRequest and return dict of scan id and engine id.'''
		xml_string = '<SiteScanRequest session-id = \"%s\" site-id=\"%s\">\
					</SiteScanRequest>' % (self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		scan = xml_response.find('Scan')
		scan_id = scan.attrib.get('scan-id')
		engine_id = scan.attrib.get('engine-id')
		return {'scan_id' : scan_id, 'engine_id' : engine_id}

	def get_site_devices(self, site_id):
		'''Return a list of devices in a site.'''
		xml_string = '<SiteDeviceListingRequest session-id = \"%s\" \
					site-id = \"%s\"></SiteDeviceListingRequest>' % \
					(self.session_id, site_id)
		xml_response = self.api_request(xml_string)
		print(ET.tostring(xml_response, encoding='ascii', method='xml'))

	def scan_site_hosts(self, site_id, host_list):
		'''
		Send SiteDevicesScanRequest and return dict of scan id and engine
		id. host_list is a list of ranges or hostnames as get_site_hosts()
		would return.
		'''
		hosts_string = ''
		for host in host_list:
			ip_range = host.get('range')
			if ip_range is not None:
				split_ip_range = ip_range.split('-')
				if len(split_ip_range) == 1:
					hosts_string += ('<range from=\"%s\"/>' % \
										str(split_ip_range[0]))
				elif len(split_ip_range) == 2:
					hosts_string += ('<range from=\"%s\" to=\"%s\"/>' % \
										(split_ip_range[0],
										split_ip_range[1]))
				else:
					raise Exception('Invalid IP range: %s' % ip_range)
			else:
				hostname = host.get('host')
				hosts_string += ('<host %s/>' % hostname)
				
		xml_string = '<SiteDevicesScanRequest session-id=\"%s\" \
					site-id=\"%s\"><Devices></Devices><Hosts>%s</Hosts>\
					</SiteDevicesScanRequest>' % (self.session_id,
												site_id,
												hosts_string)
		xml_response = self.api_request(xml_string)
		scan = xml_response.find('Scan')
		scan_id = scan.attrib.get('scan-id')
		engine_id = scan.attrib.get('engine-id')
		return {'scan_id': scan_id, 'engine_id' : engine_id}

if __name__ == '__main__':
	# Usage: ./nexpose.py hostname port username password
	try:
		nexpose = Nexpose(sys.argv[1], sys.argv[2])
		nexpose.login(sys.argv[3], sys.argv[4])
		print(nexpose.get_scan_summary_attributes('14', '3'))
	except urllib.error.URLError as e:
		print("URLError: Perhaps you entered the wrong URL or port?")
		exit()
	try:
		nexpose.logout()
	except:
		print('Tried to logout when we weren\'t signed in.')
		pass
