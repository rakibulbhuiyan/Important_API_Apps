from rest_framework.views import APIView, status
from rest_framework.response import Response




class BaseAPIView(APIView):
    
    def success_response(self, message="Thank you for your request", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status_code": status_code,
            "data": data or []
            }, 
            status=status_code )
        
    def error_response(self, message="I am sorry for your request", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status_code": status_code,
            "data": data or []
            }, 
            status=status_code )




# For searching ,sorting,filtering always use params


# Example usage:
# from django_filters.rest_framework import DjangoFilterBackend
# from rest_framework import filters
# from rest_framework import generics
# class ExampleListView(generics.ListAPIView):
#     queryset = ExampleModel.objects.all()
#     serializer_class = ExampleSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['field1', 'field2']
#     search_fields = ['field1', 'field2']


# for pagination and standardized responses
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

class BaseAPIView(APIView):
    
    def get_paginated_response(self, queryset, serializer_class, request, message="Data fetched successfully"):
        paginator = PageNumberPagination()
        paginator.page_size = int(request.GET.get("page_size", 10))
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serialized_data = serializer_class(paginated_queryset, many=True).data

        return paginator.get_paginated_response({
            "success": True,
            "message": message,
            "status_code": status.HTTP_200_OK,
            "results": serialized_data,
        })
    
    def success_response(self, message="Request successful", data=None, status_code=status.HTTP_200_OK):
        return Response({
            "success": True,
            "message": message,
            "status_code": status_code,
            "data": data or []
        }, status=status_code)
    
    def error_response(self, message="Request failed", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "success": False,
            "message": message,
            "status_code": status_code,
            "data": data or []
        }, status=status_code)



# For searching ,sorting,filtering always use params (advancede )
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone


class CustomPagination(PageNumberPagination):
    """Custom paginator with dynamic page size"""
    page_size_query_param = "page_size"
    max_page_size = 100


class BaseAPIView(APIView):
    """
    Advanced Base APIView for DRF
    Includes:
    - Pagination
    - Filtering, Search, Sorting (DRF filters)
    - Unified Response Format
    - Metadata in all responses
    """

    # Default DRF filters (child class can override)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def success_response(self, message="Request successful", data=None, meta=None, status_code=status.HTTP_200_OK):
        return Response({
            "success": True,
            "message": message,
            "status_code": status_code,
            "meta": meta or {},
            "data": data or []
        }, status=status_code)

    def error_response(self, message="Request failed", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "success": False,
            "message": message,
            "status_code": status_code,
            "meta": {},
            "errors": errors or []
        }, status=status_code)

    def get_filtered_queryset(self, queryset, request, view):
        """Apply filtering, searching and ordering on queryset"""
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, view)
        return queryset

    def get_paginated_response(self, queryset, serializer_class, request, message="Data fetched successfully"):
        paginator = CustomPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serialized_data = serializer_class(paginated_queryset, many=True).data

        meta = {
            "timestamp": timezone.now(),
            "total_records": queryset.count(),
            "page_size": paginator.get_page_size(request),
            "current_page": paginator.page.number,
            "total_pages": paginator.page.paginator.num_pages,
            "filters_applied": {k: v for k, v in request.GET.items() if k not in ["page", "page_size"]},
        }

        return paginator.get_paginated_response({
            "success": True,
            "message": message,
            "status_code": status.HTTP_200_OK,
            "meta": meta,
            "data": serialized_data,
        })
