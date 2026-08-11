from typing import Dict, Any, Tuple, List, Optional, NamedTuple
from enum import Enum
from packaging import version
import requests
import urllib3
from requests import Response, Session
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from requests.exceptions import Timeout
from urllib3 import Retry
from retry import retry


class HttpConfig:
    MAX_ATTEMPTS: int = 3
    BACKOFF_FACTOR: float = 0.3
    DEFAULT_TIMEOUT: int = 10

    DEFAULT_ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE"]
    DEFAULT_ERROR_STATUS_CODES: List[int] = [413, 429, 408, 500, 501, 502, 503, 504]


class HttpError(Exception):
    pass


class RequestsTypes(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'


class HttpErrorType(NamedTuple):
    status_code: int
    texts: List[str]


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def request_with_retry(request_type: RequestsTypes, url: str, headers: Dict = None, body: Any = None,
                       user: str = None,
                       password: str = None,
                       status_forcelist: List[int] = None,
                       method_whitelist: List[str] = None,
                       max_attempts: int = HttpConfig.MAX_ATTEMPTS,
                       backoff_factor: float = HttpConfig.BACKOFF_FACTOR,
                       params: Optional[Dict] = None,
                       timeout: Optional[int] = HttpConfig.DEFAULT_TIMEOUT,
                       stream: Optional[bool] = False,
                       retried_http_errors: Optional[List[HttpErrorType]] = None
                       ) -> Response:
    return _request_with_retry(
        request_type, url, headers, body, user, password, status_forcelist,
        method_whitelist, max_attempts, backoff_factor, params, timeout, stream,
        retried_http_errors,
        is_json=False
    )


def json_request_with_retry(request_type: RequestsTypes, url: str, headers: Dict = None, body: Any = None,
                            user: str = None,
                            password: str = None,
                            status_forcelist: List[int] = None,
                            method_whitelist: List[str] = None,
                            max_attempts: int = HttpConfig.MAX_ATTEMPTS,
                            backoff_factor: float = HttpConfig.BACKOFF_FACTOR,
                            params: Optional[Dict] = None,
                            timeout: Optional[int] = HttpConfig.DEFAULT_TIMEOUT,
                            stream: Optional[bool] = False,
                            retried_http_errors: Optional[List[HttpErrorType]] = None
                            ) -> Response:
    return _request_with_retry(
        request_type, url, headers, body, user, password, status_forcelist,
        method_whitelist, max_attempts, backoff_factor, params, timeout, stream,
        retried_http_errors,
        is_json=True
    )


def _build_http_session(status_forcelist: List[int], allowed_methods: List[str], max_attempts: int,
                        backoff_factor) -> Session:
    if allowed_methods is None:
        allowed_methods = frozenset(HttpConfig.DEFAULT_ALLOWED_METHODS)
    if status_forcelist is None:
        status_forcelist = HttpConfig.DEFAULT_ERROR_STATUS_CODES

    urllib3_version = version.parse(urllib3.__version__)

    if urllib3_version >= version.parse("2.0.0"):
        retries = Retry(
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
            total=max_attempts,
            backoff_factor=backoff_factor
        )
    else:
        retries = Retry(
            status_forcelist=status_forcelist,
            method_whitelist=allowed_methods,
            total=max_attempts,
            backoff_factor=backoff_factor
        )
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    return http


def _build_auth_object(user: str, password: str) -> HTTPBasicAuth:
    auth = None
    if type(user) is str and type(password) is str:
        auth = HTTPBasicAuth(username=user, password=password)
    elif user is not None or password is not None:
        raise Exception("User and password must be strings and provided together!")
    return auth


def _prepare_for_request(
        user: str,
        password: str,
        status_forcelist: List[int],
        method_whitelist: List[str],
        max_attempts: int,
        backoff_refactor: float
) -> Tuple[Session, HTTPBasicAuth]:
    http: Session = _build_http_session(status_forcelist, method_whitelist, max_attempts, backoff_refactor)
    auth = _build_auth_object(user, password)
    return http, auth


def _validate_retried_http_errors(errors: List[HttpErrorType]) -> None:
    if not len(set(err.status_code for err in errors)) == len(errors):
        raise ValueError(f"Given retried errors contain the same status code at least twice")


@retry((Timeout, HttpError), tries=HttpConfig.MAX_ATTEMPTS, backoff=HttpConfig.BACKOFF_FACTOR)
def _request_with_retry(request_type: RequestsTypes, url: str, headers: Dict = None, body: Any = None,
                        user: str = None,
                        password: str = None,
                        status_forcelist: List[int] = None,
                        method_whitelist: List[str] = None,
                        max_attempts: int = HttpConfig.MAX_ATTEMPTS,
                        backoff_factor: float = HttpConfig.BACKOFF_FACTOR,
                        params: Optional[Dict] = None,
                        timeout: Optional[int] = HttpConfig.DEFAULT_TIMEOUT,
                        stream: Optional[bool] = False,
                        retried_http_errors: Optional[List[HttpErrorType]] = None,
                        is_json: bool = False
                        ) -> Response:
    if retried_http_errors:
        _validate_retried_http_errors(retried_http_errors)

    http, auth = _prepare_for_request(user, password, status_forcelist, method_whitelist, max_attempts,
                                      backoff_factor)

    retried_http_errors_dct: Dict[int, List[str]] = {e.status_code: e.texts for e in
                                                     retried_http_errors} if retried_http_errors else {}
    try:
        if is_json:
            response: Response = http.request(request_type.value, url, headers=headers, json=body,
                                              verify=False, auth=auth, params=params, timeout=timeout,
                                              stream=stream)
        else:
            response: Response = http.request(request_type.value, url, headers=headers, data=body,
                                              verify=False, auth=auth, params=params, timeout=timeout,
                                              stream=stream)
        if response.status_code in retried_http_errors_dct and response.text in retried_http_errors_dct[
            response.status_code]:
            raise HttpError(f"failed with status code: {response.status_code} and text: {response.text}")
        else:
            return response
    except (Timeout, HttpError):
        raise
    except BaseException as e:
        raise Exception({'message': f"failed url request {max_attempts} times", 'error': {str(e)}})
