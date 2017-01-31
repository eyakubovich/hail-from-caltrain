from __future__ import absolute_import
import gevent.monkey

gevent.monkey.patch_all()

from app import app, settings


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=settings.PORT,
        debug=settings.DEBUG)
