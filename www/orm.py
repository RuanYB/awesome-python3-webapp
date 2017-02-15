#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ryan ruan'

import asyncio, logging

import aiomysql

def log(sql, args=()):
	logging.info('SQL: %s' % sql)

# 创建一个全局的连接池，每个HTTP请求都从池中获得数据库连接
@asyncio.coroutine
def create_pool(loop, **kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = yield from aiomysql.create_pool(
		host = kw.get('host', 'localhost'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
		)

#SELECT statement: return result set
@asyncio.coroutine
def select(sql, args, size=None):
	log(sql, args)
	global __pool
	with (yield from __pool) as conn:
		#create dict cursor
		cur = yield from conn.cursor(aiomysql.DictCursor)
		#execute sql query
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()
		yield from cur.close()
		logging.info('rows returned: %s' % len(rs))
		return rs

#INSERT, UPDATE, DELETE statement: return result count
@asyncio.coroutine
def execute(sql, args):
	log(sql)
	with (yield from __pool) as conn:
		try:
			# execute类型的SQL操作返回的结果只有行号，所以不需要用DictCursor
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			yield from cur.close()
		except BaseException as e:
			raise
		return affected

#定义Field类，负责保存（数据库）表的字段名和字段类型
class Field(object):

	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

#定义不同的衍生Field
class StringField(Field):

	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

	def __init__(self, name=None, default=None):
		super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name, 'real', primary_key, default)

class TextField(Field):

	def __init__(self, name=None, default=None):
		super().__init__(name, 'Text', False, default)


#定义Model的元类
# ModelMetaclass元类定义了所有Model基类(继承ModelMetaclass)的子类实现的操作
# -*-ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备：
# ***读取具体子类(user)的映射信息
# -*-在当前类中查找所有的类属性(attrs)，如果找到Field属性，就将其保存到__mappings__
# ***的dict中，同时从类属性中删除Field(防止实例属性遮住类的同名属性)
# 将数据库表名保存到__table__中
# 完成这些工作就可以在Model中定义各种数据库的操作方法
class ModelMetaClass(type):

	# __new__控制__init__的执行，所以在其执行之前
    # cls:代表要__init__的类，此参数在实例化时由Python解释器自动提供
	def __new__(cls, name, bases, attrs):
		#排除Model类本身
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)

		#获取table名称
		tableName = attrs.get('__table__', None) or name
		logging.info('found model: %s (table: %s)' % (name, tableName))

		#获取所有的Field和主键名
		mappings = dict()
		fields = []
		primaryKey = None
		for k,v in attrs.items():
			#Field属性
			if isinstance(v, Field):
			#k是类的一个属性，v是这个属性在数据库中对应的Field列表属性
			logging.info('found mapping: %s --> %s' % (k, v))
			mappings[k] = v
			#找到主键
			if v.primaryKey:
				#如果此时类实例已经存在主键，说明主键重复了
				if primaryKey:
					raise StandardError('Duplicate primary key for field: %s' % k)
				#否则将此列设为列表的主键
				primaryKey = k
			else:
				fields.append(k)
		#end for 

		if not primaryKey:
			raise StandardError('primary Key is not found')

		#从类属性中删除Field属性
		for k in mappings.keys():
			attrs.pop(k)

		#保存除了主键之外的属性名，转成``列表形式
		escaped_fields = list(map(lambda f : '`%s`' % f, fields))

		#保存属性和列的映射关系
		attrs['__mappings'] = mappings
		#保存表名
		attrs['__table__'] = tableName
		#保存主键属性名
		attrs['__primary_key__'] = primaryKey
		#保存除主键之外的属性名
		attrs['__fields__'] = fields

		#构造默认的SELECT、INSERT、UPDATE、DELETE语句
		#反引号``功能同repr()
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values(%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set `%s` where `%s`=?' % (tableName, ','.join(map(lambda f:'`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)

		return type.__new__(cls, name, bases, attrs)


#Define Model
class Model(dict, metaclass=ModelMetaClass):

	def __init__(self, **kw):
		super(Model, self).__init__(self, **kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value



			
