# coding=utf-8
"""URLs for GeoContext app."""

from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

from geocontext.views import (
    ContextServiceRegistryList,
    ContextServiceRegistryDetail,
    ContextCacheList,
    ContextValueGeometryList,
    collection_value_list,
    ContextGroupValueView,
    get_context
)

urlpatterns = [
    url(regex=r'^geocontext/$',
        view=get_context,
        name='geocontext-retrieve'),
]

urlpatterns_api = [
    # Context Service Registry
    url(regex=r'^geocontext/csr/$',
        view=ContextServiceRegistryList.as_view(),
        name='context-service-registry-list'
        ),
    url(regex=r'^geocontext/csr/(?P<key>[\w-]+)/$',
        view=ContextServiceRegistryDetail.as_view(),
        name='context-service-registry-detail'
        ),
    # Context Cache
    url(regex=r'^geocontext/cache/$',
        view=ContextCacheList.as_view(),
        name='context-cache-list'
        ),
    url(regex=r'^geocontext/value/list/'
              r'(?P<x>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<y>[+-]?[0-9]+[.]?[0-9]*)/$',
        view=ContextValueGeometryList.as_view(),
        name='context-value-list-all'
        ),
    url(regex=r'^geocontext/value/list/'
              r'(?P<x>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<y>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<csr_keys>[\w\-,]+)/$',
        view=ContextValueGeometryList.as_view(),
        name='context-value-list-csr'
        ),
    url(regex=r'^geocontext/value/collection/'
              r'(?P<x>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<y>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<collection_key>[\w\-,]+)/$',
        view=collection_value_list,
        name='context-collection-list'
        ),
    url(regex=r'^geocontext/value/group/'
              r'(?P<x>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<y>[+-]?[0-9]+[.]?[0-9]*)/'
              r'(?P<context_group_key>[\w\-,]+)/$',
        view=ContextGroupValueView.as_view(),
        name='context-group-list'
        ),
]

urlpatterns_api = format_suffix_patterns(urlpatterns_api)

urlpatterns += urlpatterns_api
