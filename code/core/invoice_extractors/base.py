#!/usr/bin/env python3
"""
发票字段提取器抽象基类模块

提供所有发票提取器的抽象基类，定义统一的接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import re
import fitz

# 公司名后缀：用于从票面文本中识别「像公司名」的片段
COMPANY_SUFFIX_RE = re.compile(
    r'(?:股份有限公司|有限责任公司|有限公司|分公司|旅行社|集团公司|集团|'
    r'宾馆|酒店|饭店|经营部|租赁部|合作社|事务所|研究院|医院|中心|厂|店)$'
)

# 出现这些字样的行不是公司名（开户行、税务机关、标签行、密码区等）
COMPANY_LINE_EXCLUDE = (
    '银行', '支行', '分行', '信用社', '税务局', '识别号', '信用代码',
    '发票', '监制', '校验码', '机器编号', '密码区',
)

# 公司名前可能粘连的标签残余（全电发票的「购买方信息」「名称:」、旧版的「购 名称：」等）
COMPANY_LABEL_PREFIXES = (
    '购买方信息', '销售方信息', '购买方名称', '销售方名称',
    '购买方', '销售方', '名称', '信息', '购买', '销售',
    '购', '买', '方', '信', '息', '名', '称', '销', '售',
    ':', '：', ' ',
)

# 公司名主干：非贪婪前缀 + 公司类后缀（后缀之后可能还有「有限公司」被切开，另行补齐）
_COMPANY_RE = re.compile(
    r'([\u4e00-\u9fa5（）()A-Za-z0-9]{2,40}?'
    r'(?:股份有限公司|有限责任公司|有限公司|分公司|旅行社|集团公司|集团|'
    r'宾馆|酒店|饭店|经营部|租赁部|合作社|事务所|研究院|医院|中心|厂|店))'
)

# 名称被版式切开的补齐片段（如「…集团」+「有限公司」）
_TAIL_CONTINUE_RE = re.compile(r'\s*(公司|有限公司|分公司|集团公司|集团)')

# 换行后的分公司/子公司名（如「哈尔滨市城投投资控股有限公司」+「机场专用路分公司」）
_TAIL_BRANCH_RE = re.compile(r'\s*([\u4e00-\u9fa5]{2,20}(?:分公司|公司|中心|店))(?=\s|$)')


def _strip_label_prefix(name: str) -> str:
    """去掉公司名前粘连的标签字（如「名称:」「购 名称：」）。"""
    changed = True
    while changed and name:
        changed = False
        for prefix in COMPANY_LABEL_PREFIXES:
            if name.startswith(prefix) and len(name) > len(prefix):
                name = name[len(prefix):]
                changed = True
                break
    return name


def iter_company_names(text: str) -> List[str]:
    """按出现顺序返回文本中「像公司名」的片段（去重、长度 4~60）。

    全电发票新版式把「购买方信息」「销售方信息」等标签与名称值分置不同行，
    旧版纸质发票则把「购/买/方」拆成竖排单字、「名　　　　称:」中间夹全角空格，
    这些版式下标签无法直接取值，只能按票面中公司名的出现顺序推断：
    第 1 个为购买方，第 2 个为销售方。

    Args:
        text: 票面文本

    Returns:
        List[str]: 公司名列表，按文本出现顺序
    """
    text = text or ''
    names: List[str] = []
    consumed = 0
    for match in _COMPANY_RE.finditer(text):
        if match.start() < consumed:
            # 已被上一个公司名合并进来的分支片段（如「机场专用路分公司」），跳过
            continue
        name = match.group(1)
        end = match.end()

        # 补齐被版式切开的尾部（「…集团」+「有限公司」）
        while True:
            tail = _TAIL_CONTINUE_RE.match(text, end)
            if not tail:
                break
            name += tail.group(1)
            end = tail.end()

        # 合并换行后的分支机构（「…有限公司」+「机场专用路分公司」）
        if name.endswith('公司'):
            branch = _TAIL_BRANCH_RE.match(text, end)
            if branch:
                name += branch.group(1)
                end = branch.end()

        consumed = end
        name = _strip_label_prefix(name).strip()
        if len(name) < 4 or len(name) > 60:
            continue
        if any(token in name for token in COMPANY_LINE_EXCLUDE):
            continue
        if name not in names:
            names.append(name)
    return names


class InvoiceExtractor(ABC):
    """
    发票字段提取器抽象基类

    所有具体票种提取器必须继承此类，实现各字段的提取方法。
    支持上下文管理器协议，确保PDF文档正确关闭。

    Attributes:
        INVOICE_TYPE_KEYWORDS: 类属性，用于识别票种的关键词列表
        TYPE_KEY: 类属性，票种标识（与 invoice_field_registry.INVOICE_TYPE_KEYS 对应）
    """

    INVOICE_TYPE_KEYWORDS: List[str] = []

    # 票种标识，供重命名层按票种选择规则。子类必须赋值。
    TYPE_KEY: str = ""

    def __init__(self, pdf_path: str):
        """
        初始化提取器

        Args:
            pdf_path: PDF文件路径
        """
        self.pdf_path = pdf_path
        self._doc = None
        self._text = None
        self._pages = []

    def __enter__(self):
        """
        上下文管理器入口

        打开PDF文档，缓存文本和页面数据

        Returns:
            InvoiceExtractor: 当前实例
        """
        self._doc = fitz.open(self.pdf_path)
        self._pages = [self._doc[i] for i in range(len(self._doc))]
        self._text = "\n".join([page.get_text(sort="block") for page in self._pages])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口

        关闭PDF文档，释放资源

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪

        Returns:
            bool: 是否处理异常（False表示不处理）
        """
        if self._doc:
            self._doc.close()
        return False

    @classmethod
    def can_handle(cls, text: str) -> bool:
        """
        判断是否能处理该文本内容

        通过检查文本中是否包含票种关键词来判断

        Args:
            text: PDF文本内容

        Returns:
            bool: 是否能处理该票种
        """
        return any(keyword in text for keyword in cls.INVOICE_TYPE_KEYWORDS)

    @abstractmethod
    def extract_amount(self) -> float:
        """
        提取金额

        Returns:
            float: 提取的金额，失败返回0.0
        """
        pass

    @abstractmethod
    def extract_invoice_date(self) -> str:
        """
        提取开票日期

        Returns:
            str: 日期字符串，格式YYYY-MM-DD
        """
        pass

    @abstractmethod
    def extract_invoice_type(self) -> str:
        """
        提取发票类型

        Returns:
            str: 发票类型名称，如"普票"、"专票"、"火车票"等
        """
        pass

    @abstractmethod
    def extract_product_type(self) -> str:
        """
        提取商品类型/服务名称

        Returns:
            str: 商品或服务名称，无则返回空字符串
        """
        pass

    @abstractmethod
    def extract_buyer_name(self) -> str:
        """
        提取购买方名称

        Returns:
            str: 购买方名称
        """
        pass

    @abstractmethod
    def extract_seller_name(self) -> str:
        """
        提取销售方名称

        Returns:
            str: 销售方名称
        """
        pass

    @abstractmethod
    def extract_invoice_code(self) -> str:
        """
        提取发票号码

        Returns:
            str: 发票号码，无则返回空字符串
        """
        pass

    @abstractmethod
    def extract_tax_amount(self) -> float:
        """
        提取税额

        Returns:
            float: 提取的税额，无则返回0.0
        """
        pass

    def extract_extra_fields(self) -> Dict[str, Any]:
        """
        提取该票种特有的字段

        非抽象钩子：默认无特有字段。需要特有字段的票种覆写此方法，
        返回 {file_info 键: 值} 的字典，键应使用英文 snake_case。

        返回值:
            Dict[str, Any]: 特有字段字典，默认为空
        """
        return {}

    def extract_all(self) -> Dict[str, Any]:
        """
        一次性提取所有字段

        调用各字段提取方法，返回完整信息字典。
        特有字段（extract_extra_fields 的返回值）会合并进结果，
        并附带票种标识 invoice_type_key。

        Returns:
            Dict[str, Any]: 包含所有字段的字典
                - amount: 金额
                - invoice_date: 开票日期
                - invoice_type: 发票类型
                - product_type: 商品类型
                - buyer_name: 购买方名称
                - seller_name: 销售方名称
                - invoice_code: 发票号码
                - tax_amount: 税额
                - invoice_type_key: 票种标识（7 类票种之一）
                - 以及各票种特有字段
        """
        info = {
            'amount': self.extract_amount(),
            'invoice_date': self.extract_invoice_date(),
            'invoice_type': self.extract_invoice_type(),
            'product_type': self.extract_product_type(),
            'buyer_name': self.extract_buyer_name(),
            'seller_name': self.extract_seller_name(),
            'invoice_code': self.extract_invoice_code(),
            'tax_amount': self.extract_tax_amount(),
        }

        # 合并票种特有字段
        try:
            info.update(self.extract_extra_fields() or {})
        except Exception:
            # 特有字段提取失败不应影响通用字段
            pass

        # 票种标识（重命名层据此选择规则）
        info['invoice_type_key'] = self.TYPE_KEY

        return info
