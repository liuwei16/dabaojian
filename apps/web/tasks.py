import itertools
import uuid
import datetime
from celery import shared_task
from apps.api import models
from utils.encrypt import md5

@shared_task
def to_preview_status_task(auction_id):
    models.Auction.objects.filter(id=auction_id).update(status=2)
    models.AuctionItem.objects.filter(auction_id=auction_id).update(status=2)

@shared_task
def to_auction_status_task(auction_id):
    models.Auction.objects.filter(id=auction_id).update(status=3)
    models.AuctionItem.objects.filter(auction_id=auction_id).update(status=3)

@shared_task
def end_auction_task(auction_id):
    models.Auction.objects.filter(id=auction_id).update(status=4)
    # models.AuctionItem.objects.filter(auction_id=auction_id).update(status=4)
    # 商品状态可能成交or流拍
    total = 0
    total_unfortunate_list = []
    lucky_auction_deposit_id = set()
    auction_object = models.Auction.objects.filter(id=auction_id).first() # 找到专场
    if not auction_object:
        return 
    item_object_list = models.AuctionItem.objects.filter(auction_id=auction_id) # 找到专场所有商品
    for item_object in item_object_list:
        # 获取出价最高的记录
        lucky_object = models.BidRecord.objects.filter(item=item_object).order_by('-price').first()
        # 无出价则流拍
        if not lucky_object:
            item_object.status = 5
            item_object.save()
            continue

        item_object.status = 4 # 先将竞价记录改为成交
        item_object.deal_price = lucky_object.price
        item_object.save()

        lucky_object.status = 2
        lucky_object.save() 
        total += lucky_object.price

        # 获取当前用户缴纳保证金的情况--如果是单品保证金
        deposit_object = models.DepositRecord.objects.filter(
            user=lucky_object.user, 
            item=item_object,
            deposit_type=1
        ).first()
        if not deposit_object: # 则为全场保证金
            deposit_object = models.DepositRecord.objects.filter(
                user=lucky_object.user, 
                auction=auction_object,
                deposit_type=2,
                item__isnull=True
            ).first()
            ## debug:这里应该把两种类型的保证金情况都存下来么
            lucky_auction_deposit_id.add(deposit_object)
        # 生成订单-待支付
        order_object = models.Order.objects.create(
            status=1,
            uid=md5(str(uuid.uuid4())),
            user=lucky_object.user,
            item=item_object,
            deposit=deposit_object, # 保证金记录
            price=lucky_object.price,
        )
        # 单品保证金中：所有没有拍到商品 且 缴纳的是单品保证金 需要立即退款
        item_unfortunate_list = models.DepositRecord.objects.filter(item=item_object, deposit_type=1).exclude(
            user=lucky_object.user)
        total_unfortunate_list.extend(item_unfortunate_list)
        # 调用定时任务：24小时内要支付，否则流拍扣除保证金。
        # date = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        date = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        task_id = twenty_four_hour.apply_async(args=[order_object.id], eta=date).id # 24h后执行
        order_object.twenty_four_task_id = task_id
        order_object.save()
    # 专场：更新成交额
    auction_object.total_price = total
    auction_object.save()
    # 未拍到任何商品的用户的全场保证金
    auction_unfortunate_list = models.DepositRecord.objects.filter(
        deposit_type=2,
        auction=auction_object,
        item__isnull=True).exclude(id__in=lucky_auction_deposit_id)
    # 退保证金（原路退还）
    for deposit in itertools.chain(total_unfortunate_list, auction_unfortunate_list):
        uid = md5(str(uuid.uuid4()))  # 正确，
        if deposit.pay_type == 1:  # 微信
            # res = refund(uid, deposit.uid, deposit.amount, deposit.amount)
            res = True
            models.DepositRefundRecord.objects.create(
                uid=uid,
                status=2 if res else 1,
                amount=deposit.amount,
                deposit=deposit
            )
            if res:
                deposit.balance = 0
                deposit.save()
        else:  # 余额
            deposit.user.balance += deposit.amount
            deposit.user.save()
            models.DepositRefundRecord.objects.create(
                uid=uid,
                status=2,
                amount=deposit.amount,
                deposit=deposit
            )
            deposit.balance = 0
            deposit.save()
    # 拍卖结束之后，将在之后的第24小时将所有 未使用 的用户优惠券主动过期
    date = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    user_coupon_to_expired.apply_async(args=[auction_id], eta=date)
    
@shared_task
def twenty_four_hour(order_id):
    """24小时不支付 则直接扣除保证金"""
    order_object = models.Order.objects.filter(id=order_id).first()
    # 如果已经支付了 则什么都不执行
    if order_object.status != 1:
        return
    # 订单状态修改为逾期未支付
    order_object.status = 4
    order_object.save()
    order_object.item.status = 4 # 商品状态也要对应修改
    order_object.item.save()
    # 单品保证金直接扣除 并 创建扣除记录
    if order_object.deposit.deposit_type == 1:
        order_object.deposit.balance = 0
        order_object.deposit.save()
        models.DepositDeduct.objects.create(order=order_object, amount=order_object.deposit.amount)
        return
    # 全场保证金，扣除部分保证金（如果有剩余，则检查是否还有其他订单了，没了则剩余保证金直接退回到原账户）
    if order_object.deposit.balance <= order_object.item.deposit:
        models.DepositDeduct.objects.create(order=order_object, amount=order_object.deposit.balance)
        order_object.deposit.balance = 0
        order_object.deposit.save()
        return
    order_object.deposit.balance -= order_object.item.deposit
    order_object.deposit.save()
    models.DepositDeduct.objects.create(order=order_object, amount=order_object.item.deposit)
    # 检查此专场保证金下是否还有其他订单未支付
    exists = models.Order.objects.filter(user=order_object.user,
                                         status=1,
                                         item__auction_id=order_object.deposit.auction).exclude(id=order_id).exists()
    if exists:
        return

    uid = md5(str(uuid.uuid4()))
    if order_object.deposit.pay_type == 1:  # 微信
        # res = refund(uid, deposit.uid, deposit.amount, deposit.amount)
        res = True
        models.DepositRefundRecord.objects.create(
            uid=uid,
            status=2 if res else 1,
            amount=order_object.deposit.balance,
            deposit=order_object.deposit
        )
        if res:
            order_object.deposit.balance = 0
            order_object.deposit.save()
    else:  # 余额
        order_object.deposit.user.balance += order_object.deposit.balance
        order_object.deposit.user.save()
        models.DepositRefundRecord.objects.create(
            uid=uid,
            status=2,
            amount=order_object.deposit.balance,
            deposit=order_object.deposit
        )
        order_object.deposit.balance = 0
        order_object.deposit.save()

@shared_task
def coupon_start_apply(coupon_id):
    models.Coupon.objects.filter(id=coupon_id, status=1).update(status=2)

@shared_task
def coupon_stop_apply(coupon_id):
    models.Coupon.objects.filter(id=coupon_id, status=2).update(status=3)

@shared_task
def user_coupon_to_expired(auction_id):
    models.UserCoupon.objects.filter(coupon__auction_id=auction_id, status=1).update(status=3)