#!/usr/bin/env python3
"""上游巡检通知：有更新/异常才发，平时保持安静。

通知通道：
1. 配置 FEISHU_WEBHOOK_URL 时，优先发飞书群机器人。
2. 没有飞书 webhook，或飞书发送失败时，用 GitHub Issue @仓库 owner 兜底。

只读，不修改仓库，不创建 Release。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

LABELS = {"kernel": "MiYume", "ksu": "SukiSU-Nova", "susfs": "SUSFS"}
ISSUE_TITLE = "[上游巡检] 需要处理"


def read_payload(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"读取巡检 JSON 失败: {exc}", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def notify_reason(payload: dict[str, Any] | None, outcome: str) -> str | None:
    if payload is None:
        return "巡检没有生成 JSON，检查步骤可能失败"
    summary = payload.get("summary") or {}
    if outcome and outcome != "success":
        return f"检查步骤返回 {outcome}"
    if summary.get("has_errors"):
        return "巡检存在错误，无法确认全部上游状态"
    if not summary.get("local_ok"):
        return "本地 pin 校验失败"
    if summary.get("manager_checked") and not summary.get("manager_ok"):
        return "管理器 Release / APK / SHA256 与 pin 不一致"
    if summary.get("has_changes"):
        return "上游有新提交"
    return None


def build_text(payload: dict[str, Any] | None, reason: str, run_url: str, outcome: str) -> str:
    if payload is None:
        return "\n".join([
            "Nova 上游巡检异常",
            f"原因：{reason}",
            f"检查结果：{outcome or 'unknown'}",
            f"运行记录：{run_url}",
        ])

    summary = payload.get("summary") or {}
    lines = [
        "Nova 上游巡检",
        f"时间：{payload.get('generated_at', '-')}",
        f"结论：{reason}",
        f"本地 pin：{'PASS' if summary.get('local_ok') else 'FAIL'}",
        "",
        "上游：",
    ]
    for key in ("kernel", "ksu", "susfs"):
        item = (payload.get("upstreams") or {}).get(key) or {}
        lines.append(
            f"- {LABELS[key]}：{item.get('status', '-')}；"
            f"pin {(item.get('pin') or '-')[:12]} -> remote {(item.get('remote_head') or '-')[:12]}"
        )
        if item.get("detail"):
            lines.append(f"  {item['detail']}")
        for commit in (item.get("commits") or [])[:4]:
            lines.append(f"  - {commit.get('sha', '')[:12]} {commit.get('subject', '')}")
        if item.get("impact_files"):
            lines.append(f"  可能影响：{', '.join(item['impact_files'][:6])}")
    manager = payload.get("manager") or {}
    if manager.get("checked"):
        manager_state = "PASS" if manager.get("ok") else "FAIL"
    else:
        manager_state = "SKIP"
    lines += [
        "",
        f"管理器：{manager_state}",
        f"  {manager.get('detail', '-')}",
        "",
        f"运行记录：{run_url}",
    ]
    return "\n".join(lines)


def http_json(method: str, url: str, body: dict[str, Any] | None,
              headers: dict[str, str]) -> tuple[int, dict[str, Any] | None]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network: {exc.reason}") from exc


def send_feishu(webhook: str, secret: str, text: str) -> None:
    payload: dict[str, Any] = {"msg_type": "text", "content": {"text": text}}
    if secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        sign = base64.b64encode(
            hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    status, response = http_json(
        "POST", webhook, payload,
        {"Content-Type": "application/json; charset=utf-8"},
    )
    if status != 200:
        raise RuntimeError(f"Feishu HTTP {status}")
    if isinstance(response, dict) and response.get("code") not in (None, 0):
        raise RuntimeError(f"Feishu code={response.get('code')} msg={response.get('msg')}")
    print("Feishu 通知已发送")


def github_issue(text: str) -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("REPO", "")
    if not token or not repo:
        raise RuntimeError("缺少 GITHUB_TOKEN/REPO，无法使用 GitHub Issue 兜底")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "haydn-upstream-notify",
        "Content-Type": "application/json",
    }
    status, issues = http_json("GET", f"{api}/repos/{repo}/issues?state=open&per_page=100", None, headers)
    if status != 200 or not isinstance(issues, list):
        raise RuntimeError(f"查询 GitHub Issue 失败: HTTP {status}")
    existing = next((i for i in issues if i.get("title") == ISSUE_TITLE), None)
    owner = repo.split("/", 1)[0]
    body = f"{text}\n\n@{owner}"
    if existing:
        status, comment = http_json(
            "POST", f"{api}/repos/{repo}/issues/{existing['number']}/comments", {"body": body}, headers
        )
        if status not in (200, 201) or not comment:
            raise RuntimeError(f"追加 Issue 评论失败: HTTP {status}")
        print(f"GitHub Issue 评论已发送: {existing.get('html_url', '')}")
        return
    status, issue = http_json(
        "POST", f"{api}/repos/{repo}/issues",
        {"title": ISSUE_TITLE, "body": body}, headers,
    )
    if status not in (200, 201) or not issue:
        raise RuntimeError(f"创建 GitHub Issue 失败: HTTP {status}")
    print(f"GitHub Issue 已创建: {issue.get('html_url', '')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="上游巡检通知")
    parser.add_argument("--payload", default="", help="check-upstreams.py 的 JSON 输出")
    parser.add_argument("--run-url", default="", help="Actions run 链接")
    parser.add_argument("--check-outcome", default="success", help="检查步骤的 outcome")
    parser.add_argument("--dry-run", action="store_true", help="只打印通知内容，不发网络请求")
    args = parser.parse_args(argv)

    payload = read_payload(args.payload)
    reason = notify_reason(payload, args.check_outcome)
    if reason is None:
        print("无需通知：上游无更新，本地 pin 和管理器正常")
        return 0

    text = build_text(payload, reason, args.run_url, args.check_outcome)
    if args.dry_run:
        print("=== DRY_RUN 通知内容 ===")
        print(text)
        print("=== DRY_RUN 结束 ===")
        return 0

    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "")
    secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "")
    if webhook:
        try:
            send_feishu(webhook, secret, text)
            return 0
        except Exception as exc:
            print(f"飞书通知失败，改用 GitHub Issue 兜底: {exc}", file=sys.stderr)

    github_issue(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
