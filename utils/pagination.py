
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
class SplitLimitPagination(LimitOffsetPagination):
    """本质上帮我们进行切片处理"""
    default_limit = 5
    max_limit = 50
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    def get_offset(self, request):
        return 0
    def get_paginated_response(self, data):
        return Response(data)