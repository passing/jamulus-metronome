#!/usr/bin/python3

import jamulus

import argparse
import base64
import signal
import sys
import time


BASE_NETW_SIZE = 12
JITT_BUF_SIZE = 20

AUDIO_FILE = "click"

BPM_MIN = 30
BPM_MAX = 200
BPM_INIT = 120


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
        "--log",
        action="store_true",
        help="log messages",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print protocol data",
    )
    parser.add_argument(
        "--log-audio",
        action="store_true",
        help="log audio messages",
    )

    return parser.parse_args()


def main():
    global jc, args

    args = argument_parser()

    jc = jamulus.JamulusConnector(port=args.port, log=args.log, debug=args.debug, log_audio=args.log_audio)

    audio_sample = []
    # read audio sample from file
    f = open(AUDIO_FILE, "r")
    for line in f:
        data = base64.b64decode(line.encode())
        audio_sample.append({"data": data})
    f.close
    # attach silent audio as last frame
    audio_sample.append(jamulus.silent_audio(BASE_NETW_SIZE))

    metronome_connected = False
    metronome_enabled = False
    metronome_bpm = BPM_INIT
    metronome_frame = len(audio_sample) - 1
    metronome_next_click = time.time()

    # request list of clients to decide if a connection should be established
    jc.sendto(args.server, "CLM_REQ_CONN_CLIENTS_LIST")

    while True:
        try:
            addr, key, count, values = jc.recvfrom(2)
        except TimeoutError:
            # request list of clients to decide if a connection should be established
            jc.sendto(args.server, "CLM_REQ_CONN_CLIENTS_LIST")
            continue

        if addr != args.server:
            # drop messages not coming from the server
            continue

        if key == "AUDIO" and metronome_connected:
            # return to first frame for a new click
            if time.time() > metronome_next_click:
                if metronome_enabled:
                    metronome_frame = 0
                    metronome_next_click += 60 / metronome_bpm
                else:
                    metronome_next_click = time.time()

            # play sample frame by frame / stay on last (silent frame)
            if metronome_frame < len(audio_sample) - 1:
                metronome_frame = metronome_frame + 1

            # send audio frame, timed by the server
            jc.sendto(addr, "AUDIO", audio_sample[metronome_frame])

        elif key == "CHAT_TEXT":
            # update metronome based on chat input received
            command = values["string"].split()[-1]
            if command == "on":
                metronome_enabled = True
            elif command == "off":
                metronome_enabled = False
            elif command.isnumeric() and int(command) >= BPM_MIN and int(command) <= BPM_MAX:
                metronome_bpm = int(command)
                if metronome_enabled == False:
                    metronome_enabled = True

        elif key == "REQ_NETW_TRANSPORT_PROPS":
            # send network transport properties when requested
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
            # send jitter buffer size when requested
            jc.sendto(addr, "JITT_BUF_SIZE", {"blocks": JITT_BUF_SIZE})

        elif key == "REQ_CHANNEL_INFOS":
            # send channel infos when requested
            jc.sendto(
                addr,
                "CHANNEL_INFOS",
                {
                    "country": 0,
                    "instrument": 0,
                    "skill": 0,
                    "name": "ClickBot",
                    "city": "",
                },
            )
            # send a chat text as well
            jc.sendto(
                addr,
                "CHAT_TEXT",
                {
                    "string": 'metronome: {}@{}bpm. Send "on", "off" or a number ({}-{}) to control'.format(
                        "ON" if metronome_enabled else "OFF", metronome_bpm, BPM_MIN, BPM_MAX
                    )
                },
            )

        elif key == "CLM_CONN_CLIENTS_LIST":
            # message is only received when requested while being disconnected
            if len(values) >= 1:
                # connect to server when there's at least one client connected
                jc.sendto(args.server, "AUDIO", jamulus.silent_audio(BASE_NETW_SIZE))
                metronome_connected = True

        elif key == "CONN_CLIENTS_LIST":
            # message is only received while being connected
            if len(values) >= 2:
                for id in [channel["id"] for channel in values]:
                    # mute all channels
                    jc.sendto(addr, "CHANNEL_GAIN", {"id": id, "gain": 0})
            elif len(values) == 1:
                # disconnect when everybody else disconnected
                jc.sendto(args.server, "CLM_DISCONNECTION")
                metronome_enabled = False
                metronome_connected = False


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
