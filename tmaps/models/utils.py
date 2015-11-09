import shutil
import os.path as p
import os
from sqlalchemy import event

from flask import current_app

from tmaps.extensions.encrypt import encode
from tmaps.extensions.database import db


def auto_generate_hash(cls):
    """
    Class decorator to add an 'after_insert' event listener.
    Whenever an instance of the class is created and added to the database,
    the 'id' attribute is hashed and saved in the 'hash' attribute (String).
    Make sure that the decorated class actually has a hash attribute. E.g.:

    @auto_generate_hash
    SomeClassWhoseIdShouldBeHashed(db.Model):
        ...
        id = db.Column(db.Integer, primary_key=True)
        hash = db.Column(db.String(20))
        ...

    """
    def after_insert_callback(mapper, connection, target):
        tbl = mapper.local_table
        connection.execute(
            tbl.update().\
                values(hash=encode(target.id)).\
                where(tbl.c.id == target.id)
        )
    event.listen(cls, 'after_insert', after_insert_callback)
    return cls


def auto_remove_directory(get_location_func):
    """
    @auto_remove_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_delete_callback(mapper, connection, target):
            loc = get_location_func(target)
            try:
                shutil.rmtree(loc)
            except OSError:
                current_app.logger.warn('Can\'t remove dir, no such location: %s' % loc)

        event.listen(cls, 'after_delete', after_delete_callback)
        return cls
    return class_decorator


def auto_create_directory(get_location_func):
    """
    @auto_create_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            loc = get_location_func(target)
            if not p.exists(loc):
                os.mkdir(loc)
            else:
                print 'WARNING: Tried to create location %s but it exists already!' % loc
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


def exec_func_after_insert(func):
    """
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator
