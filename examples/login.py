#!/usr/bin/python3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from nexpose import Nexpose

if __name__ == '__main__':
	# Usage: ./nexpose.py hostname port username password
	nexpose = Nexpose(sys.argv[1], sys.argv[2])
	result = nexpose.login(sys.argv[3], sys.argv[4])
	if nexpose.session_id:
		print(nexpose.session_id)
		nexpose.logout()
