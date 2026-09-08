# 科研倒计时

一个本地运行的科研节点管理工具。用月历展示任务日期区间和截止日，并根据剩余天数自动标记紧急程度。

## 功能

- 月历展示任务起止区间，截止日醒目标记
- 每个事项可添加多个阶段节点，每个节点支持日期点或日期区间
- 点击日历日期或“另有 N 项”，从右侧查看当天全部具体安排
- 左侧“节点管理”集中新增、编辑、完成和删除单个时间节点
- 新建、编辑、删除和完成倒计时
- 自动计算剩余天数、进度和逾期状态
- 倒计时看板与状态筛选
- SQLite 本地持久化，无需配置数据库

## 运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

程序启动后会自动使用默认浏览器打开 <http://127.0.0.1:5000>。
如果不希望自动打开浏览器，可执行 `python run.py --no-browser`。

使用 PyInstaller 打包后，数据库固定保存在 EXE 同级目录的
`data/countdowns.sqlite3`，不会写入 PyInstaller 的临时解压目录。

## 业务树

```text
科研倒计时/
├─ run.py                         # 启动入口
├─ requirements.txt
├─ research_countdown/
│  ├─ __init__.py                 # 应用工厂
│  ├─ database.py                 # SQLite 初始化与连接
│  ├─ repository.py               # 数据读写层
│  ├─ services.py                 # 校验、倒计时与状态业务逻辑
│  ├─ routes.py                   # 页面和 JSON API
│  ├─ templates/index.html        # 页面结构
│  └─ static/
│     ├─ style.css                # 视觉样式
│     └─ app.js                   # 日历与交互
└─ tests/test_app.py              # 自动化测试
```
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "科研倒计时" `
  --add-data "research_countdown/templates;research_countdown/templates" `
  --add-data "research_countdown/static;research_countdown/static" `
  run.py