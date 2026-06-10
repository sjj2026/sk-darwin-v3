#!/usr/bin/env python3
"""
sk-darwin-v3 双平台周报生成器（cron 版本）
先采集最新数据，再生成报告

依赖环境变量：
  GH_TOKEN - GitHub Personal Access Token
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

REPO_NAME = "sk-darwin-v3"
MONITOR_SCRIPT = os.path.expanduser(f"~/.hermes/scripts/monitor_sk_darwin_v3.py")
DATA_FILE = os.path.expanduser(f"~/.hermes/cron/output/{REPO_NAME}_stats.json")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"history": []}

def get_weekly_change(current, previous):
    if previous is None or previous == 0:
        return f"+{current}" if current > 0 else "0"
    diff = current - previous
    if diff > 0:
        return f"↑ +{diff}"
    elif diff < 0:
        return f"↓ {diff}"
    return "→ 0"

def main():
    # Step 1: Run monitor to get fresh data
    print("📡 采集最新数据...")
    gh_token = os.environ.get("GH_TOKEN", "")
    env = {**os.environ}
    if gh_token:
        env["GH_TOKEN"] = gh_token
    
    result = subprocess.run(
        [sys.executable, MONITOR_SCRIPT],
        capture_output=True, text=True, timeout=30,
        env=env
    )
    if result.returncode != 0:
        print(f"⚠️ 监控脚本异常: {result.stderr}")
    
    # Step 2: Generate report
    data = load_data()
    history = data.get("history", [])
    
    if len(history) < 1:
        print("📊 sk-darwin-v3 周报\n暂无数据")
        return
    
    latest = history[-1]
    prev = history[-2] if len(history) >= 2 else None
    
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")
    
    report = []
    report.append(f"📊 **sk-darwin-v3 双平台周报**")
    report.append(f"📅 {week_start} ~ {week_end}")
    report.append("")
    
    # GitHub
    report.append("🔵 **GitHub** (sjj2026/sk-darwin-v3)")
    gh = latest.get("github", {})
    if "error" not in gh:
        gh_prev = prev.get("github", {}) if prev else {}
        stars = gh.get("stars", 0)
        report.append(f"  ⭐ Stars: {stars} {get_weekly_change(stars, gh_prev.get('stars', 0) if gh_prev else None)}")
        forks = gh.get("forks", 0)
        report.append(f"  🍴 Forks: {forks} {get_weekly_change(forks, gh_prev.get('forks', 0) if gh_prev else None)}")
        watchers = gh.get("watchers", 0)
        report.append(f"  👁 Watchers: {watchers} {get_weekly_change(watchers, gh_prev.get('watchers', 0) if gh_prev else None)}")
        
        gh_clones = latest.get("github_clones", {})
        if gh_clones.get("count") is not None:
            report.append(f"  📥 Clones: {gh_clones.get('count', 'N/A')}")
        gh_views = latest.get("github_views", {})
        if gh_views.get("count") is not None:
            report.append(f"  👀 Views: {gh_views.get('count', 'N/A')}")
        report.append(f"  🔗 {gh.get('url', '')}")
    else:
        report.append(f"  ❌ {gh.get('error', '获取失败')}")
    
    report.append("")
    
    # Gitee
    report.append("🟢 **Gitee** (shike-skill/sk-darwin-v3)")
    gt = latest.get("gitee", {})
    if "error" not in gt:
        gt_prev = prev.get("gitee", {}) if prev else {}
        stars = gt.get("stars", 0)
        report.append(f"  ⭐ Stars: {stars} {get_weekly_change(stars, gt_prev.get('stars', 0) if gt_prev else None)}")
        forks = gt.get("forks", 0)
        report.append(f"  🍴 Forks: {forks} {get_weekly_change(forks, gt_prev.get('forks', 0) if gt_prev else None)}")
        watchers = gt.get("watchers", 0)
        report.append(f"  👁 Watchers: {watchers} {get_weekly_change(watchers, gt_prev.get('watchers', 0) if gt_prev else None)}")
        report.append(f"  🔗 {gt.get('url', '')}")
    else:
        report.append(f"  ❌ {gt.get('error', '获取失败')}")
    
    report.append("")
    
    # Summary
    total_stars = (gh.get("stars", 0) if "error" not in gh else 0) + (gt.get("stars", 0) if "error" not in gt else 0)
    report.append(f"📈 **趋势总结**")
    report.append(f"  双平台总 Stars: {total_stars}")
    report.append(f"  数据采集: {latest.get('timestamp', 'N/A')}")
    
    print("\n".join(report))

if __name__ == "__main__":
    main()
