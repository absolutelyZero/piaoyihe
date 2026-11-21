#!/usr/bin/env python3
"""
发票票种与重命名字段注册表

该模块是「票种归类 + 各票种可插入字段集 + 默认重命名模板」的唯一事实来源，
供 UI（重命名对话框）、核心服务（重命名执行）与 MCP（字段查询）共用，
避免三处各写一份票种清单而逐渐漂移。

设计要点：
- 票种标识（type_key）与 invoice_type 的展示值解耦：
  普票/专票同属「增值税发票」，共用一条规则。
- 只列出该票种能实际提取到值的字段，因此定额发票只有通用四项。
"""

from typing import Dict, List, Optional, Tuple


# ============================================================
# 票种标识
# ============================================================

# 7 类票种标识，顺序即 UI 下拉框的展示顺序
INVOICE_TYPE_KEYS: List[str] = [
    'vat_invoice',
    'train_ticket',
    'flight_ticket',
    'vehicle_invoice',
    'taxi_invoice',
    'fixed_amount_invoice',
    'toll_invoice',
]

# 票种标识 -> 中文名
INVOICE_TYPE_LABELS: Dict[str, str] = {
    'vat_invoice': '增值税发票',
    'train_ticket': '火车票',
    'flight_ticket': '飞机票',
    'vehicle_invoice': '机动车发票',
    'taxi_invoice': '出租车发票',
    'fixed_amount_invoice': '定额发票',
    'toll_invoice': '通行费发票',
}


# 全票种通用的四个字段
_COMMON_FIELDS: List[Tuple[str, str]] = [
    ('发票类型', 'invoice_type'),
    ('开票日期', 'invoice_date'),
    ('发票号码', 'invoice_code'),
    ('金额', 'amount'),
]


# ============================================================
# 各票种字段集（有序）
# ============================================================

# 票种标识 -> 有序的 (占位符显示名, file_info 键) 列表
TYPE_FIELD_SPECS: Dict[str, List[Tuple[str, str]]] = {
    'vat_invoice': _COMMON_FIELDS + [
        ('商品类型', 'product_type'),
        ('买方名字', 'buyer_name'),
        ('销方名字', 'seller_name'),
    ],
    'train_ticket': _COMMON_FIELDS + [
        ('买方名字', 'buyer_name'),
        ('车次', 'train_number'),
        ('出发站', 'departure_station'),
        ('到达站', 'arrival_station'),
    ],
    'flight_ticket': _COMMON_FIELDS + [
        ('买方名字', 'buyer_name'),
        ('销方名字', 'seller_name'),
        ('航班号', 'flight_number'),
        ('航空公司', 'airline'),
    ],
    'vehicle_invoice': _COMMON_FIELDS + [
        ('商品类型', 'product_type'),
        ('买方名字', 'buyer_name'),
        ('销方名字', 'seller_name'),
        ('车架号', 'vin'),
    ],
    'taxi_invoice': _COMMON_FIELDS + [
        ('销方名字', 'seller_name'),
        ('车牌号', 'plate_number'),
    ],
    'fixed_amount_invoice': list(_COMMON_FIELDS),
    'toll_invoice': _COMMON_FIELDS + [
        ('商品类型', 'product_type'),
        ('买方名字', 'buyer_name'),
        ('销方名字', 'seller_name'),
        ('入口', 'toll_entry'),
        ('出口', 'toll_exit'),
        ('路段', 'toll_section'),
    ],
}


# ============================================================
# 默认重命名模板
# ============================================================
# 仅用于对话框在「该票种无已保存规则」时预填显示，不写入配置、不参与执行。
DEFAULT_RULE_TEMPLATES: Dict[str, str] = {
    'vat_invoice': '{开票日期}-{买方名字}-{金额}',
    'train_ticket': '{开票日期}-{车次}-{出发站}到{到达站}',
    'flight_ticket': '{开票日期}-{航班号}-{航空公司}',
    'vehicle_invoice': '{开票日期}-{车架号}',
    'taxi_invoice': '{开票日期}-{车牌号}-{金额}',
    'fixed_amount_invoice': '{开票日期}-{金额}',
    'toll_invoice': '{开票日期}-{入口}到{出口}',
}


# 所有字段键的并集（去重，保持首次出现顺序）
def _build_all_field_keys() -> List[str]:
    seen: List[str] = []
    for key in INVOICE_TYPE_KEYS:
        for _display, field_key in TYPE_FIELD_SPECS[key]:
            if field_key not in seen:
                seen.append(field_key)
    return seen


ALL_FIELD_KEYS: List[str] = _build_all_field_keys()


# ============================================================
# 辅助函数
# ============================================================

def get_fields(type_key: Optional[str]) -> List[Tuple[str, str]]:
    """
    获取指定票种的可插入字段集

    参数:
        type_key: 票种标识；为 None 或未知时返回全部字段的并集

    返回值:
        List[Tuple[str, str]]: 有序的 (占位符显示名, file_info 键) 列表
    """
    if type_key and type_key in TYPE_FIELD_SPECS:
        return list(TYPE_FIELD_SPECS[type_key])

    # 未知票种：返回所有字段（按 ALL_FIELD_KEYS 顺序，显示名取首次出现的）
    display_by_key: Dict[str, str] = {}
    for key in INVOICE_TYPE_KEYS:
        for display, field_key in TYPE_FIELD_SPECS[key]:
            display_by_key.setdefault(field_key, display)
    return [(display_by_key[k], k) for k in ALL_FIELD_KEYS]


def get_type_label(type_key: str) -> str:
    """
    获取票种的中文名

    参数:
        type_key: 票种标识

    返回值:
        str: 中文名；未知标识时原样返回该标识
    """
    return INVOICE_TYPE_LABELS.get(type_key, type_key)


def get_default_template(type_key: str) -> str:
    """
    获取票种的默认重命名模板

    参数:
        type_key: 票种标识

    返回值:
        str: 默认模板字符串；未知票种返回空字符串
    """
    return DEFAULT_RULE_TEMPLATES.get(type_key, '')


def resolve_field_key(display_name: str) -> Optional[str]:
    """
    把占位符显示名反查为 file_info 键

    参数:
        display_name: 占位符显示名，如 "开票日期"

    返回值:
        Optional[str]: 对应的 file_info 键；未找到返回 None
    """
    for key in INVOICE_TYPE_KEYS:
        for display, field_key in TYPE_FIELD_SPECS[key]:
            if display == display_name:
                return field_key
    return None
