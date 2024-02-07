"""
初始化动态表，在动态表中添加一些数据，方便操作
"""
import os
import sys
import django
import datetime
from datetime import timedelta

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dabaojian.settings")
django.setup()

from apps.api import models

def create_user_news():
    # init users
    for i in range(20):
        models.UserInfo.objects.create(
            telephone='1513125555',
            nickname='大卫-{0}'.format(i),
            avatar='https://gd-hbimg.huaban.com/9e045769002addcb820937a095775d50251f48034f634-Nlzmm5'
        )
    # init topic
    models.Topic.objects.create(title="春运")
    models.Topic.objects.create(title="火车票")
    # init news
    for i in range(1, 37):
        news_object = models.News.objects.create(
            cover="https://gd-hbimg.huaban.com/0b990e5c0c29ec577de9002922ea0b127775209b2a3f0-77CnS8_fw192webp",
            content=f'还有{i}天就放假',
            topic_id=1,
            user_id=1
        )
        models.NewsDetail.objects.create(
            key="0b990e5c0c29ec577de9002922ea0b127775209b2a3f0-77CnS8_fw192webp",
            cos_path='https://gd-hbimg.huaban.com/0b990e5c0c29ec577de9002922ea0b127775209b2a3f0-77CnS8_fw192webp',
            news=news_object
        )
    # init viewer
    models.ViewerRecord.objects.create(user_id=1,news_id=36)
    models.ViewerRecord.objects.create(user_id=2,news_id=36)
    models.ViewerRecord.objects.create(user_id=3,news_id=36)
    models.ViewerRecord.objects.create(user_id=10,news_id=36)
    models.ViewerRecord.objects.create(user_id=5,news_id=36)
    # init comment
    first1 = models.CommentRecord.objects.create(
        news_id=36,
        content="1",
        user_id=1,
        depth=1
    )

    first1_1 = models.CommentRecord.objects.create(
        news_id=36,
        content="1-1",
        user_id=6,
        reply=first1,
        depth=2,
        root=first1
    )

    first1_1_1 = models.CommentRecord.objects.create(
        news_id=36,
        content="1-1-1",
        user_id=10,
        reply=first1_1,
        depth=3,
        root=first1
    )

    first1_1_2 = models.CommentRecord.objects.create(
        news_id=36,
        content="1-1-2",
        user_id=14,
        reply=first1_1,
        depth=3,
        root=first1
    )


    first1_2 = models.CommentRecord.objects.create(
        news_id=36,
        content="1-2",
        user_id=8,
        reply=first1,
        depth=2,
        root=first1
    )

    first2 = models.CommentRecord.objects.create(
        news_id=36,
        content="2",
        user_id=3,
        depth=1
    )

    first3 = models.CommentRecord.objects.create(
        news_id=36,
        content="3",
        user_id=4,
        depth=1
    )

def create_auction():
    current_datetime = datetime.datetime.now()
    auction_object = models.Auction.objects.create(
        title='第一场 烟酒',
        cover="https://auction-1251317460.cos.ap-chengdu.myqcloud.com/23bf0e42-d9ff-44a4-9418-1b9e01ebbb61.png",
        preview_start_time=current_datetime,
        preview_end_time=current_datetime + timedelta(hours=5),
        auction_start_time=current_datetime + timedelta(hours=5),
        auction_end_time=current_datetime + timedelta(hours=7),
        deposit=1200,
        goods_count=2
    )

    item1_object = models.AuctionItem.objects.create(
        auction=auction_object,
        uid="202011111111",
        title='茅台',
        cover="https://auction-1251317460.cos.ap-chengdu.myqcloud.com/23bf0e42-d9ff-44a4-9418-1b9e01ebbb61.png",
        start_price=1499,
        reserve_price=1000,
        highest_price=2800,
        deposit=200,
        unit=100
    )

    image1_object = models.AuctionItemImage.objects.create(
        item=item1_object,
        img="https://auction-1251317460.cos.ap-chengdu.myqcloud.com/23bf0e42-d9ff-44a4-9418-1b9e01ebbb61.png",
        carousel=True,
        order=1
    )
    image2_object = models.AuctionItemImage.objects.create(
        item=item1_object,
        img="https://auction-1251317460.cos.ap-chengdu.myqcloud.com/23bf0e42-d9ff-44a4-9418-1b9e01ebbb61.png",
        carousel=True,
        order=2
    )
    image3_object = models.AuctionItemImage.objects.create(
        item=item1_object,
        img="https://auction-1251317460.cos.ap-chengdu.myqcloud.com/23bf0e42-d9ff-44a4-9418-1b9e01ebbb61.png",
        carousel=False,
        order=3
    )

    detail1_object = models.AuctionItemDetail.objects.create(item=item1_object,key='品牌',value='茅台')
    detail2_object = models.AuctionItemDetail.objects.create(item=item1_object, key='年份', value='1800')

def create_bid_record():
    models.BidRecord.objects.create(item_id=1,user_id=1,price=1000)
    models.BidRecord.objects.create(item_id=1,user_id=1,price=1200)
if __name__ == '__main__':
    create_auction()
    # create_bid_record()
