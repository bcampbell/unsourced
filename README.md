Unsourced
=========

Environment Dependencies
------------------------

Unsourced uses [Python](http://www.python.org/), [MySQL](http://www.mysql.com/), and [memcached](http://memcached.org/).

If you encounter any problems installing the following, refer to the Notes section at the bottom.

Set up [virtualenv](http://www.virtualenv.org/) and related packages:

```bash
$ sudo easy_install virtualenv
$ virtualenv --no-site-packages pyenv
$ source pyenv/bin/activate
$ pip install tornado lxml WTForms SQLAlchemy \
    python-dateutil rdflib rdfextras py-bcrypt \
    alembic PIL pylibmc python-memcached dogpile.cache \
    MySQL-python
```

Install the [fuzzydate](https://github.com/bcampbell/fuzzydate) Python package:

```bash
$ pip install git+https://github.com/bcampbell/fuzzydate.git
```

TODO: supply pip requirements file

Setup
-----

Clone the following repositories:

```bash
$ git clone git@github.com:bcampbell/unsourced.git
$ git clone git@github.com:bcampbell/metareadability.git
$ git clone git@github.com:bcampbell/decruft.git
```

TODO: pack up metareadability and decruft into pip-installable form.

For now, just symlink 'em into `unsourced/scrapomat`:

```bash
$ ln -s metareadability/metareadability unsourced/scrapeomat/metareadability
$ ln -s decruft/decruft unsourced/scrapeomat/decruft
```

Configuration
-------------

Copy the configuration files and update them to suit your needs.

From within the `unsourced` repository:

```bash
$ cp unsourced/config.py.EXAMPLE unsourced/config.py # now edit this file
$ cp unsourced/alembic.ini.EXAMPLE unsourced/alembic.ini # now edit this file
```

TODO: Add notes on nginx and supervisor config

Notes
-----

### pylibmc and python-memcached

You don't need both `pylibmc` and `python-memcached` -- the former is probably faster,
but is more prone to package version mismatches.


### lxml

`lxml` requires compiler and headers from Python, libxml2 and libxslt.

Using `apt`:

```bash
$ sudo apt-get install python-dev libxml2-dev libxslt-dev
```

Using `yum`:

```bash
$ sudo yum install python26-devel libxml2 libxml2-devel libxslt libxslt-devel
```

### mysql-python

MySQL-python requires mysql headers.

Using `apt`:

```bash
$ sudo apt-get install libmysqlclient-dev
```

Using `yum`:

```bash
$ sudo yum install mysql-devel
```

### Installing PIL

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

TODO: gif? png?
