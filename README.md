## rotate-to-s3.py

rotate-to-s3.py does the following to rotate your webserver logs directly to
an Amazon Web Service Simple Storage Service (AWS S3) bucket:

* reads the JSON configuration file
* renamed active logfiles
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

