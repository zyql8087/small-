# bigfiles 清单(sha256 校验;大文件本体,git 直传)

| 文件 | MB | sha256(前16) | 用途 |
|---|---|---|---|
| geometry_stl/m2_class2_1383_geometry.stl | 13.9 | 4447e7bc11e5a060 | M09 验证例1 几何输入(PDE 网格边界定义) |
| geometry_stl/m2_class2_1489_geometry.stl | 8.8 | 29fba505fec9750d | M08 全程完成样本2 几何 |
| geometry_stl/m3_class12_26_geometry.stl | 20.6 | 549cd8a8f180f5ac | M09 验证例2 几何输入(瞬态最重样本) |
| geometry_stl/m3_class12_26_geometry_shortedge_cleaned.stl | 17.3 | d9598b2678347e54 | 短边清理版几何(修复实验产物) |
| geometry_stl/m3_class12_540_geometry.stl | 19.7 | ba2fe4c398c44060 | M08 截止终止样本 几何 |
| geometry_stl/m3_class12_61_geometry.stl | 18.0 | 21ee5f9c057a6ed5 | M08 近全程样本 几何 |
| solver_inps/m08_m2_1383_zexp.inp | 32.0 | a86c61cebcf2a15e | M08 全程样本1 显式 z 求解模型 |
| solver_inps/m08_m2_1489_zexp.inp | 18.7 | 0d2a69741b22ca7b | M08 全程样本2 显式 z 求解模型 |
| solver_inps/m08_m3_26_clean_zexp.inp | 59.2 | 8f91c29c0af1b6b8 | 清洁网格(塌缩+翻转修复)验证模型 |
| solver_inps/m08_m3_26_zexp.inp | 50.4 | 1c7ce5dd5923b647 | M08 全程样本3 显式 z 求解模型 |
| solver_inps/m08_m3_540_zexp.inp | 46.6 | 1252010e23851a8a | M08 deadline-terminated 显式 z 模型 |
| solver_inps/m08_m3_61_zexp.inp | 42.0 | 38e9531bbfb7ad51 | M08 practical-terminated 显式 z 模型 |
| experiment_inps/m2_marlow_variant.inp | 31.9 | 2e1d4ca7dfb6449a | Marlow 材料 M2 变体(材料排查) |
| experiment_inps/m3_hotzone_fixed_marlow.inp | 51.6 | cb5b575191c240f8 | 热区治理×Marlow(2×2 析因) |
| experiment_inps/m3_hotzone_poly2_crossB.inp | 52.9 | ed46dc4abd7727c5 | 热区治理×poly2 交叉实验B(2×2 析因) |
| experiment_inps/m3_marlow.inp | 53.9 | 94b94c4e41c73e4b | Marlow 材料 M3 验证模型 |

**未收录(超出 GitHub git 单文件 100MB 硬限)**:全部 ODB 结果文件(437MB–1.4GB)。可用求解模型重跑再生;如需直接下载原 ODB,可用 GitHub Release 附件(单文件≤2GB)另传。
