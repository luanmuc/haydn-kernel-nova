#!/usr/bin/env python3
"""Nova 线三个上游的只读巡检。

检查内容：
1. 本地 pin 是否与当前主线 HEAD、KernelSU 子模块、审计表和 SUSFS 基线一致；
2. MiYume 内核、SukiSU-Nova、SUSFS 三个上游的目标分支是否前进；
3. 前进时列出新增 commit 和改动文件，并标出可能影响本仓库的路径；
4. SukiSU-Nova 最新 Release / 管理器 APK 是否与 pin 一致（需要 GITHUB_TOKEN）。

默认只报告，不修改仓库；--fail-on-update 可让有更新或 pin 过期时返回 2。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
PINS_DEFAULT = Path("maintenance/ksu-pins.json")
AUDIT_PATH = Path("patches/nova/builtin-new/UPSTREAM_AUDIT.yaml")
SUSFS_BASELINE_SCRIPT = Path("susfs/scripts/check-baseline.sh")
MAX_COMMITS = 8
MAX_FILES = 15

KERNEL_IMPACT_PATTERNS = (
    "arch/arm64/configs/haydn_defconfig",
    "build.config",
    "build_device.sh",
    "KernelSU",
    ".github/workflows/",
    "scripts/ci/",
)
KSU_IMPACT_PATTERNS = (
    "kernel/",
    "uapi/",
    "Kconfig",
    "manager/",
)
SUSFS_IMPACT_PATTERNS = (
    "fs/susfs.c",
    "fs/notify/",
    "fs/proc/",
    "include/linux/susfs",
    "kernel/",
)


def run(argv: list[str], cwd: Path | None = None, timeout: int = 40) -> tuple[int, str, str]:
    """Run a command without shell interpolation. Return (code, stdout, stderr)."""
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"timeout: {exc}"
    except OSError as exc:
        return 126, "", str(exc)


def git(args: list[str], cwd: Path, timeout: int = 40) -> tuple[int, str, str]:
    return run(["git", *args], cwd=cwd, timeout=timeout)


def same_commit(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    # Allow short SHAs in pins, but never compare fewer than 7 hex chars.
    if len(left) >= 7 and len(right) >= 7:
        return left.startswith(right) or right.startswith(left)
    return False


def repo_slug(url_or_slug: str) -> str:
    """Return owner/repo from a GitHub URL or a plain owner/repo slug."""
    value = url_or_slug.strip()
    if "://" in value:
        path = urllib.parse.urlparse(value).path.strip("/")
    else:
        path = value.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"cannot parse repository: {url_or_slug!r}")
    return "/".join(parts[-2:])


def gitlab_project(url_or_slug: str) -> str:
    """Return group/project from a GitLab URL or a plain group/project slug."""
    value = url_or_slug.strip()
    if "://" in value:
        path = urllib.parse.urlparse(value).path.strip("/")
    else:
        path = value.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"cannot parse GitLab project: {url_or_slug!r}")
    return "/".join(parts)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"pin file not found: {path}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"pin file must be a JSON object: {path}")
    return data


def http_json(url: str, token: str | None = None, token_header: str = "Authorization") -> tuple[dict[str, Any] | None, str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "haydn-nova-upstream-check/1.0",
    }
    if token:
        if token_header == "PRIVATE-TOKEN":
            headers["PRIVATE-TOKEN"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return None, f"HTTP {exc.code}: {detail or exc.reason}"
    except urllib.error.URLError as exc:
        return None, f"network: {exc.reason}"
    except TimeoutError:
        return None, "network: timeout"
    except Exception as exc:
        return None, f"request failed: {exc}"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON response: {exc}"
    if not isinstance(data, dict):
        return None, "unexpected JSON response"
    return data, None


def remote_head(url: str, ref: str) -> tuple[str | None, str | None]:
    """Read a branch head with git ls-remote; no API quota used."""
    refspec = ref if ref.startswith("refs/") else f"refs/heads/{ref}"
    code, out, err = run(["git", "ls-remote", url, refspec], timeout=40)
    if code != 0:
        return None, f"git ls-remote failed: {err or out or f'exit {code}'}"
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == refspec:
            return parts[0], None
    return None, f"ref not found: {refspec}"


def compare_github(slug: str, base: str, head: str, token: str | None) -> tuple[dict[str, Any] | None, str | None]:
    base_q = urllib.parse.quote(base, safe="")
    head_q = urllib.parse.quote(head, safe="")
    url = f"https://api.github.com/repos/{slug}/compare/{base_q}...{head_q}"
    data, err = http_json(url, token)
    if err:
        return None, err
    if not data:
        return None, "empty compare response"
    return data, None


def compare_gitlab(project: str, base: str, head: str, token: str | None) -> tuple[dict[str, Any] | None, str | None]:
    project_q = urllib.parse.quote(project, safe="")
    base_q = urllib.parse.quote(base, safe="")
    head_q = urllib.parse.quote(head, safe="")
    url = (
        f"https://gitlab.com/api/v4/projects/{project_q}/repository/compare"
        f"?from={base_q}&to={head_q}"
    )
    return http_json(url, token, token_header="PRIVATE-TOKEN")


def collect_github_compare(data: dict[str, Any]) -> dict[str, Any]:
    commits = []
    for item in (data.get("commits") or [])[:MAX_COMMITS]:
        commit = item.get("commit") or {}
        message = (commit.get("message") or "").splitlines()
        commits.append({
            "sha": (item.get("sha") or "")[:12],
            "subject": message[0] if message else "",
        })
    files = []
    for item in (data.get("files") or [])[:MAX_FILES]:
        path = item.get("filename") or item.get("previous_filename") or ""
        if path:
            files.append(path)
    return {
        "status": data.get("status") or "unknown",
        "ahead_by": data.get("ahead_by"),
        "behind_by": data.get("behind_by"),
        "total_commits": data.get("total_commits"),
        "commits": commits,
        "files": files,
    }


def collect_gitlab_compare(data: dict[str, Any]) -> dict[str, Any]:
    commits = []
    for item in (data.get("commits") or [])[:MAX_COMMITS]:
        commits.append({
            "sha": (item.get("short_id") or item.get("id") or "")[:12],
            "subject": item.get("title") or "",
        })
    files = []
    for item in (data.get("diffs") or [])[:MAX_FILES]:
        path = item.get("new_path") or item.get("old_path") or ""
        if path:
            files.append(path)
    return {
        "status": "ahead",
        "ahead_by": data.get("ahead_by"),
        "behind_by": data.get("behind_by"),
        "total_commits": len(data.get("commits") or []),
        "commits": commits,
        "files": files,
    }


def impact_files(files: list[str], patterns: tuple[str, ...]) -> list[str]:
    result = []
    for path in files:
        if any(path == p or path.startswith(p) for p in patterns):
            result.append(path)
    return result


def check_local(root: Path, pins: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    head_pin = str(pins.get("head_commit") or "")
    head_actual = ""
    head_code, head_out, _ = git(["rev-parse", "HEAD"], root)
    if head_code == 0:
        head_actual = head_out
    head_same = bool(head_actual and head_pin and same_commit(head_actual, head_pin))
    head_ancestor = False
    if head_pin and not head_same:
        head_ancestor_code, _, _ = git(["merge-base", "--is-ancestor", head_pin, "HEAD"], root)
        head_ancestor = head_ancestor_code == 0
    head_ok = bool(head_actual and head_pin and (head_same or head_ancestor))
    if head_same:
        head_detail = "主线 HEAD 与 pin 一致"
    elif head_ancestor:
        head_detail = "主线 HEAD 已前进，pin 仍在当前历史中"
    else:
        head_detail = "主线 HEAD 与 pin 不一致，且 pin 不在当前历史中"
    result["head"] = {
        "actual": head_actual,
        "pin": head_pin,
        "same": head_same,
        "ancestor": head_ancestor,
        "ok": head_ok,
        "detail": head_detail,
    }

    branch_code, branch_out, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    expected_branch = str(pins.get("branch") or "")
    result["branch"] = {
        "actual": branch_out if branch_code == 0 else "",
        "expected": expected_branch,
        "detached": branch_code == 0 and branch_out == "HEAD",
    }

    ksu_pin = str(pins.get("ksu_commit") or "")
    ksu_root = root / "KernelSU"
    ksu_code, ksu_out, _ = git(["rev-parse", "HEAD"], ksu_root)
    result["ksu_submodule"] = {
        "actual": ksu_out if ksu_code == 0 else "",
        "pin": ksu_pin,
        "ok": bool(ksu_code == 0 and ksu_pin and same_commit(ksu_out, ksu_pin)),
        "detail": "KernelSU 子模块与 pin 一致" if ksu_code == 0 and same_commit(ksu_out, ksu_pin) else "KernelSU 子模块与 pin 不一致或缺失",
    }

    audit_commit = ""
    audit_error = ""
    try:
        text = (root / AUDIT_PATH).read_text(encoding="utf-8")
        match = re.search(r"^audited_submodule_commit:\s*([0-9a-fA-F]{40})\s*$", text, re.MULTILINE)
        if match:
            audit_commit = match.group(1)
        else:
            audit_error = "audited_submodule_commit 未找到"
    except OSError as exc:
        audit_error = f"读取审计表失败: {exc}"
    result["upstream_audit"] = {
        "commit": audit_commit,
        "ksu_pin": ksu_pin,
        "ok": bool(audit_commit and ksu_pin and same_commit(audit_commit, ksu_pin)),
        "detail": audit_error or ("审计表与 KSU pin 一致" if same_commit(audit_commit, ksu_pin) else "审计表与 KSU pin 不一致"),
    }

    baseline_code, baseline_out, baseline_err = run(
        ["bash", str(root / SUSFS_BASELINE_SCRIPT)], cwd=root, timeout=60
    )
    result["susfs_baseline"] = {
        "ok": baseline_code == 0,
        "detail": "SUSFS 工作树与基线一致" if baseline_code == 0 else (baseline_err or baseline_out)[-300:],
    }

    baseline_tag = str(pins.get("susfs_baseline_tag") or "")
    tag_code, _, tag_err = git(["rev-parse", "--verify", f"{baseline_tag}^{{commit}}"], root)
    result["susfs_baseline_tag"] = {
        "tag": baseline_tag,
        "exists": tag_code == 0,
        "ok": tag_code == 0,
        "detail": "基线 tag 存在" if tag_code == 0 else (tag_err or "基线 tag 不存在"),
    }

    kernel_pin = str(pins.get("kernel_base_commit") or "")
    ancestor_code, _, ancestor_err = git(["merge-base", "--is-ancestor", kernel_pin, "HEAD"], root)
    result["kernel_base_ancestor"] = {
        "pin": kernel_pin,
        "ok": ancestor_code == 0,
        "detail": "内核底包 pin 是主线祖先" if ancestor_code == 0 else (ancestor_err or "内核底包 pin 不是主线祖先，或本地缺少该 commit"),
    }
    return result


def check_upstream(name: str, url: str, ref: str, pin: str, kind: str, token: str | None,
                   patterns: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "ref": ref,
        "pin": pin,
        "remote_head": "",
        "new_commits": False,
        "ahead_by": None,
        "behind_by": None,
        "status": "unknown",
        "detail": "",
        "commits": [],
        "files": [],
        "impact_files": [],
    }
    if not pin:
        result["detail"] = "pin 为空，无法比较"
        return result

    head, err = remote_head(url, ref)
    if err:
        result["status"] = "error"
        result["detail"] = err
        return result
    result["remote_head"] = head or ""
    if not head:
        result["status"] = "error"
        result["detail"] = "remote head 为空"
        return result
    if same_commit(head, pin):
        result["status"] = "up-to-date"
        result["detail"] = "上游 HEAD 与 pin 一致"
        return result

    result["new_commits"] = True
    result["status"] = "new-head"
    result["detail"] = "上游 HEAD 已前进，commit 详情待确认"

    if kind == "github":
        slug = repo_slug(url)
        data, compare_err = compare_github(slug, pin, head, token)
        collected = collect_github_compare(data) if data else None
    elif kind == "gitlab":
        project = gitlab_project(url)
        data, compare_err = compare_gitlab(project, pin, head, token)
        collected = collect_gitlab_compare(data) if data else None
    else:
        compare_err, collected = "unknown upstream kind", None

    if not collected:
        result["detail"] = f"发现新 HEAD；compare 不可用: {compare_err or '空响应'}"
        return result

    result.update(collected)
    result["impact_files"] = impact_files(result["files"], patterns)
    if result["status"] == "ahead":
        result["detail"] = f"落后上游 {result['ahead_by'] if result['ahead_by'] is not None else result['total_commits']} 个 commit"
    elif result["status"] == "diverged":
        result["detail"] = "pin 与上游已分叉（可能 rebase/force-push），需要人工核对"
    elif result["status"] == "behind":
        result["detail"] = "pin 反而领先上游，pin 可能指向了未合并/未来提交"
    return result


def check_manager_release(token: str | None, pins: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "checked": False,
        "latest_tag": "",
        "pinned_tag": str(pins.get("manager_release") or ""),
        "latest_apk": "",
        "pinned_apk": str(pins.get("manager_apk") or ""),
        "asset_sha256": "",
        "pinned_sha256": str(pins.get("manager_apk_sha256") or ""),
        "sha_checked": False,
        "ok": False,
        "detail": "",
    }
    repo = str(pins.get("ksu_repo") or "")
    if not repo:
        result["detail"] = "ksu_repo 为空"
        return result
    data, err = http_json(f"https://api.github.com/repos/{repo}/releases/latest", token)
    if err:
        result["detail"] = f"无法查询最新 Release: {err}"
        return result
    result["checked"] = True
    result["latest_tag"] = str(data.get("tag_name") or "")
    assets = data.get("assets") or []
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.endswith(".apk") and "arm64-v8a" in name:
            result["latest_apk"] = name
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:"):
                result["asset_sha256"] = digest.split(":", 1)[1]
            break
    tag_ok = bool(result["latest_tag"] and same_commit(result["latest_tag"], result["pinned_tag"]))
    apk_ok = bool(result["latest_apk"] and result["pinned_apk"] and result["latest_apk"] == result["pinned_apk"])
    sha_checked = bool(result["asset_sha256"] and result["pinned_sha256"])
    sha_ok = True
    if sha_checked:
        sha_ok = result["asset_sha256"].lower() == result["pinned_sha256"].lower()
    result["sha_checked"] = sha_checked
    result["ok"] = tag_ok and apk_ok and sha_ok
    if result["ok"]:
        if sha_checked:
            result["detail"] = "最新 Release、APK 文件名和 SHA256 与 pin 一致"
        else:
            result["detail"] = "最新 Release 和 APK 文件名与 pin 一致；SHA256 未由 API 提供，未校验"
    else:
        parts = []
        if not tag_ok:
            parts.append(f"Release tag: 最新 {result['latest_tag'] or '未知'} / pin {result['pinned_tag'] or '未知'}")
        if not apk_ok:
            parts.append(f"APK: 最新 {result['latest_apk'] or '未找到'} / pin {result['pinned_apk'] or '未知'}")
        if not sha_ok:
            parts.append("APK SHA256 与 pin 不一致")
        result["detail"] = "；".join(parts)
    return result


def summarize(root: Path, pins: dict[str, Any], local: dict[str, Any],
              upstreams: dict[str, dict[str, Any]], manager: dict[str, Any]) -> dict[str, Any]:
    local_checks = [v for k, v in local.items() if isinstance(v, dict) and "ok" in v]
    local_ok = all(bool(v.get("ok")) for v in local_checks)
    updates = [name for name, item in upstreams.items() if item.get("new_commits")]
    errors = [name for name, item in upstreams.items() if item.get("status") == "error"]
    skipped = [name for name, item in upstreams.items() if item.get("status") == "skipped"]
    manager_ok = bool(manager.get("ok")) if manager.get("checked") else None
    return {
        "local_ok": local_ok,
        "local_failures": [k for k, v in local.items() if isinstance(v, dict) and "ok" in v and not v.get("ok")],
        "updates": updates,
        "errors": errors,
        "skipped": skipped,
        "manager_checked": bool(manager.get("checked")),
        "manager_ok": manager_ok,
        "has_changes": bool(updates),
        "has_errors": bool(errors),
    }


def render_text(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    s = payload["summary"]
    lines.append("Nova 上游巡检")
    lines.append(f"仓库: {payload['root']}")
    lines.append(f"时间: {payload['generated_at']}")
    lines.append("")
    lines.append(f"本地 pin: {'PASS' if s['local_ok'] else 'FAIL'}")
    if s["local_failures"]:
        lines.append(f"  失败项: {', '.join(s['local_failures'])}")
    lines.append("")
    for key, label in (("kernel", "MiYume"), ("ksu", "SukiSU-Nova"), ("susfs", "SUSFS")):
        item = payload["upstreams"][key]
        lines.append(f"[{label}] {item['status']}: {item['detail']}")
        lines.append(f"  pin: {item['pin'] or '-'}  remote: {item['remote_head'] or '-'}")
        for commit in item.get("commits") or []:
            lines.append(f"  - {commit['sha']} {commit['subject']}")
        if item.get("impact_files"):
            lines.append(f"  可能影响: {', '.join(item['impact_files'][:8])}")
        elif item.get("files"):
            lines.append(f"  改动文件: {', '.join(item['files'][:8])}")
    if payload.get("manager"):
        m = payload["manager"]
        if m.get("checked"):
            manager_label = "PASS" if m.get("ok") else "FAIL"
        else:
            manager_label = "SKIP"
        lines.append("")
        lines.append(f"[管理器] {manager_label}: {m.get('detail', '')}")
    lines.append("")
    if s["has_errors"]:
        lines.append(f"结论: 巡检存在错误，无法确认全部上游状态 -> {', '.join(s['errors'])}")
    elif s.get("skipped") and len(s["skipped"]) == 3:
        lines.append("结论: 离线模式，未检查上游")
    elif s["updates"]:
        lines.append(f"结论: 有上游更新 -> {', '.join(s['updates'])}")
    else:
        lines.append("结论: 三个上游均无新提交")
    return "\n".join(lines)


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines: list[str] = []
    lines.append("# Nova 上游巡检")
    lines.append("")
    lines.append(f"- 仓库：`{payload['root']}`")
    lines.append(f"- 时间：{payload['generated_at']}")
    lines.append(f"- 本地 pin：**{'PASS' if s['local_ok'] else 'FAIL'}**")
    if s["local_failures"]:
        lines.append(f"  - 失败项：`{', '.join(s['local_failures'])}`")
    lines.append("")
    lines.append("## 上游")
    lines.append("")
    lines.append("| 上游 | 状态 | pin | remote HEAD | 说明 |")
    lines.append("|---|---|---|---|---|")
    labels = {"kernel": "MiYume 内核", "ksu": "SukiSU-Nova", "susfs": "SUSFS"}
    for key in ("kernel", "ksu", "susfs"):
        item = payload["upstreams"][key]
        lines.append(
            f"| {labels[key]} | {md_cell(item['status'])} | `{(item['pin'] or '-')[:12]}` | "
            f"`{(item['remote_head'] or '-')[:12]}` | {md_cell(item['detail'])} |"
        )
    lines.append("")
    for key in ("kernel", "ksu", "susfs"):
        item = payload["upstreams"][key]
        if not item.get("commits"):
            continue
        lines.append(f"### {labels[key]}")
        lines.append("")
        for commit in item["commits"]:
            lines.append(f"- `{commit['sha']}` {commit['subject']}")
        if item.get("impact_files"):
            lines.append(f"- 可能影响：`{', '.join(item['impact_files'][:8])}`")
        lines.append("")
    if payload.get("manager"):
        m = payload["manager"]
        if m.get("checked"):
            manager_label = "PASS" if m.get("ok") else "FAIL"
        else:
            manager_label = "SKIP"
        lines.append("## 管理器")
        lines.append("")
        lines.append(f"- 状态：**{manager_label}**")
        lines.append(f"- {m.get('detail', '')}")
        lines.append("")
    lines.append("## 结论")
    lines.append("")
    if s["has_errors"]:
        lines.append(f"巡检存在错误，无法确认全部上游状态：`{', '.join(s['errors'])}`。")
    elif s.get("skipped") and len(s["skipped"]) == 3:
        lines.append("离线模式，未检查上游。")
    elif s["updates"]:
        lines.append(f"有上游更新：`{', '.join(s['updates'])}`。")
    else:
        lines.append("三个上游均无新提交。")
    return "\n".join(lines)


def build_payload(root: Path, pins: dict[str, Any], no_network: bool,
                  github_token: str | None, gitlab_token: str | None) -> dict[str, Any]:
    local = check_local(root, pins)
    upstreams: dict[str, dict[str, Any]] = {}
    manager: dict[str, Any] = {}
    if no_network:
        for key, label in (("kernel", "MiYume"), ("ksu", "SukiSU-Nova"), ("susfs", "SUSFS")):
            upstreams[key] = {
                "name": label, "url": "", "ref": "", "pin": "",
                "remote_head": "", "new_commits": False, "status": "skipped",
                "detail": "离线模式，未检查远端", "commits": [], "files": [], "impact_files": [],
            }
        manager = {"checked": False, "ok": None, "detail": "离线模式，未检查管理器 Release"}
    else:
        kernel_url = str(pins.get("kernel_upstream") or "")
        kernel_ref = str(pins.get("kernel_branch") or "main")
        ksu_url = f"https://github.com/{pins.get('ksu_repo')}.git"
        ksu_ref = str(pins.get("ksu_ref") or "builtin-new")
        susfs_url = str(pins.get("susfs_upstream") or "")
        susfs_ref = str(pins.get("susfs_branch") or "gki-android14-5.15")
        upstreams["kernel"] = check_upstream(
            "MiYume", kernel_url, kernel_ref, str(pins.get("kernel_base_commit") or ""),
            "github", github_token, KERNEL_IMPACT_PATTERNS,
        )
        upstreams["ksu"] = check_upstream(
            "SukiSU-Nova", ksu_url, ksu_ref, str(pins.get("ksu_commit") or ""),
            "github", github_token, KSU_IMPACT_PATTERNS,
        )
        upstreams["susfs"] = check_upstream(
            "SUSFS", susfs_url, susfs_ref,
            str(pins.get("susfs_branch_head_at_audit") or pins.get("susfs_upstream_commit") or ""),
            "gitlab", gitlab_token, SUSFS_IMPACT_PATTERNS,
        )
        manager = check_manager_release(github_token, pins)
    summary = summarize(root, pins, local, upstreams, manager)
    return {
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "pins": pins,
        "local": local,
        "upstreams": upstreams,
        "manager": manager,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nova 线三个上游的只读巡检")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="仓库根目录")
    parser.add_argument("--pins", default="", help="pin JSON 路径；默认 <root>/maintenance/ksu-pins.json")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    parser.add_argument("--offline", action="store_true", help="只做本地 pin 检查，不访问上游")
    parser.add_argument("--fail-on-update", action="store_true", help="有上游更新或本地 pin 失败时返回 2")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    pins_path = Path(args.pins).resolve() if args.pins else root / PINS_DEFAULT
    try:
        pins = read_json(pins_path)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    github_token = os.environ.get("GITHUB_TOKEN") or None
    gitlab_token = os.environ.get("GITLAB_TOKEN") or None
    try:
        payload = build_payload(root, pins, args.offline, github_token, gitlab_token)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(render_markdown(payload))
    else:
        print(render_text(payload))

    s = payload["summary"]
    if s["has_errors"]:
        return 1
    if args.fail_on_update and (s["has_changes"] or not s["local_ok"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
