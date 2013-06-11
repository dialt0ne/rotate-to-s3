## rotate-to-s3.py

rotate-to-s3.py does the following to rotate your webserver logs from your
Amazon Web Service Elastic Compute Cloud (AWS EC2) instance directly to
an Amazon Web Service Simple Storage Service (AWS S3) bucket:

* reads the JSON configuration file
* renames active logfiles
* signals the webserver to logswitch
* compresses old logfiles
* uploads compessed logfiles to an S3 bucket

So, if the logfile is named `access.log` it will be rotated to S3 with
the name `90abcdef-YYYYMMDD-HHMMSS-access.log.gz` where `90abcdef` is the
EC2 instance ID of the system, without the leading `i-` (see this
[blog post](http://aws.typepad.com/aws/2012/03/amazon-s3-performance-tips-tricks-seattle-hiring-event.html) why).

If the init script is installed, it will also move the logs to S3 on
shutdown or reboot so that no logs are lost at instance termination.

### How to install

#### Ubuntu system

	git clone git://github.com/dialt0ne/rotate-to-s3.git
	cd rotate-to-s3
	sudo mkdir -p /opt/corsis/bin
	sudo cp rotate-to-s3.py /opt/corsis/bin
	sudo mkdir -p /opt/corsis/etc
	sudo cp rotate-to-s3.json /opt/corsis/etc
	sudo cp rotate-to-s3 /etc/init.d/rotate-to-s3
	sudo update-rc.d rotate-to-s3 stop 01 0 1 6 .

### Configuration

	cd /opt/corsis/etc
	sudo $EDITOR example_com.json
	# customize as needed

	sudo crontab -e
	#>>>
	0 * * * * /opt/corsis/bin/rotate-to-s3.py -c /opt/corsis/etc/rotate-to-s3.json

### Usage

	$ ./rotate-to-s3.py -h
	usage: rotate-to-s3.py [-h] [-c CONFIG]

	optional arguments:
	  -h, --help            show this help message and exit
	  -c CONFIG, --config CONFIG
				json config file, default: rotate-to-s3.json

### ToDo

* possibly retry on S3 upload issues
* better error handling and reporting

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

