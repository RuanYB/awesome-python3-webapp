#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment
'''

__author__ = 'Ryan Ruan'

import time, uuid
 
from orm import Model, StringField, BooleanField, FloatField, TextField

#生成唯一标识符，取自当前时间的15位的整数+uuid随机生成的标识
def next_id():
	return '%015d%s000' % (int(time.time()*1000), uuid.uuid4().hex)

class User(Model):
	__table__ = 'users'

	#缺省值可以作为函数对象传入，在调用save()自动计算
	#id, email, password, admin yes or no, name, image, create time
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	email = StringField(ddl='varchar(50)')
	passwd = StringField(ddl='varchar(50')
	admin = BooleanField()
	name = StringField(ddl='varchar(50)')
	image = StringField(ddl='varchar(50)')
	#创建时间的缺省值是函数
	create_at = FloatField(default='time.time')

class Blog(Model):
	__table__ = 'blogs'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	user_image = StringField(ddl='varchar(500)')
	name = StringField(ddl='varchar(50)')
	summary = StringField(ddl='varchar(200)')
	content = TextField()
	create_at = StringField(default=time.time)

class Comment(Model):
	__table__ = 'comments'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	blog_id = StringField(ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	user_name = StringField(ddl='varchar(50)')
	user_image = StringField(ddl='varchar(500)')
	content = TextField()
	create_at = FloatField(default=time.time)


