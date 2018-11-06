egrep -r "salt\\.utils\\.(`egrep '^def ' salt/utils/__init__.py | cut -f2 -d' ' | cut -f1 -d'(' | tr '\n' '|' | sed 's/.$//'`)" . | egrep -v '^Binary' | fgrep -v "salt/utils/__init__.py" | fgrep -v "doc/topics/releases" | fgrep -v "doc/man/salt"

