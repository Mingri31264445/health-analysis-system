# 健康分析系統

## 快速開始

### 1. Clone 專案

```bash
git clone
```

### 2. 切換至專案資料夾

```bash
cd health-analysis-system
```

### 3. 建立虛擬環境

```bash
conda create -n myproject python=3.11
conda activate myproject
```

### 4. 安裝套件

```bash
pip install -r requirements.txt
```

### 5. 建立資料庫

```bash
python manage.py migrate
```

> 第一次拉到權限功能後也要執行這行，系統會建立「研究人員」群組與資料歸屬欄位。

### 6. 建立 media 資料夾

```bash
mkdir media
```

### 6. 啟動伺服器

```bash
python manage.py runserver
```

瀏覽器打開：http://localhost:8000

## 專案說明

整合式健康分析系統，包含：

- 健康問卷管理
- 經絡儀測試記錄管理
- BFS 測試紀錄管理
- 面診系統紀錄管理

本系統以「一個受測者帳號，多筆檢測紀錄」為核心設計。健康問卷用來建立基本背景資料，BFS、經絡儀與面診資料則作為同一位受測者的長期健康紀錄。

## 初審意見改進

已整理兩份初審建議與後續改進方向，包含現況分析、長期追蹤、健康問卷定位、隱私保護、非功能規格與可行性分析：

- `docs/initial-review-improvement.md`

## 權限角色

- 一般使用者：只能查看與操作自己的健康問卷、BFS 紀錄、經絡紀錄與面診紀錄。
- 研究人員：可查看全部受測者紀錄，方便研究分析與資料整理，但不能管理帳號權限。
- 系統管理員：可查看、修改與刪除全部紀錄，並可在 Django Admin 管理帳號與群組。

若要指定研究人員，請先建立管理員帳號並登入 `/admin/`，再到使用者資料中把該帳號加入「研究人員」群組。

## 聯絡方式

有問題請聯絡
Discord : minz_0116
