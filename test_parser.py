import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from parser import parse_label_text

def test_all():
    tests = [
        {
            "name": "图1 聚酯薄膜 TB1",
            "lines": ["聚酯薄膜", "型号: TB1", "规格: 75μm×1091mm×4050m",
                      "净重: 461.6kg", "卷号: H260828B08C16N", "订单号: H260828B08C16N", "内电晕"],
            "checks": {"thickness": 75, "width": 1091, "weight": 461.6, "roll_no": "H260828B08C16N", "corona": "内电晕"}
        },
        {
            "name": "图2 防静电膜 OCA",
            "lines": ["50U透明防静电膜", "50u*1160mm*6070m", "平方数: 7041.2",
                      "批号: E0922DA02", "供应商: 佛山安飞姆"],
            "checks": {"thickness": 50, "width": 1160, "square_m": 7041.2}
        },
        {
            "name": "图3 合格证 D11",
            "lines": ["聚酯薄膜", "型号: D11", "等级: 优等品", "规格: 50μm×1095mm×6100m",
                      "净重: 466.0kg", "批号: 2260804A07A13", "内电晕"],
            "checks": {"thickness": 50, "width": 1095, "weight": 466.0, "batch_no": "2260804A07A13", "corona": "内电晕"}
        },
        {
            "name": "图4 聚脂薄膜 CY20RM",
            "lines": ["聚脂薄膜", "型号: CY20RM", "规格: 0.050mm×1095mm",
                      "净重: 933.3kg", "订单号: 1186N", "卷号: 042RM050109501", "内电"],
            "checks": {"thickness": 50, "width": 1095, "weight": 933.3, "roll_no": "042RM050109501", "corona": "内电晕"}
        }
    ]

    passed = 0
    failed = 0

    for t in tests:
        print(f"\n测试: {t['name']}")
        result = parse_label_text(t['lines'])
        print(f"  解析结果: 厚度={result['thickness']}μm, 宽度={result['width']}mm, 卷号={result['roll_no']}")

        all_ok = True
        for key, expected in t['checks'].items():
            actual = result.get(key)
            if key in ('thickness', 'weight', 'square_m'):
                ok = actual and abs(float(actual) - float(expected)) < 0.1
            else:
                ok = actual == expected
            if not ok:
                print(f"  ❌ {key}: 期望 {expected}, 实际 {actual}")
                all_ok = False

        if all_ok:
            print(f"  ✅ 通过")
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"结果: {passed} 通过, {failed} 失败 (共 {len(tests)} 个)")
    return failed == 0

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
