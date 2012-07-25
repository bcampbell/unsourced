#!/bin/bash

VIRTUAL_ENV=$1
if [ -z $VIRTUAL_ENV ]; then
  echo "usage: $0 </path/to/virtualenv> <cmds>"
  exit 1
fi

. $VIRTUAL_ENV/bin/activate
shift 1
exec "$@"
deactivate

