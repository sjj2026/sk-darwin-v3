#!/usr/bin/env python3
"""
会话轨迹收集器
记录完整的因果链：提示词 → Agent动作 → 环境反馈 → 最终响应

集成到OpenClaw的执行流程中，自动记录所有中间步骤
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading

class TrajectoryCollector:
    """会话轨迹收集器 - 线程安全版本"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保全局只有一个收集器"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, storage_path: str = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # 默认存储路径
            self.storage_path = Path.home() / ".openclaw" / "workspace" / "session_evidence.json"
            
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_trajectory: Optional[Dict] = None
        self._trajectory_lock = threading.Lock()
        
    def start_session(self, user_id: str, session_id: str, initial_prompt: str = ""):
        """开始新的会话轨迹"""
        with self._trajectory_lock:
            self.current_trajectory = {
                "trajectory_id": f"τ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_id[:8]}",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "skills_invoked": [],
                "causal_chain": [
                    {
                        "step": 1,
                        "action": "receive_prompt",
                        "timestamp": datetime.now().isoformat(),
                        "input": initial_prompt,
                        "output": "解析后的意图"
                    }
                ],
                "final_response": None,
                "success": None,
                "metrics": {
                    "total_steps": 1,
                    "tool_calls": 0,
                    "errors": 0,
                    "duration_ms": 0
                }
            }
            self.start_time = datetime.now()
            
    def record_skill_invocation(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True
    ):
        """记录技能调用"""
        with self._trajectory_lock:
            if not self.current_trajectory:
                return
                
            step = {
                "step": len(self.current_trajectory["causal_chain"]) + 1,
                "action": "invoke_skill",
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "input": input_data,
                "output": output_data,
                "success": success
            }
            
            self.current_trajectory["causal_chain"].append(step)
            self.current_trajectory["metrics"]["total_steps"] += 1
            
            if skill_name not in self.current_trajectory["skills_invoked"]:
                self.current_trajectory["skills_invoked"].append(skill_name)
                
    def record_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True
    ):
        """记录工具调用"""
        with self._trajectory_lock:
            if not self.current_trajectory:
                return
                
            step = {
                "step": len(self.current_trajectory["causal_chain"]) + 1,
                "action": "tool_call",
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "parameters": parameters,
                "result": result,
                "success": success
            }
            
            self.current_trajectory["causal_chain"].append(step)
            self.current_trajectory["metrics"]["total_steps"] += 1
            self.current_trajectory["metrics"]["tool_calls"] += 1
            
    def record_error(
        self,
        error_type: str,
        error_message: str,
        recovery_action: str = "",
        context: Dict[str, Any] = None
    ):
        """记录错误和恢复动作"""
        with self._trajectory_lock:
            if not self.current_trajectory:
                return
                
            step = {
                "step": len(self.current_trajectory["causal_chain"]) + 1,
                "action": "error_encountered",
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "error_message": error_message,
                "recovery_action": recovery_action,
                "context": context or {}
            }
            
            self.current_trajectory["causal_chain"].append(step)
            self.current_trajectory["metrics"]["total_steps"] += 1
            self.current_trajectory["metrics"]["errors"] += 1
            
    def record_decision(
        self,
        decision_type: str,
        reasoning: str,
        options_considered: List[str] = None,
        selected_option: str = ""
    ):
        """记录决策过程"""
        with self._trajectory_lock:
            if not self.current_trajectory:
                return
                
            step = {
                "step": len(self.current_trajectory["causal_chain"]) + 1,
                "action": "make_decision",
                "timestamp": datetime.now().isoformat(),
                "decision_type": decision_type,
                "reasoning": reasoning,
                "options_considered": options_considered or [],
                "selected_option": selected_option
            }
            
            self.current_trajectory["causal_chain"].append(step)
            self.current_trajectory["metrics"]["total_steps"] += 1
            
    def end_session(self, final_response: str, success: bool):
        """结束会话轨迹并保存"""
        with self._trajectory_lock:
            if not self.current_trajectory:
                return
                
            self.current_trajectory["final_response"] = final_response
            self.current_trajectory["success"] = success
            self.current_trajectory["metrics"]["duration_ms"] = int(
                (datetime.now() - self.start_time).total_seconds() * 1000
            )
            
            # 保存到存储
            self._save_trajectory()
            
            # 清空当前轨迹
            trajectory_id = self.current_trajectory["trajectory_id"]
            self.current_trajectory = None
            
            return trajectory_id
            
    def _save_trajectory(self):
        """保存轨迹到JSON文件"""
        if not self.storage_path.exists():
            data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "trajectories": []
            }
        else:
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0"
                    },
                    "trajectories": []
                }
                
        data["trajectories"].append(self.current_trajectory)
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def get_trajectories_by_skill(self, skill_name: str) -> List[Dict]:
        """获取调用特定技能的所有轨迹"""
        if not self.storage_path.exists():
            return []
            
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return []
            
        return [
            t for t in data.get("trajectories", [])
            if skill_name in t.get("skills_invoked", [])
        ]
        
    def get_all_trajectories(self) -> List[Dict]:
        """获取所有轨迹"""
        if not self.storage_path.exists():
            return []
            
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("trajectories", [])
        except json.JSONDecodeError:
            return []
            
    def get_statistics(self) -> Dict[str, Any]:
        """获取轨迹统计信息"""
        trajectories = self.get_all_trajectories()
        
        if not trajectories:
            return {
                "total_trajectories": 0,
                "total_users": 0,
                "success_rate": 0.0,
                "avg_steps": 0.0,
                "avg_tool_calls": 0.0,
                "avg_errors": 0.0,
                "avg_duration_ms": 0.0
            }
            
        total = len(trajectories)
        successes = sum(1 for t in trajectories if t.get("success", False))
        unique_users = len(set(t.get("user_id", "unknown") for t in trajectories))
        
        return {
            "total_trajectories": total,
            "total_users": unique_users,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_steps": sum(t["metrics"]["total_steps"] for t in trajectories) / total,
            "avg_tool_calls": sum(t["metrics"]["tool_calls"] for t in trajectories) / total,
            "avg_errors": sum(t["metrics"]["errors"] for t in trajectories) / total,
            "avg_duration_ms": sum(t["metrics"]["duration_ms"] for t in trajectories) / total
        }


# 便捷函数
_collector = None

def get_collector() -> TrajectoryCollector:
    """获取全局收集器实例"""
    global _collector
    if not _collector:
        _collector = TrajectoryCollector()
    return _collector


if __name__ == "__main__":
    # 测试代码
    collector = TrajectoryCollector("./test_evidence.json")
    
    # 模拟一个会话
    collector.start_session("user_001", "session_test123", "帮我分析一下AI技能市场")
    collector.record_skill_invocation(
        "darwin-skill",
        {"skill_name": "test-skill"},
        {"score": 85, "grade": "B"},
        success=True
    )
    collector.record_tool_call(
        "web_search",
        {"query": "AI技能市场趋势"},
        {"results": ["结果1", "结果2"]},
        success=True
    )
    collector.record_error(
        "APIError",
        "端口配置错误",
        "重试",
        {"api": "clawhub"}
    )
    collector.end_session("分析完成，AI技能市场呈现增长趋势", True)
    
    # 打印统计信息
    print(json.dumps(collector.get_statistics(), indent=2, ensure_ascii=False))
