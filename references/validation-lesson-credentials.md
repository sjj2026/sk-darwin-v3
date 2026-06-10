# darwin-v3 实战教训

## 凭证文件优先检查原则

### 问题
在使用darwin-v3优化技能后，尝试上传到觅游技能便利店时：
1. 直接调用注册API创建新账号
2. 未先检查现有凭证文件
3. 导致重复注册，新账号需重新认领

### 教训
**在任何需要凭证的操作前，必须先检查本地凭证文件是否存在且有效**

### 检查顺序
1. 检查凭证文件是否存在：`~/.hermes/meyo/credentials.json`
2. 验证凭证有效性：调用API确认agent_id有效
3. 如凭证存在但无效，尝试恢复或更新
4. 只有确认无凭证时才执行注册

### 伪代码流程
```
CRED_FILE = ~/.hermes/meyo/credentials.json

if CRED_FILE exists:
    API_KEY = extract from CRED_FILE
    RESULT = verify API call
    if RESULT contains agent_id:
        echo "凭证有效，跳过注册"
    else:
        echo "凭证无效，需要重新注册"
else:
    echo "无凭证文件，执行注册"
```

### 日期
2026-05-29
