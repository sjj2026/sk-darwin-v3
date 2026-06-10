#!/usr/bin/env python3
"""
批量进化器
三动作决策：Refine/Create/Skip

核心功能：
1. 根据证据组决定进化动作
2. 生成候选更新
3. 保守编辑保护
4. 批量处理多个技能
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Literal, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

# 添加父目录到路径以导入skill_grouper
sys.path.insert(0, str(Path(__file__).parent))
from skill_grouper import SkillGrouper

@dataclass
class EvolutionCandidate:
    """进化候选"""
    candidate_id: str
    skill_name: str
    action: Literal["Refine", "Create", "Skip"]
    rationale: str
    proposed_changes: str
    expected_improvement: str
    priority: int  # 1-5，5最高
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class BatchEvolver:
    """批量进化器"""
    
    def __init__(self, evidence_path: str = None):
        self.grouper = SkillGrouper(evidence_path)
        self.candidates: List[EvolutionCandidate] = []
        
    def decide_action(
        self,
        skill_name: str,
        group_stats: Dict,
        min_samples: int = 5
    ) -> Tuple[Literal["Refine", "Create", "Skip"], str]:
        """决定进化动作
        
        决策逻辑：
        - 证据不足（<min_samples） → Skip
        - 成功率高（≥95%）且无失败模式 → Skip
        - 成功率低（<80%）且有失败模式 → Refine
        - 其他情况 → Skip
        """
        success_rate = group_stats.get("success_rate", 0.0)
        failure_patterns = group_stats.get("failure_patterns", [])
        count = group_stats.get("count", 0)
        
        # 证据不足 → Skip
        if count < min_samples:
            return "Skip", f"证据不足（{count}<{min_samples}个样本），无法得出可靠结论"
            
        # 成功率高且无失败模式 → Skip
        if success_rate >= 0.95 and not failure_patterns:
            return "Skip", f"性能稳定（成功率{success_rate:.1%}），无明确改进空间"
            
        # 成功率低且有明确失败模式 → Refine
        if success_rate < 0.8 and failure_patterns:
            pattern_desc = ", ".join([p["error_type"] for p in failure_patterns[:3]])
            return "Refine", f"成功率偏低（{success_rate:.1%}），发现失败模式：{pattern_desc}"
            
        # 成功率中等，但有失败模式 → Refine
        if 0.8 <= success_rate < 0.95 and failure_patterns:
            pattern_desc = ", ".join([p["error_type"] for p in failure_patterns[:2]])
            return "Refine", f"存在改进空间，发现失败模式：{pattern_desc}"
            
        # 默认 Skip
        return "Skip", "当前表现良好，暂无需修改"
        
    def generate_candidates(self, min_samples: int = 5) -> List[EvolutionCandidate]:
        """生成候选更新"""
        self.candidates = []
        groups = self.grouper.group_by_skill()
        
        if not groups:
            return []
            
        candidate_id = 1
        
        for skill_name, trajectories in groups.items():
            if skill_name == "∅":
                # 处理G(∅)：检测可复用模式
                patterns = self._detect_reusable_patterns(trajectories)
                for pattern in patterns:
                    candidate = EvolutionCandidate(
                        candidate_id=f"C{candidate_id:03d}",
                        skill_name=f"new_skill_{candidate_id}",
                        action="Create",
                        rationale=f"从无技能会话中发现可复用模式：{pattern['description']}",
                        proposed_changes=f"新建技能以封装该模式",
                        expected_improvement="+10% on D8[可扩展性]",
                        priority=3,
                        created_at=datetime.now().isoformat()
                    )
                    self.candidates.append(candidate)
                    candidate_id += 1
                continue
                
            # 计算统计信息
            stats = self.grouper.calculate_group_statistics(trajectories)
            
            # 决策
            action, rationale = self.decide_action(skill_name, stats, min_samples)
            
            if action == "Skip":
                continue
                
            # 计算优先级
            priority = self._calculate_priority(skill_name, stats)
            
            # 生成候选
            candidate = EvolutionCandidate(
                candidate_id=f"C{candidate_id:03d}",
                skill_name=skill_name,
                action=action,
                rationale=rationale,
                proposed_changes=self._propose_changes(skill_name, stats),
                expected_improvement=self._estimate_improvement(stats),
                priority=priority,
                created_at=datetime.now().isoformat()
            )
            
            self.candidates.append(candidate)
            candidate_id += 1
            
        # 按优先级排序
        self.candidates.sort(key=lambda c: c.priority, reverse=True)
        
        return self.candidates
        
    def _detect_reusable_patterns(self, trajectories: List[Dict]) -> List[Dict]:
        """检测可复用模式
        
        从G(∅)中发现反复出现的子流程
        """
        if len(trajectories) < 3:
            return []
            
        patterns = []
        
        # 1. 检测常见的工具调用序列
        tool_sequences = []
        for t in trajectories:
            if t.get("success", False):
                tools = [
                    step.get("tool") for step in t.get("causal_chain", [])
                    if step.get("action") == "tool_call"
                ]
                if tools:
                    tool_sequences.append(tuple(tools))
                    
        if tool_sequences:
            from collections import Counter
            most_common = Counter(tool_sequences).most_common(1)[0]
            if most_common[1] >= 3:  # 至少出现3次
                patterns.append({
                    "type": "tool_sequence",
                    "description": f"常见工具序列：{' → '.join(most_common[0])}",
                    "frequency": most_common[1]
                })
                
        # 2. 检测常见的决策模式
        decision_patterns = []
        for t in trajectories:
            if t.get("success", False):
                decisions = [
                    step.get("decision_type") for step in t.get("causal_chain", [])
                    if step.get("action") == "make_decision"
                ]
                if decisions:
                    decision_patterns.append(tuple(decisions))
                    
        if decision_patterns:
            from collections import Counter
            most_common = Counter(decision_patterns).most_common(1)[0]
            if most_common[1] >= 3:
                patterns.append({
                    "type": "decision_pattern",
                    "description": f"常见决策模式：{' → '.join(most_common[0])}",
                    "frequency": most_common[1]
                })
                
        return patterns
        
    def _calculate_priority(self, skill_name: str, stats: Dict) -> int:
        """计算进化优先级（1-5，5最高）
        
        考虑因素：
        - 成功率（越低优先级越高）
        - 失败模式数量（越多优先级越高）
        - 影响用户数（越多优先级越高）
        """
        priority = 3  # 基准优先级
        
        success_rate = stats.get("success_rate", 1.0)
        failure_patterns = stats.get("failure_patterns", [])
        unique_users = stats.get("unique_users", 1)
        
        # 成功率因素
        if success_rate < 0.5:
            priority += 2
        elif success_rate < 0.7:
            priority += 1
        elif success_rate >= 0.95:
            priority -= 2
            
        # 失败模式因素
        if len(failure_patterns) >= 3:
            priority += 1
            
        # 用户数因素
        if unique_users >= 5:
            priority += 1
            
        return max(1, min(5, priority))
        
    def _propose_changes(self, skill_name: str, stats: Dict) -> str:
        """提出修改建议"""
        failure_patterns = stats.get("failure_patterns", [])
        success_invariants = stats.get("success_invariants", [])
        
        proposals = []
        
        # 根据失败模式提出建议
        for pattern in failure_patterns[:3]:
            error_type = pattern.get("error_type", "")
            
            if "APIError" in error_type:
                proposals.append("修正API配置（端口、认证、参数格式）")
            elif "ValidationError" in error_type:
                proposals.append("增强输入验证和类型检查")
            elif "TimeoutError" in error_type:
                proposals.append("添加超时处理和重试机制")
            elif "FileNotFound" in error_type:
                proposals.append("添加文件存在性检查和fallback路径")
            elif "PermissionError" in error_type:
                proposals.append("添加权限检查和降级方案")
            else:
                proposals.append(f"处理{error_type}错误场景")
                
        # 保护成功不变量
        if success_invariants:
            proposals.append(f"保护成功不变量：{', '.join([i['description'] for i in success_invariants[:2]])}")
            
        return "; ".join(proposals) if proposals else "优化执行流程"
        
    def _estimate_improvement(self, stats: Dict) -> str:
        """估计改进效果"""
        success_rate = stats.get("success_rate", 1.0)
        failure_patterns = stats.get("failure_patterns", [])
        
        if success_rate < 0.5:
            return "+30% on D1[功能完整性] and D3[边界条件]"
        elif success_rate < 0.7:
            return "+20% on D3[边界条件]"
        elif len(failure_patterns) >= 2:
            return "+15% on D3[边界条件] and D6[安全性]"
        else:
            return "+10% on D3[边界条件]"
            
    def generate_evolution_report(self, output_path: str = None) -> Dict:
        """生成进化报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_candidates": len(self.candidates),
            "action_distribution": {
                "Refine": sum(1 for c in self.candidates if c.action == "Refine"),
                "Create": sum(1 for c in self.candidates if c.action == "Create"),
                "Skip": sum(1 for c in self.candidates if c.action == "Skip")
            },
            "candidates": [c.to_dict() for c in self.candidates]
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
        return report
        
    def apply_conservative_edit(
        self,
        original_skill: Dict,
        proposed_changes: str,
        success_invariants: List[Dict]
    ) -> Dict:
        """应用保守编辑
        
        原则：
        1. 保护成功不变量
        2. 最小化修改范围
        3. 向后兼容
        """
        # 这里是简化实现，实际应用中需要更复杂的逻辑
        # TODO: 实现实际的技能修改逻辑
        
        modified_skill = original_skill.copy()
        modified_skill["modifications"] = proposed_changes
        modified_skill["protected_invariants"] = success_invariants
        modified_skill["edit_timestamp"] = datetime.now().isoformat()
        
        return modified_skill


if __name__ == "__main__":
    # 测试代码
    evolver = BatchEvolver("./test_evidence.json")
    
    # 生成候选更新
    candidates = evolver.generate_candidates()
    
    print(f"生成 {len(candidates)} 个候选更新：")
    for c in candidates[:5]:  # 显示前5个
        print(f"  [{c.action}] {c.skill_name}: {c.rationale}")
        
    # 生成报告
    report = evolver.generate_evolution_report("./test_evolution_report.json")
    print(f"\n动作分布：{report['action_distribution']}")
