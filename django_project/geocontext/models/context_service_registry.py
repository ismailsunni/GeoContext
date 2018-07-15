# coding=utf-8
"""Context Service Registry Model."""

import requests
from datetime import datetime, timedelta
import pytz
from xml.dom import minidom

from owslib.wms import WebMapService

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.http import QueryDict

from geocontext.utilities import (
    convert_coordinate, parse_gml_geometry, get_bbox)


class ContextServiceRegistry(models.Model):
    """Context Service Registry"""

    WFS = 'WFS'
    WCS = 'WCS'
    WMS = 'WMS'
    REST = 'REST'
    WIKIPEDIA = 'Wikipedia'
    QUERY_TYPES = (
        (WFS, 'WFS'),
        (WCS, 'WCS'),
        (WMS, 'WMS'),
        (REST, 'REST'),
        (WIKIPEDIA, 'Wikipedia'),
    )

    key = models.CharField(
        help_text=_('Key of Context Service.'),
        blank=False,
        null=False,
        max_length=200,
        unique=True,
    )

    name = models.CharField(
        help_text=_('Name of Context Service.'),
        blank=False,
        null=False,
        max_length=200,
    )

    description = models.CharField(
        help_text=_('Description of Context Service.'),
        blank=True,
        null=True,
        max_length=1000,
    )

    url = models.CharField(
        help_text=_('URL of Context Service.'),
        blank=False,
        null=False,
        max_length=1000,
    )

    user = models.CharField(
        help_text=_('User name for accessing Context Service.'),
        blank=True,
        null=True,
        max_length=200,
    )

    password = models.CharField(
        help_text=_('Password for accessing Context Service.'),
        blank=True,
        null=True,
        max_length=200,
    )

    api_key = models.CharField(
        help_text=_('API key for accessing Context Service.'),
        blank=True,
        null=True,
        max_length=200,
    )

    query_url = models.CharField(
        help_text=_('Query URL for accessing Context Service.'),
        blank=True,
        null=True,
        max_length=1000,
    )

    query_type = models.CharField(
        help_text=_('Query type of the Context Service.'),
        blank=False,
        null=False,
        max_length=200,
        choices=QUERY_TYPES
    )

    # I will try to use CharField first, if not I will use django-regex-field
    result_regex = models.CharField(
        help_text=_('Regex to retrieve the desired value.'),
        blank=False,
        null=False,
        max_length=200,
    )

    time_to_live = models.IntegerField(
        help_text=_(
            'Time to live of Context Service to be used in caching in '
            'seconds unit.'),
        blank=True,
        null=True,
        default=604800  # 7 days
    )

    srid = models.IntegerField(
        help_text=_('The Spatial Reference ID of the service registry.'),
        blank=True,
        null=True,
        default=4326
    )

    layer_typename = models.CharField(
        help_text=_('Layer type name to get the context.'),
        blank=False,
        null=False,
        max_length=200,
    )

    service_version = models.CharField(
        help_text=_('Version of the service (e.g. WMS 1.1.0, WFS 2.0.0).'),
        blank=False,
        null=False,
        max_length=200,
    )

    def __str__(self):
        return self.name

    def retrieve_context_value(self, x, y, srid=4326):
        """Retrieve context from a location.

        :param x: The value of x coordinate.
        :type x: float

        :param y: The value of y coordinate.
        :type y: float

        :param srid: The srid of the coordinate.
        :type srid: int

        :
        """
        if self.query_type == ContextServiceRegistry.WMS:
            wms = WebMapService(self.url, self.service_version)
            response = wms.getfeatureinfo(
                layers=[self.layer_typename],
                bbox=get_bbox(x, y),
                size=[101, 101],
                xy=[50, 50],
                srs='EPSG:' + str(srid),
                info_format='application/vnd.ogc.gml'
            )
            content = response.read()
            value = self.parse_request_value(content)
            # No geometry and url for WMS
            geometry = None
            url = response.geturl()
        else:
            url = self.build_query_url(x, y, srid)
            request = requests.get(url)
            content = request.content
            if ':' in self.layer_typename:
                workspace = self.layer_typename.split(':')[0]
                geometry = parse_gml_geometry(content, workspace)
            else:
                geometry = parse_gml_geometry(content)
            if not geometry:
                return None
            if not geometry.srid:
                geometry.srid = self.srid
            value = self.parse_request_value(content)

        # Create cache here.
        from geocontext.models.context_cache import ContextCache
        expired_time = datetime.utcnow() + timedelta(seconds=self.time_to_live)
        # Set timezone to UTC
        expired_time = expired_time.replace(tzinfo=pytz.UTC)
        context_cache = ContextCache(
            service_registry=self,
            name=self.key,
            value=value,
            expired_time=expired_time
        )

        if url:
            context_cache.source_uri = url

        if geometry:
            context_cache.set_geometry_field(geometry)

        context_cache.save()

        context_cache.refresh_from_db()

        return context_cache

    def parse_request_value(self, request_content):
        """Parse request value from request content.

        :param request_content: String that represent content of a request.
        :type request_content: unicode

        :returns: The value of the result_regex in the request_content.
        :rtype: unicode
        """
        if self.query_type in [
            ContextServiceRegistry.WFS, ContextServiceRegistry.WMS]:
            xmldoc = minidom.parseString(request_content)
            try:
                value_dom = xmldoc.getElementsByTagName(self.result_regex)[0]
                return value_dom.childNodes[0].nodeValue
            except IndexError:
                return None

    def build_query_url(self, x, y, srid=4326):
        """Build query based on the model and the parameter.

        :param x: The value of x coordinate.
        :type x: float

        :param y: The value of y coordinate.
        :type y: float

        :param srid: The srid of the coordinate.
        :type srid: int

        :return: URL to do query.
        :rtype: unicode
        """
        if self.query_type == ContextServiceRegistry.WFS:
            # construct bbox
            if srid != self.srid:
                x, y = convert_coordinate(x, y, srid, self.srid)
            bbox = get_bbox(x, y)
            bbox_string = ','.join([str(i) for i in bbox])

            parameters = {
                'SERVICE': 'WFS',
                'REQUEST': 'GetFeature',
                'VERSION': self.service_version,
                'TYPENAME': self.layer_typename,
                # 'SRSNAME': 'EPSG:%s' % self.srid,  # added manually
                'OUTPUTFORMAT': 'GML3',
                # 'BBOX': bbox_string  # added manually
            }
            query_dict = QueryDict('', mutable=True)
            query_dict.update(parameters)

            if '?' in self.url:
                url = self.url + '&' + query_dict.urlencode()
            else:
                url = self.url + '?' + query_dict.urlencode()
            # Only add SRSNAME when there is no workspace
            if ':' not in self.layer_typename:
                url += '&SRSNAME=%s' % self.srid
            url += '&BBOX=' + bbox_string

            return url
