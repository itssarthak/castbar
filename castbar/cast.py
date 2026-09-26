"""Chromecast side: discovers every Cast device on the network and keeps it connected."""
from concurrent.futures import ThreadPoolExecutor

import pychromecast
import zeroconf
from pychromecast.controllers.media import MediaStatusListener
from pychromecast.controllers.receiver import CastStatusListener
from pychromecast.discovery import CastBrowser, SimpleCastListener

ACTIVE = ("PLAYING", "PAUSED", "BUFFERING")



class Device(CastStatusListener, MediaStatusListener):
    def __init__(self, info, zconf, on_change):
        self.info = info
        self.on_change = on_change
        self.cast = pychromecast.get_chromecast_from_cast_info(info, zconf)
        self.cast.register_status_listener(self)
        self.cast.media_controller.register_status_listener(self)
        self.cast.start()

    def new_cast_status(self, status):
        self.on_change()

    def new_media_status(self, status):
        self.on_change()

    def load_media_failed(self, queue_item_id, error_code):
        pass

    def to_dict(self):
        s = self.cast.status
        m = self.cast.media_controller.status
        media = None
        if m.player_state in ACTIVE:
            media = {
                "title": m.title or (s.display_name if s else "") or "Unknown",
                "subtitle": m.artist or m.series_title or m.album_name or "",
                "art": m.images[0].url if m.images else None,
                "match": (m.content_id or "").split(":")[-1],  # text the browser tab's URL will contain
                "state": m.player_state,
                "position": m.adjusted_current_time or 0,
                "duration": m.duration,
                "can": {
                    "pause": m.supports_pause,
                    "seek": m.supports_seek and bool(m.duration),
                    "next": m.supports_queue_next,
                    "prev": m.supports_queue_prev,
                },
            }
        return {
            "uuid": str(self.info.uuid),
            "name": self.info.friendly_name or "Cast device",
            "group": self.info.cast_type == "group",
            "volume": s.volume_level if s else 0,
            "muted": s.volume_muted if s else False,
            "fixed": bool(s) and s.volume_control_type == "fixed",
            "app": s.display_name if s and s.display_name != "Backdrop" else None,
            "media": media,
        }


class CastManager:
    def __init__(self, on_change):
        self.on_change = on_change
        self.devices = {}
        # ponytail: one worker keeps volume drags in order; an unreachable device stalls
        # other commands for up to 10s. Per-device queues if that ever bites.
        self.pool = ThreadPoolExecutor(1)
        self.zconf = zeroconf.Zeroconf()
        self.browser = CastBrowser(SimpleCastListener(self._add, self._remove), self.zconf)
        self.browser.start_discovery()

    def _add(self, uuid, service):
        key = str(uuid)
        if key not in self.devices:
            self.devices[key] = Device(self.browser.devices[uuid], self.zconf, self.on_change)
            self.on_change()

    def _remove(self, uuid, service, cast_info):
        device = self.devices.pop(str(uuid), None)
        if device:
            self.pool.submit(device.cast.disconnect)
            self.on_change()

    def state(self):
        devices = [d.to_dict() for d in list(self.devices.values())]
        rank = {"PLAYING": 0, "BUFFERING": 0, "PAUSED": 1}
        return {"devices": sorted(devices, key=lambda d: (
            rank.get((d["media"] or {}).get("state"), 2), d["group"], d["name"].lower()))}

    def command(self, uuid, cmd, value=None):
        device = self.devices.get(uuid)
        if not device:
            return
        cast, mc = device.cast, device.cast.media_controller
        actions = {
            "play": mc.play,
            "pause": mc.pause,
            "stop": mc.stop,
            "next": mc.queue_next,
            "prev": mc.queue_prev,
            "seek": lambda: mc.seek(max(0, float(value))),
            "volume": lambda: cast.set_volume(min(1, max(0, float(value)))),
            "mute": lambda: cast.set_volume_muted(bool(value)),
        }
        if cmd in actions:
            self.pool.submit(self._run, actions[cmd])

    def _run(self, fn):
        try:
            fn()
        except Exception as e:  # device went away mid-command; the next status update corrects the UI
            print("cast command failed:", e)
        self.on_change()

