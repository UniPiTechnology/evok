import time

import requests

host = "127.0.0.1"


def main():
    url = f"http://{host}/bulk"

    # Example echo method
    payload_set = {
        "individual_assignments": []
    }

    payload_reset = {
        "individual_assignments": []
    }

    for i in ['01', '02', '03', '04']:
        cmd = {"device_type": "do", "device_circuit": f"1_{i}", "assigned_values": {'value': 1}}
        payload_set['individual_assignments'].append(cmd)

        cmd = {"device_type": "do", "device_circuit": f"1_{i}", "assigned_values": {'value': 0}}
        payload_reset['individual_assignments'].append(cmd)

    response = requests.post(url, json=payload_set).json()
    print(response)

    time.sleep(2)

    response = requests.post(url, json=payload_reset).json()
    print(response)


if __name__ == "__main__":
    main()
