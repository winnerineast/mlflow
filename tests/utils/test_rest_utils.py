#!/usr/bin/env python

import mock
import numpy
import pytest

from mlflow.utils.rest_utils import http_request, http_request_safe,\
    MlflowHostCreds, _DEFAULT_HEADERS
from mlflow.pyfunc.scoring_server import NumpyEncoder
from mlflow.exceptions import MlflowException, RestException


@mock.patch('requests.request')
def test_http_request_hostonly(request):
    host_only = MlflowHostCreds("http://my-host")
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request(host_only, '/my/endpoint')
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=True,
        headers=_DEFAULT_HEADERS,
    )


@mock.patch('requests.request')
def test_http_request_cleans_hostname(request):
    # Add a trailing slash, should be removed.
    host_only = MlflowHostCreds("http://my-host/")
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request(host_only, '/my/endpoint')
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=True,
        headers=_DEFAULT_HEADERS,
    )


@mock.patch('requests.request')
def test_http_request_with_basic_auth(request):
    host_only = MlflowHostCreds("http://my-host", username='user', password='pass')
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request(host_only, '/my/endpoint')
    headers = dict(_DEFAULT_HEADERS)
    headers['Authorization'] = 'Basic dXNlcjpwYXNz'
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=True,
        headers=headers,
    )


@mock.patch('requests.request')
def test_http_request_with_token(request):
    host_only = MlflowHostCreds("http://my-host", token='my-token')
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request(host_only, '/my/endpoint')
    headers = dict(_DEFAULT_HEADERS)
    headers['Authorization'] = 'Bearer my-token'
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=True,
        headers=headers,
    )


@mock.patch('requests.request')
def test_http_request_with_insecure(request):
    host_only = MlflowHostCreds("http://my-host", ignore_tls_verification=True)
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request(host_only, '/my/endpoint')
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=False,
        headers=_DEFAULT_HEADERS,
    )


@mock.patch('requests.request')
def test_429_retries(request):
    host_only = MlflowHostCreds("http://my-host", ignore_tls_verification=True)

    class MockedResponse(object):
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = "mocked text"

    request.side_effect = [MockedResponse(x) for x in (429, 200)]
    assert http_request(host_only, '/my/endpoint', max_rate_limit_interval=0).status_code == 429
    request.side_effect = [MockedResponse(x) for x in (429, 200)]
    assert http_request(host_only, '/my/endpoint', max_rate_limit_interval=1).status_code == 200
    request.side_effect = [MockedResponse(x) for x in (429, 429, 200)]
    assert http_request(host_only, '/my/endpoint', max_rate_limit_interval=1).status_code == 429
    request.side_effect = [MockedResponse(x) for x in (429, 429, 200)]
    assert http_request(host_only, '/my/endpoint', max_rate_limit_interval=2).status_code == 200
    request.side_effect = [MockedResponse(x) for x in (429, 429, 200)]
    assert http_request(host_only, '/my/endpoint', max_rate_limit_interval=3).status_code == 200
    # Test that any non 429 code is returned
    request.side_effect = [MockedResponse(x) for x in (429, 404, 429, 200)]
    assert http_request(host_only, '/my/endpoint').status_code == 404
    # Test that retries work as expected
    request.side_effect = [MockedResponse(x) for x in (429, 503, 429, 200)]
    with pytest.raises(MlflowException, match="failed to return code 200"):
        http_request(host_only, '/my/endpoint', retries=1)
    request.side_effect = [MockedResponse(x) for x in (429, 503, 429, 200)]
    assert http_request(host_only, '/my/endpoint', retries=2).status_code == 200


@mock.patch('requests.request')
def test_http_request_wrapper(request):
    host_only = MlflowHostCreds("http://my-host", ignore_tls_verification=True)
    response = mock.MagicMock()
    response.status_code = 200
    request.return_value = response
    http_request_safe(host_only, '/my/endpoint')
    request.assert_called_with(
        url='http://my-host/my/endpoint',
        verify=False,
        headers=_DEFAULT_HEADERS,
    )
    response.status_code = 400
    response.text = ""
    request.return_value = response
    with pytest.raises(MlflowException, match="Response body"):
        http_request_safe(host_only, '/my/endpoint')
    response.text =\
        '{"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "Node type not supported"}'
    request.return_value = response
    with pytest.raises(RestException, match="RESOURCE_DOES_NOT_EXIST: Node type not supported"):
        http_request_safe(host_only, '/my/endpoint')


def test_numpy_encoder():
    test_number = numpy.int64(42)
    ne = NumpyEncoder()
    defaulted_val = ne.default(test_number)
    assert defaulted_val == 42


def test_numpy_encoder_fail():
    if not hasattr(numpy, "float128"):
        pytest.skip("numpy on exit"
                    "this platform has no float128")
    test_number = numpy.float128
    with pytest.raises(TypeError):
        ne = NumpyEncoder()
        ne.default(test_number)
