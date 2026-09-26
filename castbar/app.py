"""Menu bar shell: a status item that opens a popover hosting ui/index.html."""
import json
import os

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMakeRect,
    NSMinYEdge,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSSize,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSViewController,
)
from Foundation import NSURL, NSObject
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

from cast import CastManager

WIDTH = 340
UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")


class Bridge(NSObject, protocols=[objc.protocolNamed("WKScriptMessageHandler")]):
    def userContentController_didReceiveScriptMessage_(self, controller, message):
        self.delegate.handle_(json.loads(message.body()))


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("hifispeaker.2.fill", "Castbar")
        icon.setTemplate_(True)
        button = self.item.button()
        button.setImage_(icon)
        button.setTarget_(self)
        button.setAction_("toggle:")

        self.bridge = Bridge.alloc().init()
        self.bridge.delegate = self
        config = WKWebViewConfiguration.alloc().init()
        config.userContentController().addScriptMessageHandler_name_(self.bridge, "cast")
        self.web = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, WIDTH, 160), config)
        self.web.setValue_forKey_(False, "drawsBackground")  # let the popover's native material show through
        url = NSURL.fileURLWithPath_(UI)
        self.web.loadFileURL_allowingReadAccessToURL_(url, url.URLByDeletingLastPathComponent())

        controller = NSViewController.alloc().init()
        controller.setView_(self.web)
        self.popover = NSPopover.alloc().init()
        self.popover.setContentViewController_(controller)
        self.popover.setBehavior_(NSPopoverBehaviorTransient)
        self.popover.setContentSize_(NSSize(WIDTH, 160))

        self.pending = False
        self.casts = CastManager(self.changed)
        # Show the popup on launch so people see where the app lives. Delay lets the status item get placed first.
        AppHelper.callLater(0.5, self.toggle_, button)

    def toggle_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(sender)
        else:
            self.popover.showRelativeToRect_ofView_preferredEdge_(sender.bounds(), sender, NSMinYEdge)
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            self.push()

    def changed(self):
        """Called from pychromecast threads; coalesces bursts into one UI push on the main thread."""
        if not self.pending:
            self.pending = True
            AppHelper.callAfter(self.push)

    def push(self):
        self.pending = False
        self.web.evaluateJavaScript_completionHandler_(f"render({json.dumps(self.casts.state())})", None)

    def handle_(self, msg):
        cmd = msg.get("cmd")
        if cmd == "ready":
            self.push()
        elif cmd == "height":
            self.popover.setContentSize_(NSSize(WIDTH, min(640, max(120, msg["value"]))))
        elif cmd == "quit":
            NSApplication.sharedApplication().terminate_(None)
        else:
            self.casts.command(msg.get("uuid"), cmd, msg.get("value"))


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
