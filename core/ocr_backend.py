import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import requests

VAT_INVOICE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
TOKEN_TTL = 25 * 24 * 3600  # 25天，单位秒


@dataclass
class OCRError(Exception):
    error_type: str  # AUTH_ERROR / NETWORK_ERROR / PARSE_ERROR / RATE_LIMIT
    message: str


class OCRBackend(ABC):
    @abstractmethod
    def recognize(self, image_bytes: bytes) -> dict:
        """返回百度 /vat_invoice 接口的 words_result 字典"""


class BaiduOCRBackend(OCRBackend):
    def __init__(self, api_key: str, secret_key: str):
        self._api_key = api_key
        self._secret_key = secret_key
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        try:
            resp = requests.post(TOKEN_URL, params={
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._secret_key,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = time.time() + TOKEN_TTL
            return self._access_token
        except Exception as e:
            raise OCRError(error_type="AUTH_ERROR", message=str(e))

    def recognize(self, image_bytes: bytes, _retry: int = 3) -> dict:
        try:
            token = self._get_access_token()
        except OCRError:
            raise
        except Exception as e:
            raise OCRError(error_type="AUTH_ERROR", message=str(e))

        img_b64 = base64.b64encode(image_bytes).decode()
        try:
            resp = requests.post(
                VAT_INVOICE_URL,
                params={"access_token": token},
                data={"image": img_b64},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.Timeout:
            raise OCRError(error_type="NETWORK_ERROR", message="请求超时")
        except requests.RequestException as e:
            raise OCRError(error_type="NETWORK_ERROR", message=str(e))

        if "error_code" in result:
            code = result["error_code"]
            if code in (110, 111):
                raise OCRError(error_type="AUTH_ERROR", message=result.get("error_msg", ""))
            if code == 18:
                # QPS 超限：退避重试，最多 _retry 次
                if _retry > 0:
                    time.sleep(1.0)
                    return self.recognize(image_bytes, _retry=_retry - 1)
                raise OCRError(error_type="RATE_LIMIT", message="QPS超限，已重试3次仍失败")
            raise OCRError(error_type="PARSE_ERROR", message=result.get("error_msg", ""))

        return result
