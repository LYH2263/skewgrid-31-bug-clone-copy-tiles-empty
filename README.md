# Skewgrid（错层）

栅格金字塔瓦片缓存。按 TMS / XYZ 组织 `{z}/{x}/{y}` 瓦片，检查路径与瓦片内容是否对齐，并在地图和覆盖率图上查看缺口或 y 轴不一致。

## 启动

```bash
docker compose up --build
```

若缓存目录结构有过变更，需要重建数据卷：

```bash
docker compose down -v
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:3100 |
| API / 瓦片 | http://localhost:8100 |

```bash
cd backend
pytest
```

## 功能

- 图层列表与新建
- 图层快照克隆（复制为新 slug，可选拷贝本地金字塔，扫描/任务历史不带入）
- 地图预览（XYZ / TMS）
- 覆盖率格子
- 单瓦检查与写回
- 扫描历史
- 预渲染、批量修复、GeoJSON 导出
- 设置项

示例图层：`demo-grid`（z=0..3）、`clean-atlas`（z=0..2）。
