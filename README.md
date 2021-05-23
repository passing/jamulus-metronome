# Jamulus Metronome Client

Simple implementation of a Metronome for Jamulus.

The script connects as a Jamulus Client to a Jamulus Server. It is not able to handle any audio, but just replays audio packets with a 'click sound', that have been captured before.
To save network bandwidth, the script connects to a Server only when some user has connected and disconnects when all users have left.

The timing to send audio packets is lazy, as the script just sends one packet whenever it has received one.

## Running the metronome client

The script can be run anywhere, but preferrably on the same host as the Server it connects to.

```
./metronome.py --server <jamulus-server>
```

## Controlling the metronome client

the client reacts to chat messages in Jamulus:
- `on`: turn metronome on
- `off`: turn metronome off
- numbers: set metronome bpm.

## Capturing audio

The capture script writes all non-muted audio packets to a file with base64 encoding.

```
./audio_capture.py --server <jamulus-server> --file <capture-file>
```

To record a short sample, a real Jamulus Client needs to be connected to the same Server. That Client should then be unmuted for a short time while it is playing the sample.
Contributions for making this process easier are very welcome ;)
