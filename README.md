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

## 聯絡方式

有問題請聯絡
Discord : minz_0116
