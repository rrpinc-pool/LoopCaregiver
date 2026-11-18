"""Read Apple processing and tester availability without changing any builds."""

import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt


now = int(time.time())
token = jwt.encode(
    {"iss": os.environ["FASTLANE_ISSUER_ID"], "iat": now, "exp": now + 600,
     "aud": "appstoreconnect-v1"},
    os.environ["FASTLANE_KEY"],
    algorithm="ES256",
    headers={"kid": os.environ["FASTLANE_KEY_ID"], "typ": "JWT"},
)


def get(path, **query):
    url = "https://api.appstoreconnect.apple.com/v1/" + path
    if query:
        url += "?" + urlencode(query)
    request = Request(url, headers={"Authorization": "Bearer " + token})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


results = []
for suffix in ("LoopFollow", "loopkit.LoopCaregiver"):
    bundle = "com." + os.environ["TEAMID"] + "." + suffix
    apps = get("apps", **{"filter[bundleId]": bundle})["data"]
    if len(apps) != 1:
        raise RuntimeError("Expected one matching app for " + suffix)
    app = apps[0]
    builds = get("builds", **{"filter[app]": app["id"], "sort": "-uploadedDate", "limit": "2"})["data"]
    for build in builds:
        detail = get("builds/" + build["id"] + "/buildBetaDetail")["data"]["attributes"]
        version = get("builds/" + build["id"] + "/preReleaseVersion")["data"]["attributes"]["version"]
        attributes = build["attributes"]
        results.append({
            "app": app["attributes"]["name"], "version": version,
            "build": attributes["version"], "processing": attributes["processingState"],
            "expires": attributes["expirationDate"], "minimumOS": attributes["minOsVersion"],
            "beta": detail,
        })
print(json.dumps(results, indent=2))
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("```json\n" + json.dumps(results, indent=2) + "\n```\n")
