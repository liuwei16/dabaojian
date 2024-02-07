"""
URL configuration for dabaojian project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from apps.api.views import news, auth, celery_demo, auction, coupon, order

urlpatterns = [
    path('topic/', news.TopicView.as_view()),
    path('news/', news.NewsView.as_view()),
    path('news/<int:pk>', news.NewsDetailView.as_view()), # django2.0开始都推荐使用path而非url来定义url模式
    path('comment/', news.CommentView.as_view()),
    path('favor/', news.FavorView.as_view()),

    path('message/', auth.MessageView.as_view()),
    path('login/', auth.LoginView.as_view()),
    
    path('create/', celery_demo.create_task),
    path('get/', celery_demo.get_result),

    # 拍卖
    path('auction/', auction.AuctionView.as_view()),
    path('auction/<int:pk>', auction.AuctionDetailView.as_view()),
    path('auction2/', auction.Auction2View.as_view({'get': 'list'})),
    path('auction2/<int:pk>', auction.Auction2View.as_view({'get':'retrieve'})),
    path('auction/item/<int:pk>', auction.AuctionItemDetailView.as_view()),
    path('auction/deposit/<int:pk>', auction.AuctionDepositView.as_view()),
    path('auction/bid/', auction.BidView.as_view()),
    # 优惠券
    path('coupon/', coupon.CouponView.as_view()),
    path('user/coupon/', coupon.UserCouponView.as_view()),
    path('choose/coupon/', coupon.ChooseCouponView.as_view()),
    # 订单
    path('order/', order.OrderView.as_view()),
    path('pay/<int:pk>', order.PayView.as_view()),
    path('pay/now/', order.PayNowView.as_view()),
    path('address/', order.AddressView.as_view()),
]

