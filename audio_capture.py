#!/usr/bin/python3

import jamulus

import argparse
import base64
import signal
import sys


BASE_NETW_SIZE = 12
JITT_BUF_SIZE = 5


def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=jamulus.DEFAULT_PORT, help="local port number")
    parser.add_argument(
        "--server",
        type=jamulus.server_argument,
        required=True,
        help="central server to register on",
    )
    parser.add_argument(
        "--log-data",
        action="store_true",
        help="log protocol data",
    )
    parser.add_argument(
        "--log-audio",
        action="store_true",
        help="log audio messages",
    )
    parser.add_argument("--file", type=str, required=True, help="output filename")

    return parser.parse_args()


def main():
    global jc, args

    args = argument_parser()

    jc = jamulus.JamulusConnector(port=args.port, log_data=args.log_data, log_audio=args.log_audio)

    write_file = open(args.file, "w")

    audio_values = jamulus.silent_audio(BASE_NETW_SIZE)
    jc.sendto(args.server, "AUDIO", audio_values)

    while True:
        addr, key, count, values = jc.recvfrom()

        if addr != args.server:
            # drop messages not coming from the server
            continue

        if key == "AUDIO":
            if values != audio_values:
                print(base64.b64encode(values["data"]).decode())
                write_file.write("{}\n".format(base64.b64encode(values["data"]).decode()))
            jc.sendto(addr, "AUDIO", audio_values)

        elif key == "REQ_SPLIT_MESS_SUPPORT":
            jc.sendto(addr, "SPLIT_MESS_SUPPORTED")
            pass

        elif key == "REQ_NETW_TRANSPORT_PROPS":
            jc.sendto(
                addr,
                "NETW_TRANSPORT_PROPS",
                {
                    "base_netw_size": BASE_NETW_SIZE,
                    "block_size_fact": 1,
                    "num_chan": 1,
                    "sam_rate": 48000,
                    "audiocod_type": 3,
                    "flags": 0,
                    "audiocod_arg": 0,
                },
            )

        elif key == "REQ_JITT_BUF_SIZE":
            jc.sendto(addr, "JITT_BUF_SIZE", {"blocks": JITT_BUF_SIZE})

        elif key == "REQ_CHANNEL_INFOS":
            jc.sendto(
                addr,
                "CHANNEL_INFOS",
                {
                    "country": 0,
                    "instrument": 0,
                    "skill": 0,
                    "name": "Audio Capture",
                    "city": "",
                },
            )


def signal_handler(sig, frame):
    print()
    jc.sendto(args.server, "CLM_DISCONNECTION")

    try:
        while True:
            jc.recvfrom(1)
    except TimeoutError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
