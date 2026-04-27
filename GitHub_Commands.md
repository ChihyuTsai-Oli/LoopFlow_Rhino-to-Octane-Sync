# GitHub 同步指令

在 Cursor 終端機依序複製貼上執行。  
**每次只在一台電腦操作，切換前先完成 Push，切換後先執行 Pull。**

---

## 開始工作前 — Pull（從 GitHub 拉取最新）

```powershell
cd "E:\_GitHub\LoopFlow"
git pull
```

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Blender-Sync"
git pull
```

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync"
git pull
```

---

## 工作完成後 — Commit & Push

### LoopFlow

```powershell
cd "E:\_GitHub\LoopFlow"
git add -A
git status --short
```

```powershell
git commit -m "update: "
git push origin main
```

### LoopFlow_Rhino-to-Blender-Sync

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Blender-Sync"
git add -A
git status --short
```

```powershell
git commit -m "update: "
git push origin main
```

### LoopFlow_Rhino-to-Octane-Sync

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync"
git add -A
git status --short
```

```powershell
git commit -m "update: "
git push origin main
```

---

## 確認全部同步狀態

```powershell
cd "E:\_GitHub\LoopFlow"; git status
```

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Blender-Sync"; git status
```

```powershell
cd "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync"; git status
```
