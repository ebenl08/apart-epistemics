"""Pull python:3.12-slim (linux/amd64) from Docker Hub into a plain rootfs dir (no Docker needed).
Usage: python pull_rootfs.py /root/rootfs/py312slim  -> also writes <dir>.digest
"""
import io, json, os, sys, tarfile, urllib.request

REPO, TAG = "library/python", "3.12-slim"
out = sys.argv[1]


def get(url, token, accept=None):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    if accept:
        req.add_header("Accept", accept)
    return urllib.request.urlopen(req)


tok = json.load(urllib.request.urlopen(
    f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{REPO}:pull"))["token"]
base = f"https://registry-1.docker.io/v2/{REPO}"
idx = json.load(get(f"{base}/manifests/{TAG}", tok,
                    "application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json"))
digest = next(m["digest"] for m in idx["manifests"]
              if m["platform"]["os"] == "linux" and m["platform"]["architecture"] == "amd64")
man = json.load(get(f"{base}/manifests/{digest}", tok,
                    "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json"))
os.makedirs(out, exist_ok=True)
for layer in man["layers"]:
    blob = get(f"{base}/blobs/{layer['digest']}", tok).read()
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        members = []
        for m in tf.getmembers():
            name = os.path.basename(m.name)
            if name.startswith(".wh."):  # whiteout: delete the shadowed path from lower layers
                target = os.path.join(out, os.path.dirname(m.name), name[4:])
                if name != ".wh..wh..opq" and os.path.lexists(target):
                    os.system(f"rm -rf '{target}'")
                continue
            members.append(m)
        tf.extractall(out, members=members, filter="tar")
open(out.rstrip("/") + ".digest", "w").write(digest + "\n")
print("rootfs ok", digest, len(man["layers"]), "layers")
