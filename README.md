Unsourced
=========

Setting up
----------

Unsourced uses [Python](http://www.python.org/), [MySQL](http://www.mysql.com/), and [memcached](http://memcached.org/).

To bootstrap your setup, just run:

    script/bootstrap


Notes
-----

### PIL dependency

On ubuntu 11.10/64bit:

`pip` doesn't install PIL properly under 64bit ubuntu - it misses zlib, libjpeg and libfreetype.
 
Cheesy hack workaround is to install ubuntu PIL package then copy the files into the virtualenv manually:

```bash
$ sudo apt-get install python-imaging
$ cp -r /usr/lib/python2.7/dist-packages/PIL {{VIRTUALENV}}/lib/python2.7/site-packages
```

On Amazon EC2 Linux AMI:

`pip` compiles PIL from source, so make sure all the image format libraries are installed before installing PIL - the missing ones won't be installed and you'll end up with annoying `IOError: decoder jpeg not available` kinds of errors.

```bash
$ sudo yum install libjpeg libjpeg-devel
```


Alternate setup (debian/ubuntu):
-------------------------------

```bash
$ sudo apt-get install python-virtualenv
$ sudo apt-get install libpng-dev libgif-dev libjpeg-dev libmysqlclient-dev

(assumes you've got mysql etc already installed)

$ mkdir unsourced.org
$ cd unsourced.org
$ git clone https://github.com/bcampbell/unsourced
$ virtualenv --no-site-packages pyenv
$ . pyenv/bin/activate
$ pip install --upgrade distribute
$ pip install -r unsourced/requirements.txt

$ git clone https://github.com/bcampbell/decruft.git
$ git clone https://github.com/bcampbell/metareadability.git
$ ln -s $PWD/decruft/decruft unsourced/scrapeomat/
$ ln -s $PWD/metareadability/metareadability unsourced/scrapeomat/

$ mkdir uploads
```

then:

make sure uploads dir is writable by server
mysqladmin create
customise config.py and alembic.ini

```bash
 python unsourced/app.py
 python unsourced/scrapomat.py
```

Production site runs behind Nginx, and uses supervisord to manage processes.
See sample config files in config/

The Debian Squeeze packages for nginx are a bit stale. Nginx.org has more
recent packages available.



