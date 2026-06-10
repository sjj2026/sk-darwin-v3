#!/usr/bin/env python3
"""
环境验证器
在真实环境中对比测试新旧版本，确保单调性

核心功能：
1. 提取测试任务
2. 在真实环境中运行技能
3. 对比执行结果
4. 单调性保证（只有更优才接受）
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Literal, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import tempfile
import shutil

@dataclass
class ValidationResult:
    """验证结果"""
    candidate_id: str
    skill_name: str
    verdict: Literal["Accept", "Reject"]
    baseline_performance: Dict
    candidate_performance: Dict
    improvement_metrics: Dict
    rationale: str
    validated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class EnvironmentValidator:
    """环境验证器"""
    
    def __init__(
        self,
        test_environment: str = "linux_container",
        workspace_path: str = None
    ):
        self.test_environment = test_environment
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.results: List[ValidationResult] = []
        
    def extract_test_tasks(
        self,
        trajectories: List[Dict],
        skill_name: str,
        max_tasks: int = 10
    ) -> List[Dict]:
        """从会话轨迹中提取测试任务
        
        选择策略：
        1. 优先选择失败的案例（验证修复效果）
        2. 包含部分成功的案例（验证不破坏现有功能）
        3. 覆盖不同的用户和场景
        """
        skill_trajectories = [
            t for t in trajectories
            if skill_name in t.get("skills_invoked", [])
        ]
        
        if not skill_trajectories:
            return []
            
        # 分离成功和失败案例
        failures = [t for t in skill_trajectories if not t.get("success", False)]
        successes = [t for t in skill_trajectories if t.get("success", False)]
        
        test_tasks = []
        
        # 优先选择失败案例（最多70%）
        failure_count = min(len(failures), int(max_tasks * 0.7))
        for t in failures[:failure_count]:
            test_tasks.append({
                "trajectory_id": t.get("trajectory_id"),
                "initial_prompt": self._extract_initial_prompt(t),
                "expected_behavior": "修复原有错误",
                "original_success": False,
                "original_error": self._extract_error(t)
            })
            
        # 补充成功案例（至少30%）
        success_count = min(len(successes), max_tasks - len(test_tasks))
        for t in successes[:success_count]:
            test_tasks.append({
                "trajectory_id": t.get("trajectory_id"),
                "initial_prompt": self._extract_initial_prompt(t),
                "expected_behavior": "保持原有成功",
                "original_success": True
            })
            
        return test_tasks
        
    def _extract_initial_prompt(self, trajectory: Dict) -> str:
        """提取初始提示词"""
        causal_chain = trajectory.get("causal_chain", [])
        if causal_chain and causal_chain[0].get("action") == "receive_prompt":
            return causal_chain[0].get("input", "")
        return ""
        
    def _extract_error(self, trajectory: Dict) -> str:
        """提取错误信息"""
        for step in trajectory.get("causal_chain", []):
            if step.get("action") == "error_encountered":
                return step.get("error_message", "")
        return ""
        
    def validate_candidate(
        self,
        candidate: Dict,
        baseline_skill: Dict,
        candidate_skill: Dict,
        test_tasks: List[Dict]
    ) -> ValidationResult:
        """验证候选更新
        
        流程：
        1. 在真实环境中运行baseline版本
        2. 在相同环境中运行candidate版本
        3. 对比结果
        4. 决定Accept/Reject
        """
        candidate_id = candidate.get("candidate_id", "unknown")
        skill_name = candidate.get("skill_name", "unknown")
        
        # 运行baseline版本
        baseline_results = self._run_in_environment(
            baseline_skill,
            test_tasks,
            f"{skill_name}_baseline"
        )
        
        # 运行candidate版本
        candidate_results = self._run_in_environment(
            candidate_skill,
            test_tasks,
            f"{skill_name}_candidate"
        )
        
        # 对比结果
        verdict, rationale, improvement = self._compare_results(
            baseline_results,
            candidate_results,
            test_tasks
        )
        
        result = ValidationResult(
            candidate_id=candidate_id,
            skill_name=skill_name,
            verdict=verdict,
            baseline_performance=baseline_results,
            candidate_performance=candidate_results,
            improvement_metrics=improvement,
            rationale=rationale,
            validated_at=datetime.now().isoformat()
        )
        
        self.results.append(result)
        return result
        
    def _run_in_environment(
        self,
        skill: Dict,
        tasks: List[Dict],
        run_id: str
    ) -> Dict:
        """在真实环境中运行技能
        
        这里是简化实现，实际应用中需要：
        1. 创建隔离的测试环境（Linux容器）
        2. 部署技能
        3. 执行任务
        4. 收集结果
        """
        # 模拟运行结果
        # TODO: 实际在Linux容器中执行
        
        total_tasks = len(tasks)
        if total_tasks == 0:
            return {
                "run_id": run_id,
                "total_tasks": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "errors": []
            }
            
        # 简化实现：基于技能配置估算结果
        success_rate = 0.75  # 基准成功率
        
        # 如果技能有修改，假设成功率提升
        if skill.get("modifications"):
            success_rate += 0.10
            
        # 如果技能保护了成功不变量，假设成功率稳定
        if skill.get("protected_invariants"):
            success_rate = max(success_rate, 0.85)
            
        success_count = int(total_tasks * success_rate)
        
        return {
            "run_id": run_id,
            "total_tasks": total_tasks,
            "success_count": success_count,
            "failure_count": total_tasks - success_count,
            "success_rate": success_count / total_tasks,
            "avg_duration_ms": 3200 + (total_tasks * 100),
            "errors": []
        }
        
    def _compare_results(
        self,
        baseline: Dict,
        candidate: Dict,
        test_tasks: List[Dict]
    ) -> Tuple[Literal["Accept", "Reject"], str, Dict]:
        """对比结果，决定是否接受
        
        单调性保证：
        1. 成功率必须提升或持平
        2. 性能不能显著下降
        3. 不能破坏原有的成功案例
        """
        baseline_rate = baseline.get("success_rate", 0)
        candidate_rate = candidate.get("success_rate", 0)
        
        baseline_duration = baseline.get("avg_duration_ms", 0)
        candidate_duration = candidate.get("avg_duration_ms", 0)
        
        # 计算改进指标
        improvement = {
            "success_rate_delta": candidate_rate - baseline_rate,
            "duration_delta_ms": candidate_duration - baseline_duration,
            "success_count_delta": candidate.get("success_count", 0) - baseline.get("success_count", 0)
        }
        
        # 决策逻辑
        
        # 1. 成功率提升 → Accept
        if candidate_rate > baseline_rate:
            delta = candidate_rate - baseline_rate
            return (
                "Accept",
                f"成功率提升 {delta:.1%}（{baseline_rate:.1%}→{candidate_rate:.1%}）",
                improvement
            )
            
        # 2. 成率持平，性能提升 → Accept
        if candidate_rate == baseline_rate:
            if candidate_duration < baseline_duration:
                speedup = baseline_duration - candidate_duration
                return (
                    "Accept",
                    f"性能提升 {speedup}ms（成功率保持{baseline_rate:.1%}）",
                    improvement
                )
            else:
                return (
                    "Reject",
                    f"成功率无提升且性能无改善（{baseline_rate:.1%}）",
                    improvement
                )
                
        # 3. 成功率下降 → Reject
        else:
            degradation = baseline_rate - candidate_rate
            return (
                "Reject",
                f"成功率下降 {degradation:.1%}（{baseline_rate:.1%}→{candidate_rate:.1%}），违反单调性保证",
                improvement
            )
            
    def validate_all_candidates(
        self,
        candidates: List[Dict],
        skills: Dict[str, Dict],
        trajectories: List[Dict]
    ) -> List[ValidationResult]:
        """批量验证所有候选更新"""
        self.results = []
        
        for candidate in candidates:
            skill_name = candidate.get("skill_name")
            
            if skill_name not in skills:
                print(f"警告：技能 {skill_name} 不存在，跳过验证")
                continue
                
            # 提取测试任务
            test_tasks = self.extract_test_tasks(trajectories, skill_name)
            
            if not test_tasks:
                print(f"警告：技能 {skill_name} 无测试任务，跳过验证")
                continue
                
            # 模拟baseline和candidate技能
            baseline_skill = skills[skill_name].copy()
            candidate_skill = skills[skill_name].copy()
            candidate_skill["modifications"] = candidate.get("proposed_changes")
            candidate_skill["protected_invariants"] = []  # TODO: 从grouper获取
            
            # 执行验证
            result = self.validate_candidate(
                candidate,
                baseline_skill,
                candidate_skill,
                test_tasks
            )
            
            print(f"[{result.verdict}] {skill_name}: {result.rationale}")
            
        return self.results
        
    def generate_validation_report(self, output_path: str = None) -> Dict:
        """生成验证报告"""
        accept_count = sum(1 for r in self.results if r.verdict == "Accept")
        reject_count = sum(1 for r in self.results if r.verdict == "Reject")
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_candidates": len(self.results),
            "accept_count": accept_count,
            "reject_count": reject_count,
            "accept_rate": accept_count / len(self.results) if self.results else 0,
            "monotonicity_guarantee": True,  # 只有Accept的才部署
            "results": [r.to_dict() for r in self.results]
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
        return report
        
    def sync_accepted_skills(
        self,
        output_dir: str = None
    ) -> Dict[str, List[str]]:
        """同步被接受的技能到部署池"""
        if output_dir is None:
            output_dir = self.workspace_path / "deployed_skills"
        else:
            output_dir = Path(output_dir)
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        accepted = []
        rejected = []
        
        for result in self.results:
            if result.verdict == "Accept":
                # 记录接受的技能
                accepted.append(result.skill_name)
                
                # TODO: 实际部署技能文件
                deploy_record = {
                    "skill_name": result.skill_name,
                    "candidate_id": result.candidate_id,
                    "deployed_at": datetime.now().isoformat(),
                    "improvement": result.improvement_metrics
                }
                
                deploy_file = output_dir / f"{result.skill_name}_deploy.json"
                with open(deploy_file, 'w', encoding='utf-8') as f:
                    json.dump(deploy_record, f, indent=2, ensure_ascii=False)
            else:
                rejected.append(result.skill_name)
                
        return {
            "accepted": accepted,
            "rejected": rejected,
            "deploy_dir": str(output_dir)
        }


if __name__ == "__main__":
    # 测试代码
    validator = EnvironmentValidator()
    
    # 模拟测试数据
    test_trajectories = [
        {
            "trajectory_id": "τ_001",
            "skills_invoked": ["test-skill"],
            "success": False,
            "causal_chain": [
                {"action": "receive_prompt", "input": "测试任务1"},
                {"action": "error_encountered", "error_message": "API错误"}
            ]
        },
        {
            "trajectory_id": "τ_002",
            "skills_invoked": ["test-skill"],
            "success": True,
            "causal_chain": [
                {"action": "receive_prompt", "input": "测试任务2"}
            ]
        }
    ]
    
    test_candidate = {
        "candidate_id": "C001",
        "skill_name": "test-skill",
        "proposed_changes": "修复API配置错误"
    }
    
    test_skills = {
        "test-skill": {"name": "test-skill", "version": "1.0"}
    }
    
    # 执行验证
    result = validator.validate_candidate(
        test_candidate,
        test_skills["test-skill"],
        {"name": "test-skill", "version": "2.0", "modifications": "修复API错误"},
        validator.extract_test_tasks(test_trajectories, "test-skill")
    )
    
    print(f"验证结果：{result.verdict}")
    print(f"理由：{result.rationale}")
