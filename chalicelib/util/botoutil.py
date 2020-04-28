from __future__ import annotations

from typing import List, Union

from util.iterables import ensure_list, query

__all__ = ["HTTPResponseError", "raise_for_status"]


class HTTPResponseError(Exception):
    pass


def raise_for_status(response: dict, ok_codes: Union[int, List[int]] = 200):
    status_code = query("ResponseMetadata.HTTPStatusCode", response)
    if status_code is None:
        raise ValueError(f"Couldn't determine status_code from response: {response=}")
    if status_code not in ensure_list(ok_codes):
        raise HTTPResponseError(
            f"Request returned invalid response code: {status_code}"
        )
