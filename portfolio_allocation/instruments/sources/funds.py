import json
import re
import sys
import time

import countrynames
import pycountry
import requests
from cache_to_disk import cache_to_disk

from ..model import InstrumentData, InstrumentDataSource

_DEFAULT_CACHE_AGE = 30


class FundsDataSource(InstrumentDataSource):
    def get(self, instruments: list[str]) -> dict[str, InstrumentData]:
        result = {}
        for instrument in instruments:
            try:
                if instrument.startswith("FX"):
                    result[instrument] = self._finex(instrument)
                elif instrument.startswith("T"):
                    result[instrument] = self._tinkoff(instrument)
                else:
                    continue
            except _InstrumentMissingException:
                continue
        return result

    @cache_to_disk(_DEFAULT_CACHE_AGE)
    def _finex(self, instrument: str) -> InstrumentData:
        url = "https://finex-etf.ru/products/" + instrument
        print("Sending request GET " + url)
        start = time.time()
        r = requests.get(url)
        print("Got response in " + str(time.time() - start) + " seconds")
        if r.status_code == 404:
            raise _InstrumentMissingException
        group = re.search('<script id="__NEXT_DATA__" type="application/json">([^<]*)</script>', r.text).group(1)
        data = json.loads(group)
        try:
            response_data = data['props']['pageProps']['initialState']['fondDetail']['responseData']
        except IndexError:
            raise _InstrumentMissingException
        country_share = response_data['share'].get('countryShare')
        if country_share is None or country_share == {}:
            try:
                country_share = {response_data['name'].split("/")[1].strip(): 1}
            except:
                country_share = {}
        return InstrumentData(
            instrument=instrument,
            countries=_map_keys(country_share, _country_name_to_english),
            industries=response_data['share'].get('otherShare'),
            fee=response_data['commission'],
            currencies={
                str(response_data['currencyNav']): 1
            },
            classes={
                str(response_data['classActive']): 1
            }
        )

    @cache_to_disk(_DEFAULT_CACHE_AGE)
    def _tinkoff(self, instrument: str) -> InstrumentData:
        url = "https://www.tinkoff.ru/invest/etfs/" + instrument
        print("Sending request GET " + url)
        start = time.time()
        r = requests.get(url)
        print("Got response in " + str(time.time() - start) + " seconds")
        r.encoding = 'UTF-8'
        group = re.search("<script>window\\['__REACT_QUERY_STATE__invest'] = '(.*)'</script>", r.text).group(1) \
            .replace('\\\\"', '')
        data = json.loads(group)
        try:
            response_data = data['queries'][0]['state']['data']['detail']
        except IndexError:
            raise _InstrumentMissingException
        return InstrumentData(
            instrument=instrument,
            countries=_map_keys(self._tinkoff_chart_to_shares(response_data, 'countries'), _country_name_to_english),
            industries=self._tinkoff_chart_to_shares(response_data, 'sectors'),
            fee=response_data['expense']['total'],
            currencies={
                str(response_data['currency']): 1
            },
            classes=self._tinkoff_chart_to_shares(response_data, 'types')
        )

    @staticmethod
    def _tinkoff_chart_to_shares(response_data: dict, key: str) -> dict[str, float]:
        return {x['name']: round(x['relativeValue'] / 100, 8) for x in
                next(filter(lambda obj: obj['type'] == key, response_data['pies']['charts']))['items']}


class _InstrumentMissingException(Exception):
    pass


def _map_keys(dictionary: dict[str, any], mapping_function) -> dict[str, any]:
    return {mapping_function(k): v for k, v in dictionary.items()}


def _country_name_to_english(name: str) -> str:
    try:
        return pycountry.countries.get(alpha_2=countrynames.to_code(name)).name
    except LookupError:
        print('Unexpected country name: "' + name + '"', file=sys.stderr)
        return name


funds = FundsDataSource().get
