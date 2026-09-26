"""Build the app: python setup.py py2app  ->  dist/Castbar.app"""
from setuptools import setup

setup(
    app=["castbar/app.py"],
    name="Castbar",
    data_files=[("ui", ["castbar/ui/index.html"])],
    options={
        "py2app": {
            "packages": ["pychromecast", "zeroconf"],
            "iconfile": "castbar/Castbar.icns",
            "plist": {
                "CFBundleIdentifier": "com.itssarthak.castbar",
                "CFBundleShortVersionString": "0.1.3",
                "LSUIElement": True,  # menu bar only, no Dock icon
                "NSLocalNetworkUsageDescription": "Castbar finds and controls Cast devices on your network.",
                "NSAppleEventsUsageDescription": "Castbar switches to the Chrome tab that's already playing what you clicked.",
                "NSBonjourServices": ["_googlecast._tcp"],
                "NSAppTransportSecurity": {"NSAllowsArbitraryLoadsInWebContent": True},  # album art over http
            },
        }
    },
    setup_requires=["py2app"],
)
