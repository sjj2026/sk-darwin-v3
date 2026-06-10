#!/usr/bin/env python3
"""
技能分组聚合器
按技能分组会话证据，形成自然消融实验

核心功能：
1. 从会话轨迹中提取证据
2. 按技能分组聚合
3. 计算成功率和失败模式
4. 提取成功不变量
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime

class SkillGrouper:
    """技能分组聚合器"""
    
    def __init__(self, evidence_path: str = None):
        if evidence_path:
            self.evidence_path = Path(evidence_path)
        else:
            self.evidence_path = Path.home() / ".openclaw" / "workspace" / "session_evidence.json"
            
    def load_trajectories(self) -> List[Dict]:
        """加载所有会话轨迹"""
        if not self.evidence_path.exists():
            return []
            
        try:
            with open(self.evidence_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("trajectories", [])
        except json.JSONDecodeError:
            return []
            
    def group_by_skill(self, trajectories: List[Dict] = None) -> Dict[str, List[Dict]]:
        """按技能分组会话证据
        
        返回：
        {
            "skill_A": [trajectory1, trajectory2, ...],
            "skill_B": [trajectory3, ...],
            "∅": [trajectory_no_skill, ...]
        }
        """
        if trajectories is None:
            trajectories = self.load_trajectories()
            
        groups = defaultdict(list)
        
        for trajectory in trajectories:
            skills = trajectory.get("skills_invoked", [])
            
            if skills:
                # 为每个调用的技能添加轨迹
                for skill in skills:
                    groups[skill].append(trajectory)
            else:
                # 无技能调用的轨迹归入G(∅)
                groups["∅"].append(trajectory)
                
        return dict(groups)
    
    def calculate_group_statistics(self, group: List[Dict]) -> Dict:
        """计算证据组的统计信息
        
        返回：
        {
            "count": 总轨迹数,
            "success_count": 成功轨迹数,
            "failure_count": 失败轨迹数,
            "success_rate": 成功率,
            "unique_users": 唯一用户数,
            "avg_steps": 平均步骤数,
            "avg_duration_ms": 平均持续时间,
            "failure_patterns": 失败模式列表,
            "success_invariants": 成功不变量列表,
            "error_distribution": 错误分布,
            "tool_usage": 工具使用统计
        }
        """
        if not group:
            return {
                "count": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "unique_users": 0,
                "avg_steps": 0.0,
                "avg_duration_ms": 0.0,
                "failure_patterns": [],
                "success_invariants": [],
                "error_distribution": {},
                "tool_usage": {}
            }
            
        total = len(group)
        successes = [t for t in group if t.get("success", False)]
        failures = [t for t in group if not t.get("success", False)]
        
        unique_users = len(set(t.get("user_id", "unknown") for t in group))
        avg_steps = sum(t["metrics"]["total_steps"] for t in group) / total
        avg_duration = sum(t["metrics"]["duration_ms"] for t in group) / total
        
        # 识别失败模式
        failure_patterns = self._identify_failure_patterns(failures)
        
        # 提取成功不变量
        success_invariants = self._extract_success_invariants(successes)
        
        # 错误分布
        error_distribution = self._calculate_error_distribution(group)
        
        # 工具使用统计
        tool_usage = self._calculate_tool_usage(group)
        
        return {
            "count": total,
            "success_count": len(successes),
            "failure_count": len(failures),
            "success_rate": len(successes) / total if total > 0 else 0.0,
            "unique_users": unique_users,
            "avg_steps": avg_steps,
            "avg_duration_ms": avg_duration,
            "failure_patterns": failure_patterns,
            "success_invariants": success_invariants,
            "error_distribution": error_distribution,
            "tool_usage": tool_usage
        }
        
    def _identify_failure_patterns(self, failures: List[Dict]) -> List[Dict]:
        """识别失败模式"""
        if not failures:
            return []
            
        patterns = []
        error_types = Counter()
        error_contexts = defaultdict(list)
        
        for trajectory in failures:
            for step in trajectory.get("causal_chain", []):
                if step.get("action") == "error_encountered":
                    error_type = step.get("error_type", "Unknown")
                    error_message = step.get("error_message", "")
                    context = step.get("context", {})
                    
                    error_types[error_type] += 1
                    error_contexts[error_type].append({
                        "message": error_message,
                        "context": context,
                        "trajectory_id": trajectory.get("trajectory_id")
                    })
                    
        # 返回出现次数≥2的错误模式
        for error_type, count in error_types.most_common():
            if count >= 2:
                patterns.append({
                    "error_type": error_type,
                    "frequency": count,
                    "examples": error_contexts[error_type][:3]  # 最多显示3个示例
                })
                
        return patterns
        
    def _extract_success_invariants(self, successes: List[Dict]) -> List[Dict]:
        """提取成功不变量
        
        识别所有成功轨迹中共同的关键特征
        """
        if not successes:
            return []
            
        invariants = []
        
        # 1. 检查是否有共同的验证步骤
        validation_steps = []
        for trajectory in successes:
            for step in trajectory.get("causal_chain", []):
                if "validation" in step.get("action", "").lower() or \
                   "check" in step.get("action", "").lower():
                    validation_steps.append(step.get("action"))
                    
        if validation_steps:
            most_common = Counter(validation_steps).most_common(1)[0]
            if most_common[1] >= len(successes) * 0.8:  # 80%以上的成功轨迹都有这个步骤
                invariants.append({
                    "type": "validation_step",
                    "description": f"存在验证步骤：{most_common[0]}",
                    "frequency": most_common[1]
                })
                
        # 2. 检查工具使用模式
        tool_patterns = []
        for trajectory in successes:
            tools_used = [
                step.get("tool") for step in trajectory.get("causal_chain", [])
                if step.get("action") == "tool_call"
            ]
            tool_patterns.append(tuple(tools_used))
            
        if tool_patterns:
            most_common_pattern = Counter(tool_patterns).most_common(1)[0]
            if most_common_pattern[1] >= len(successes) * 0.6:  # 60%以上的成功轨迹使用相同的工具序列
                invariants.append({
                    "type": "tool_sequence",
                    "description": f"共同工具序列：{' → '.join(most_common_pattern[0])}",
                    "frequency": most_common_pattern[1]
                })
                
        # 3. 检查错误处理
        has_error_handling = []
        for trajectory in successes:
            has_error = any(
                step.get("action") == "error_encountered" 
                for step in trajectory.get("causal_chain", [])
            )
            has_recovery = any(
                step.get("recovery_action") 
                for step in trajectory.get("causal_chain", [])
                if step.get("action") == "error_encountered"
            )
            has_error_handling.append(has_error and has_recovery)
            
        if sum(has_error_handling) >= len(successes) * 0.5:
            invariants.append({
                "type": "error_handling",
                "description": "具备错误处理和恢复机制",
                "frequency": sum(has_error_handling)
            })
            
        return invariants
        
    def _calculate_error_distribution(self, trajectories: List[Dict]) -> Dict[str, int]:
        """计算错误分布"""
        error_dist = Counter()
        
        for trajectory in trajectories:
            for step in trajectory.get("causal_chain", []):
                if step.get("action") == "error_encountered":
                    error_type = step.get("error_type", "Unknown")
                    error_dist[error_type] += 1
                    
        return dict(error_dist)
        
    def _calculate_tool_usage(self, trajectories: List[Dict]) -> Dict[str, int]:
        """计算工具使用统计"""
        tool_usage = Counter()
        
        for trajectory in trajectories:
            for step in trajectory.get("causal_chain", []):
                if step.get("action") == "tool_call":
                    tool_name = step.get("tool", "unknown")
                    tool_usage[tool_name] += 1
                    
        return dict(tool_usage)
        
    def generate_report(self, output_path: str = None) -> Dict:
        """生成分组聚合报告"""
        groups = self.group_by_skill()
        
        if not groups:
            return {
                "generated_at": datetime.now().isoformat(),
                "total_skills": 0,
                "total_trajectories": 0,
                "groups": {}
            }
            
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_skills": len([k for k in groups.keys() if k != "∅"]),
            "total_trajectories": sum(len(v) for v in groups.values()),
            "groups": {}
        }
        
        for skill_name, trajectories in groups.items():
            stats = self.calculate_group_statistics(trajectories)
            report["groups"][skill_name] = stats
            
        # 保存报告
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
        return report
        
    def detect_natural_ablation_experiments(self) -> List[Dict]:
        """检测自然消融实验
        
        当多个用户在不同任务、不同环境下调用同一技能，得到不同结果时，
        技能本身是受控变量，可判断哪些场景下技能有效、哪些场景下会失败。
        """
        groups = self.group_by_skill()
        experiments = []
        
        for skill_name, trajectories in groups.items():
            if skill_name == "∅":
                continue
                
            # 按用户分组
            user_groups = defaultdict(list)
            for t in trajectories:
                user_groups[t.get("user_id", "unknown")].append(t)
                
            # 至少有2个用户，且成功率有显著差异
            if len(user_groups) >= 2:
                user_stats = {}
                for user_id, user_trajectories in user_groups.items():
                    successes = sum(1 for t in user_trajectories if t.get("success", False))
                    user_stats[user_id] = {
                        "total": len(user_trajectories),
                        "success_rate": successes / len(user_trajectories) if user_trajectories else 0
                    }
                    
                # 计算成功率差异
                rates = [s["success_rate"] for s in user_stats.values()]
                max_diff = max(rates) - min(rates)
                
                # 差异>30%，可能存在环境因素
                if max_diff > 0.3:
                    experiments.append({
                        "skill_name": skill_name,
                        "user_count": len(user_groups),
                        "user_stats": user_stats,
                        "success_rate_range": (min(rates), max(rates)),
                        "potential_factors": "环境差异可能导致成功率变化"
                    })
                    
        return experiments


if __name__ == "__main__":
    # 测试代码
    grouper = SkillGrouper("./test_evidence.json")
    
    # 生成报告
    report = grouper.generate_report("./test_groups_report.json")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # 检测自然消融实验
    experiments = grouper.detect_natural_ablation_experiments()
    if experiments:
        print("\n检测到自然消融实验：")
        for exp in experiments:
            print(f"  技能 {exp['skill_name']}: 用户成功率范围 {exp['success_rate_range']}")
