## rotate-to-s3.py

rotate-to-s3.py does the following to rotate your webserver logs directly to
an Amazon Web Service Simple Storage Service (AWS S3) bucket:

* reads the JSON configuration file
* renames active logfiles
* signals the webserver to logswitch
* compresses old logfiles
* uploads compessed logfiles to an S3 bucket


### How to install

	git clone git://github.com/dialt0ne/rotate-to-s3.git
	cd rotate-to-s3
	sudo mkdir -p /opt/corsis/bin
	sudo cp rotate-to-s3.py /opt/corsis/bin
	sudo mkdir -p /opt/corsis/etc
	sudo cp rotate-to-s3.json /opt/corsis/etc/example_com.json

### Configuration

	cd /opt/corsis/etc
	sudo $EDITOR example_com.json
	# customize as needed

	sudo crontab -e
	#>>>
	0 * * * * /opt/corsis/bin/rotate-to-s3.py -c /opt/corsis/etc/example_com.json

### Usage

	$ ./rotate-to-s3.py -h
	usage: rotate-to-s3.py [-h] [-c CONFIG]

	optional arguments:
	  -h, --help            show this help message and exit
	  -c CONFIG, --config CONFIG
				json config file, default: rotate-to-s3.json

### License

Copyright 2012 Corsis
http://www.corsis.com/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

