"""Harbor environment that runs each trial in its own proot/chroot (no Docker needed).

Why: the RunPod host has no Docker/Singularity and no CAP_SYS_ADMIN (no mounts, no
namespaces), but it does have CAP_SYS_CHROOT. Each trial gets a private copy of a
python:3.12-slim rootfs, so the absolute paths the tasks and the CLM harness use
(/app, /logs, /tests, the CLM state dir) do not collide across concurrent trials.

Use with:  harbor trials start ... -e chroot_env:ChrootEnvironment
           (with infra/ on PYTHONPATH)

Runner (CHROOT_RUNNER): "proot" (default) runs commands under proot with the host
/proc, /dev and /sys bound in, so /dev/null, /dev/stdin, /dev/fd and process
substitution behave as in Docker. "chroot" is the earlier fallback: no /proc, and
/dev/null is a regular file truncated before every exec (mknod is blocked).

Deviations from Docker, logged in .agent/decisions.md:
  - no CPU/memory limits, no network isolation;
  - host /proc is visible (proot mode);
  - isolation is filesystem-only (fine for non-adversarial benchmark trials).

Rootfs template: CHROOT_TEMPLATE (default /root/rootfs/py312slim).
Per-trial roots: CHROOT_ROOT_DIR (default /root/chroots).
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import uuid
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities

TEMPLATE = Path(os.environ.get("CHROOT_TEMPLATE", "/root/rootfs/py312slim"))
ROOT_DIR = Path(os.environ.get("CHROOT_ROOT_DIR", "/root/chroots"))
RUNNER = os.environ.get("CHROOT_RUNNER", "proot")
_BASE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


class ChrootEnvironment(BaseEnvironment):
    @staticmethod
    def type() -> str:
        return "chroot"

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(mounted=False)

    def _validate_definition(self):
        if not TEMPLATE.is_dir():
            raise FileNotFoundError(f"chroot template rootfs missing: {TEMPLATE}")

    # ------------------------------------------------------------ paths
    @property
    def root(self) -> Path:
        # session_id is "<task>__env", shared by concurrent trials of the same task
        # (e.g. skill=none and skill=clm); a per-instance suffix keeps their roots apart.
        if not hasattr(self, "_root_dir"):
            self._root_dir = ROOT_DIR / f"{self.session_id}-{uuid.uuid4().hex[:8]}"
        return self._root_dir

    def _host(self, path: str) -> Path:
        """Host path of an absolute in-chroot path."""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.task_env_config.workdir or "/") / p
        return self.root / str(p).lstrip("/")

    # ------------------------------------------------------------ lifecycle
    async def start(self, force_build: bool) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            "cp", "-a", str(TEMPLATE), str(self.root))
        if await proc.wait() != 0:
            raise RuntimeError(f"failed to copy rootfs to {self.root}")
        if RUNNER == "chroot":
            devnull = self.root / "dev" / "null"
            devnull.parent.mkdir(exist_ok=True)
            devnull.write_bytes(b"")
            devnull.chmod(0o666)
        targets = {m.get("target") if isinstance(m, dict) else getattr(m, "target", None)
                   for m in self._mounts}
        targets |= {"/logs/agent", "/logs/verifier", "/logs/artifacts"}
        for t in filter(None, targets):
            self._host(t).mkdir(parents=True, exist_ok=True)
        if self.task_env_config.workdir:
            self._host(self.task_env_config.workdir).mkdir(parents=True, exist_ok=True)
        await self._upload_environment_dir_after_start()

    async def stop(self, delete: bool):
        if delete and self.root.exists():
            await asyncio.to_thread(shutil.rmtree, self.root, True)

    # ------------------------------------------------------------ files
    async def upload_file(self, source_path: Path | str, target_path: str):
        dst = self._host(target_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, source_path, dst)

    async def upload_dir(self, source_dir: Path | str, target_dir: str):
        dst = self._host(target_dir)
        dst.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copytree, source_dir, dst, dirs_exist_ok=True)

    async def download_file(self, source_path: str, target_path: Path | str):
        src = self._host(source_path)
        if not src.is_file():
            raise FileNotFoundError(source_path)
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, src, target_path)

    async def download_dir(self, source_dir: str, target_dir: Path | str):
        src = self._host(source_dir)
        if not src.is_dir():
            raise FileNotFoundError(source_dir)
        await asyncio.to_thread(shutil.copytree, src, target_dir, dirs_exist_ok=True,
                                symlinks=True)

    async def is_dir(self, path: str, user: str | int | None = None) -> bool:
        return self._host(path).is_dir()

    async def is_file(self, path: str, user: str | int | None = None) -> bool:
        return self._host(path).is_file()

    # ------------------------------------------------------------ exec
    async def exec(self, command: str, cwd: str | None = None,
                   env: dict[str, str] | None = None, timeout_sec: int | None = None,
                   user: str | int | None = None) -> ExecResult:
        full_env = {"PATH": _BASE_PATH, "HOME": "/root", "LANG": "C.UTF-8",
                    "TERM": "dumb", **(self.task_env_config.env or {})}
        merged = self._merge_env(env)
        if merged:
            full_env.update(merged)
        workdir = cwd or self.task_env_config.workdir or "/"
        script = ((": > /dev/null 2>&1; " if RUNNER == "chroot" else "") +
                  f"mkdir -p {shlex.quote(workdir)}; cd {shlex.quote(workdir)} || exit 1\n"
                  f"{command}")
        if RUNNER == "proot":
            argv = ["proot", "-r", str(self.root), "-b", "/proc", "-b", "/dev", "-b", "/sys",
                    "/bin/bash", "-c", script]
        else:
            argv = ["chroot", str(self.root), "/bin/bash", "-c", script]
            if user not in (None, "root", 0):
                argv = ["chroot", f"--userspec={user}", str(self.root), "/bin/bash", "-c",
                        script]
        proc = await asyncio.create_subprocess_exec(
            *argv, env=full_env, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            start_new_session=True)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            rc = proc.returncode
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, 9)
            except ProcessLookupError:
                pass
            out, err = await proc.communicate()
            rc = 124
            err = (err or b"") + f"\n[chroot_env] timed out after {timeout_sec}s\n".encode()
        stdout = out.decode("utf-8", "replace")
        stderr = err.decode("utf-8", "replace")
        callback = self._output_callback()
        if callback is not None:
            if stdout:
                await callback(stdout, "stdout")
            if stderr:
                await callback(stderr, "stderr")
        return ExecResult(stdout=stdout, stderr=stderr, return_code=rc)
