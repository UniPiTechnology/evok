import math
import time
from asyncio import TaskGroup
import statistics

import aiohttp
import asyncio

host = '192.168.221.40'

set_values = ['01', '02', '03', '04']
set_index = 0
set_value = True


def set_increment():
    global set_index, set_value
    set_index += 1
    if set_index >= len(set_values):
        set_index = 0
        set_value = not set_value


async def rest_request_get(session: aiohttp.ClientSession, results):
    url = f'http://{host}/rest/do/1_01'
    start_stamp = time.time()
    async with session.get(url) as response:
        await response.text()
    diff = time.time() - start_stamp
    results.append(diff)


async def json_request_get(session: aiohttp.ClientSession, results):
    url = f'http://{host}/json/do/1_01'
    start_stamp = time.time()
    async with session.get(url) as response:
        await response.text()
    diff = time.time() - start_stamp
    results.append(diff)


async def rest_request_set(session: aiohttp.ClientSession, results):
    url = f'http://{host}/rest/do/1_{set_values[set_index]}'
    start_stamp = time.time()
    data = {'value': str(1 if set_value else 0)}
    set_increment()
    async with session.post(url, data=data) as response:
        await response.text()
    diff = time.time() - start_stamp
    results.append(diff)


async def json_request_set(session: aiohttp.ClientSession, results):
    global set_index
    url = f'http://{host}/rest/do/1_{set_values[set_index]}'
    data = {'value': str(1 if set_value else 0)}
    set_increment()
    start_stamp = time.time()
    async with session.post(url, data=data) as response:
        await response.text()
    diff = time.time() - start_stamp
    results.append(diff)


async def request(fce, period: float, repeat: int) -> dict:
    results = list()
    async with aiohttp.ClientSession() as session:
        async with TaskGroup() as group:
            for _ in range(repeat):
                group.create_task(fce(session, results))
                await asyncio.sleep(period)
    ret = {'fce': fce.__name__, 'period': period}
    ret.update(get_result(results))
    print(end='.', flush=True)
    await asyncio.sleep(1)
    return ret


def get_result(results: list) -> dict:
    avg = round(sum(results) / len(results) * 1000, 3)
    variance = sum([(((x * 1000) - avg) ** 2) for x in results]) / len(results)
    stddev = round(math.sqrt(variance), 3)
    min_value = round(min(results) * 1000, 3)
    max_value = round(max(results) * 1000, 3)
    median_value = round(statistics.median(results) * 1000, 3)

    return {'average': avg, 'std_dev': stddev, 'min': min_value, 'max': max_value, 'median': median_value}


async def main():
    print("Benchmark started ", end='.')
    results = list()

    results.append(await request(fce=rest_request_get, period=0, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.001, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.002, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.003, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.006, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.01, repeat=100))
    results.append(await request(fce=rest_request_get, period=0.1, repeat=30))

    results.append(await request(fce=json_request_get, period=0, repeat=100))
    results.append(await request(fce=json_request_get, period=0.001, repeat=100))
    results.append(await request(fce=json_request_get, period=0.002, repeat=100))
    results.append(await request(fce=json_request_get, period=0.003, repeat=100))
    results.append(await request(fce=json_request_get, period=0.006, repeat=100))
    results.append(await request(fce=json_request_get, period=0.01, repeat=100))
    results.append(await request(fce=json_request_get, period=0.1, repeat=30))

    results.append(await request(fce=rest_request_set, period=0, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.001, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.002, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.003, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.006, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.01, repeat=100))
    results.append(await request(fce=rest_request_set, period=0.1, repeat=30))

    results.append(await request(fce=json_request_set, period=0, repeat=100))
    results.append(await request(fce=json_request_set, period=0.001, repeat=100))
    results.append(await request(fce=json_request_set, period=0.002, repeat=100))
    results.append(await request(fce=json_request_set, period=0.003, repeat=100))
    results.append(await request(fce=json_request_set, period=0.006, repeat=100))
    results.append(await request(fce=json_request_set, period=0.01, repeat=100))
    results.append(await request(fce=json_request_set, period=0.1, repeat=30))

    print()
    for data in results:
        print(f"{data['fce']}:\t{data}")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
