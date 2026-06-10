#!/usr/bin/env python3
"""
sk-darwin-v3 双平台监控脚本
监控 GitHub 和 Gitee 仓库的 Star、Fork、Clone 数据
输出 JSON 格式供 cron 任务读取

依赖环境变量：
  GH_TOKEN - GitHub Personal Access Token
  GITEE_TOKEN - Gitee Personal Access Token
"""
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_NAME = "sk-darwin-v3"
GITHUB_REPO = f"sjj2026/{REPO_NAME}"
GITEE_REPO = f"shike-skill/{REPO_NAME}"
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITEE_TOKEN = os.environ.get("GITEE_TOKEN", "a097dec9e19c4607d585cf818c4fee60")

DATA_FILE = os.path.expanduser(f"~/.hermes/cron/output/{REPO_NAME}_stats.json")

def get_github_stats():
    """Get GitHub repo stats"""
    if not GITHUB_TOKEN:
        return {"error": "GH_TOKEN not set"}
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{GITHUB_REPO}", "--jq",
             '{stargazers_count, forks_count, open_issues_count, watchers_count, description, html_url}'],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN}
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
                "issues": data.get("open_issues_count", 0),
                "url": data.get("html_url", f"https://github.com/{GITHUB_REPO}")
            }
        else:
            return {"error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

def get_github_traffic(endpoint):
    """Get GitHub traffic data (clones or views)"""
    if not GITHUB_TOKEN:
        return {}
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{GITHUB_REPO}/traffic/{endpoint}", "--jq",
             '{count:.count, uniques:.uniques}'],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN}
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return {"count": data.get("count", 0), "uniques": data.get("uniques", 0)}
        return {}
    except Exception:
        return {}

def get_gitee_stats():
    """Get Gitee repo stats"""
    try:
        result = subprocess.run(
            ["curl", "-s",
             "-H", f"Authorization: token {GITEE_TOKEN}",
             f"https://gitee.com/api/v5/repos/{GITEE_REPO}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
                "issues": data.get("open_issues_count", 0),
                "url": data.get("html_url", f"https://gitee.com/{GITEE_REPO}")
            }
        else:
            return {"error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}

def load_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            return {"history": []}
    return {"history": []}

def save_stats(stats):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"📊 sk-darwin-v3 双平台监控 [{now}]")
    print("=" * 50)
    
    # GitHub
    print("\n🔵 GitHub:")
    gh = get_github_stats()
    gh_clones = {}
    gh_views = {}
    if "error" in gh:
        print(f"   ❌ {gh['error']}")
    else:
        print(f"   ⭐ Stars: {gh['stars']}")
        print(f"   🍴 Forks: {gh['forks']}")
        print(f"   👁 Watchers: {gh['watchers']}")
        print(f"   📋 Issues: {gh['issues']}")
        print(f"   🔗 {gh['url']}")
        
        gh_clones = get_github_traffic("clones")
        if gh_clones:
            print(f"   📥 Clones: {gh_clones['count']} ({gh_clones['uniques']} unique)")
        
        gh_views = get_github_traffic("views")
        if gh_views:
            print(f"   👀 Views: {gh_views['count']} ({gh_views['uniques']} unique)")
    
    # Gitee
    print("\n🟢 Gitee:")
    gt = get_gitee_stats()
    if "error" in gt:
        print(f"   ❌ {gt['error']}")
    else:
        print(f"   ⭐ Stars: {gt['stars']}")
        print(f"   🍴 Forks: {gt['forks']}")
        print(f"   👁 Watchers: {gt['watchers']}")
        print(f"   📋 Issues: {gt['issues']}")
        print(f"   🔗 {gt['url']}")
    
    # Save history
    history = load_history()
    gh_clones = {}
    gh_views = {}
    entry = {
        "timestamp": now,
        "github": gh if "error" not in gh else gh,
        "gitee": gt if "error" not in gt else gt
    }
    if gh_clones:
        entry["github_clones"] = gh_clones
    if gh_views:
        entry["github_views"] = gh_views
    history["history"].append(entry)
    history["history"] = history["history"][-52:]
    save_stats(history)
    
    print("\n" + "=" * 50)
    print(f"✅ 数据已保存到 {DATA_FILE}")

if __name__ == "__main__":
    main()
