#!/usr/bin/env python3
"""
darwin v3.0 主程序
集成SkillClaw机制的技能进化框架

完整流程：
Phase -1: 会话轨迹收集
Phase 0: 初始评估
Phase 1: 分组聚合
Phase 2: 三动作决策
Phase 3: 批量进化实施
Phase 4: 环境验证
Phase 5: 最终评估
Phase 6: 技能同步
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from trajectory_collector import TrajectoryCollector, get_collector
from skill_grouper import SkillGrouper
from batch_evolver import BatchEvolver, EvolutionCandidate
from environment_validator import EnvironmentValidator, ValidationResult

class DarwinV3:
    """darwin v3.0 主控制器"""
    
    def __init__(
        self,
        evidence_path: str = None,
        workspace_path: str = None,
        config_path: str = None
    ):
        self.evidence_path = Path(evidence_path) if evidence_path else \
            Path.home() / ".openclaw" / "workspace" / "session_evidence.json"
        self.workspace_path = Path(workspace_path) if workspace_path else \
            Path.home() / ".openclaw" / "workspace"
            
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self.collector = TrajectoryCollector(str(self.evidence_path))
        self.grouper = SkillGrouper(str(self.evidence_path))
        self.evolver = BatchEvolver(str(self.evidence_path))
        self.validator = EnvironmentValidator(
            workspace_path=str(self.workspace_path)
        )
        
        # 状态追踪
        self.current_phase = -1
        self.evolution_history = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        default_config = {
            "min_samples": 5,
            "max_test_tasks": 10,
            "accept_threshold": 0.8,
            "enable_auto_deploy": False,
            "notification_email": None
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        return default_config
        
    def run_full_evolution_cycle(self) -> Dict:
        """运行完整的进化周期
        
        从Phase -1到Phase 6的完整流程
        """
        print("=" * 60)
        print("darwin v3.0 - 技能进化框架")
        print("集成SkillClaw机制")
        print("=" * 60)
        
        report = {
            "start_time": datetime.now().isoformat(),
            "phases": {}
        }
        
        # Phase -1: 会话轨迹收集
        print("\n[Phase -1] 会话轨迹收集")
        self.current_phase = -1
        trajectories = self.collector.get_all_trajectories()
        stats = self.collector.get_statistics()
        
        report["phases"]["phase_-1"] = {
            "trajectory_count": len(trajectories),
            "statistics": stats
        }
        
        print(f"  收集轨迹: {len(trajectories)}条")
        print(f"  成功率: {stats['success_rate']:.1%}")
        print(f"  平均步骤: {stats['avg_steps']:.1f}")
        
        if len(trajectories) < self.config["min_samples"]:
            print(f"\n⚠️  轨迹数量不足（{len(trajectories)}<{self.config['min_samples']}），建议继续收集")
            return report
            
        # Phase 0: 初始评估
        print("\n[Phase 0] 初始评估")
        self.current_phase = 0
        
        # 计算当前技能库状态
        groups = self.grouper.group_by_skill(trajectories)
        initial_scores = {}
        
        for skill_name, skill_trajectories in groups.items():
            if skill_name == "∅":
                continue
            skill_stats = self.grouper.calculate_group_statistics(skill_trajectories)
            initial_scores[skill_name] = {
                "success_rate": skill_stats["success_rate"],
                "user_count": skill_stats["unique_users"],
                "trajectory_count": skill_stats["count"]
            }
            
        report["phases"]["phase_0"] = {
            "total_skills": len([k for k in groups.keys() if k != "∅"]),
            "initial_scores": initial_scores
        }
        
        print(f"  技能数量: {len(initial_scores)}")
        for skill_name, scores in initial_scores.items():
            print(f"    {skill_name}: 成功率 {scores['success_rate']:.1%}")
            
        # Phase 1: 分组聚合
        print("\n[Phase 1] 分组聚合")
        self.current_phase = 1
        
        group_report = self.grouper.generate_report()
        natural_experiments = self.grouper.detect_natural_ablation_experiments()
        
        report["phases"]["phase_1"] = {
            "group_count": len(groups),
            "natural_experiments": natural_experiments
        }
        
        print(f"  证据组数: {len(groups)}")
        print(f"  自然消融实验: {len(natural_experiments)}个")
        
        # Phase 2: 三动作决策
        print("\n[Phase 2] 三动作决策")
        self.current_phase = 2
        
        candidates = self.evolver.generate_candidates(
            min_samples=self.config["min_samples"]
        )
        evolution_report = self.evolver.generate_evolution_report()
        
        report["phases"]["phase_2"] = {
            "total_candidates": len(candidates),
            "action_distribution": evolution_report["action_distribution"],
            "candidates": evolution_report["candidates"]
        }
        
        print(f"  候选更新: {len(candidates)}个")
        print(f"  动作分布: {evolution_report['action_distribution']}")
        
        if not candidates:
            print("\n✅ 无需进化，所有技能表现良好")
            return report
            
        # Phase 3: 批量进化实施
        print("\n[Phase 3] 批量进化实施")
        self.current_phase = 3
        
        # 这里需要实际的技能文件，简化实现
        print(f"  生成 {len(candidates)} 个候选更新")
        
        for i, candidate in enumerate(candidates[:5], 1):
            print(f"  [{i}] {candidate.skill_name}: {candidate.action}")
            print(f"      {candidate.rationale}")
            
        report["phases"]["phase_3"] = {
            "candidates_processed": len(candidates)
        }
        
        # Phase 4: 环境验证
        print("\n[Phase 4] 环境验证")
        self.current_phase = 4
        
        # 模拟技能库（实际应用中从文件加载）
        skills = {skill_name: {} for skill_name in groups.keys() if skill_name != "∅"}
        
        validation_results = self.validator.validate_all_candidates(
            [c.to_dict() for c in candidates],
            skills,
            trajectories
        )
        validation_report = self.validator.generate_validation_report()
        
        report["phases"]["phase_4"] = {
            "total_validated": len(validation_results),
            "accept_count": validation_report["accept_count"],
            "reject_count": validation_report["reject_count"],
            "monotonicity_guarantee": validation_report["monotonicity_guarantee"]
        }
        
        print(f"  验证候选: {len(validation_results)}个")
        print(f"  接受: {validation_report['accept_count']}个")
        print(f"  拒绝: {validation_report['reject_count']}个")
        print(f"  单调性保证: {'✅' if validation_report['monotonicity_guarantee'] else '❌'}")
        
        # Phase 5: 最终评估
        print("\n[Phase 5] 最终评估")
        self.current_phase = 5
        
        # 计算改进
        improvements = {}
        for result in validation_results:
            if result.verdict == "Accept":
                improvements[result.skill_name] = result.improvement_metrics
                
        report["phases"]["phase_5"] = {
            "improvements": improvements,
            "total_improved": len(improvements)
        }
        
        print(f"  成功改进: {len(improvements)}个技能")
        
        # Phase 6: 技能同步
        print("\n[Phase 6] 技能同步")
        self.current_phase = 6
        
        sync_result = self.validator.sync_accepted_skills()
        
        report["phases"]["phase_6"] = {
            "deployed_skills": sync_result["accepted"],
            "rejected_skills": sync_result["rejected"],
            "deploy_dir": sync_result["deploy_dir"]
        }
        
        print(f"  部署技能: {len(sync_result['accepted'])}个")
        print(f"  拒绝技能: {len(sync_result['rejected'])}个")
        print(f"  部署目录: {sync_result['deploy_dir']}")
        
        # 完成报告
        report["end_time"] = datetime.now().isoformat()
        report["duration_seconds"] = (
            datetime.fromisoformat(report["end_time"]) - 
            datetime.fromisoformat(report["start_time"])
        ).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ 进化周期完成")
        print(f"   耗时: {report['duration_seconds']:.1f}秒")
        print("=" * 60)
        
        # 保存报告
        report_path = self.workspace_path / f"darwin_v3_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"\n报告已保存: {report_path}")
        
        return report
        
    def run_nightly_evolution(self):
        """运行夜间进化任务
        
        适合定时任务调用
        """
        print(f"\n{'='*60}")
        print(f"darwin v3.0 夜间进化任务")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        try:
            report = self.run_full_evolution_cycle()
            
            # 发送通知（如果配置了邮箱）
            if self.config.get("notification_email"):
                self._send_notification(report)
                
            return report
            
        except Exception as e:
            print(f"\n❌ 进化失败: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _send_notification(self, report: Dict):
        """发送进化通知邮件"""
        # TODO: 实现邮件通知
        pass
        
    def get_status(self) -> Dict:
        """获取当前状态"""
        trajectories = self.collector.get_all_trajectories()
        stats = self.collector.get_statistics()
        
        return {
            "current_phase": self.current_phase,
            "trajectory_count": len(trajectories),
            "statistics": stats,
            "evolution_history_count": len(self.evolution_history)
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="darwin v3.0 - 技能进化框架")
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="运行夜间进化任务"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看当前状态"
    )
    parser.add_argument(
        "--evidence-path",
        type=str,
        help="会话轨迹存储路径"
    )
    parser.add_argument(
        "--workspace-path",
        type=str,
        help="工作空间路径"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    darwin = DarwinV3(
        evidence_path=args.evidence_path,
        workspace_path=args.workspace_path,
        config_path=args.config
    )
    
    if args.status:
        status = darwin.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.nightly:
        darwin.run_nightly_evolution()
    else:
        darwin.run_full_evolution_cycle()


if __name__ == "__main__":
    main()
