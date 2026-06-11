#!/usr/bin/env python3
"""個人 + pixi-teams の全リポジトリの言語バイト数を集計し、
README.md の <!-- LANG-STATS:START --> 〜 <!-- LANG-STATS:END --> を書き換える。

組織 private repo を読むため、gh は STATS_TOKEN(PAT) で認証している前提。
PAT の権限が足りず組織 repo を 1 件も読めなかった場合は、
誤って「公開分のみ」で上書きしないよう異常終了する。
"""
import json
import subprocess
import collections
import re
import sys
import pathlib

OWNERS = ["harutokun0705", "pixi-teams"]
# fork / 本体コピー系ツール（自分が書いたコードではない）は除外
EXCLUDE = {
    "harutokun0705/everything-claude-code",
    "harutokun0705/system-design-primer",
}
THRESHOLD = 3.0   # この % 未満は "Others" にまとめる
BAR_WIDTH = 28


def gh(args):
    return subprocess.run(["gh", *args], capture_output=True, text=True).stdout


def list_repos(owner):
    out = gh(["repo", "list", owner, "--limit", "300", "--json", "nameWithOwner,isFork"])
    try:
        return json.loads(out)
    except Exception:
        return []


def languages(repo):
    out = gh(["api", f"repos/{repo}/languages"])
    try:
        d = json.loads(out)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def make_bar(pct):
    filled = round(pct / 100 * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def main():
    total = collections.Counter()
    org_repo_seen = 0
    for owner in OWNERS:
        repos = list_repos(owner)
        for x in repos:
            r = x["nameWithOwner"]
            if x.get("isFork") or r in EXCLUDE:
                continue
            if owner == "pixi-teams":
                org_repo_seen += 1
            for k, v in languages(r).items():
                if isinstance(v, int):
                    total[k] += v

    # 組織 repo を 1 件も読めない＝PAT 権限不足。公開分での誤上書きを防ぐ
    if org_repo_seen == 0:
        print("ERROR: pixi-teams のリポジトリを 1 件も取得できませんでした（PAT 権限/SSO を確認）", file=sys.stderr)
        sys.exit(1)

    s = sum(total.values()) or 1
    items = total.most_common()
    major = [(k, v) for k, v in items if v * 100 / s >= THRESHOLD]
    others = sum(v for k, v in items if v * 100 / s < THRESHOLD)

    name_w = max([len(k) for k, _ in major] + [6])
    rows = []
    for k, v in major:
        p = v * 100 / s
        rows.append(f"{k:<{name_w}}  {make_bar(p)}  {p:4.1f} %")
    if others:
        p = others * 100 / s
        rows.append(f"{'Others':<{name_w}}  {make_bar(p)}  {p:4.1f} %")

    block = "```text\n" + "\n".join(rows) + "\n```"

    readme = pathlib.Path("README.md")
    txt = readme.read_text(encoding="utf-8")
    new = re.sub(
        r"(<!-- LANG-STATS:START.*?-->).*?(<!-- LANG-STATS:END -->)",
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
        txt,
        flags=re.S,
    )
    readme.write_text(new, encoding="utf-8")
    print(block)


if __name__ == "__main__":
    main()
