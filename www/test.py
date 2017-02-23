import asyncio, sys

import orm

from models import User, Blog, Comment

async def test(loop):
	await orm.create_pool(loop, user='ryan', password='790332099', database='awesome')

	u = User(name='Test1', email='test1@example.com', image='about:blank')

	await u.save()

if __name__=="__main__":
	
	loop = asyncio.get_event_loop()
	loop.run_until_complete(test(loop))
	loop.close()

	if loop.is_closed():
		sys.exit(0)
	
