from django.urls import path
from apps.web.views import auction

urlpatterns = [
    path('auction/list/', auction.auction_list, name='auction_list'), # 这里的name是为了方便在html中引用，否则url写出来太长了
    path('auction/add/', auction.auction_add, name='auction_add'),
    path('auction/edit/<int:pk>', auction.auction_edit, name='auction_edit'),
    path('auction/delete/<int:pk>', auction.auction_delete, name='auction_delete'),
    
    path('auction/item/list/<int:auction_id>', auction.auction_item_list, name='auction_item_list'),
    path('auction/item/add/<int:auction_id>', auction.auction_item_add, name='auction_item_add'),
    path('auction/item/edit/<int:auction_id>/<int:item_id>', auction.auction_item_edit, name='auction_item_edit'),
    path('auction/item/delete/<int:item_id>', auction.auction_item_delete, name='auction_item_delete'),

    path('auction/item/detail/add/<int:item_id>', auction.auction_item_detail_add, name='auction_item_detail_add'),
    path('auction/item/detail/add/one/<int:item_id>', auction.auction_item_detail_add_one, name='auction_item_detail_add_one'),
    path('auction/item/detail/delete/one/', auction.auction_item_detail_delete_one, name='auction_item_detail_delete_one'),

    path('auction/item/image/add/<int:item_id>', auction.auction_item_image_add, name='auction_item_image_add'),
    path('auction/item/image/add/one/<int:item_id>', auction.auction_item_image_add_one, name='auction_item_image_add_one'),
    path('auction/item/image/delete/one/', auction.auction_item_image_delete_one, name='auction_item_image_delete_one'),

    path('coupon/list/', auction.coupon_list, name='coupon_list'), 
    path('coupon/add/', auction.coupon_add, name='coupon_add'), 
    path('coupon/edit/<int:pk>', auction.coupon_edit, name='coupon_edit'),
    path('coupon/delete/<int:pk>', auction.coupon_delete, name='coupon_delete'),
]

